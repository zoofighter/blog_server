# Google Cloud 배포 가이드

## 1. 사전 준비 (로컬)

### 1.1 gcloud CLI 설치
```bash
brew install google-cloud-sdk
gcloud auth login
```

### 1.2 프로젝트 생성 및 설정
```bash
# 프로젝트 ID는 전 세계에서 유일해야 함 (예: blog-agg-2026)
gcloud projects create <프로젝트ID> --name="Blog Aggregator"
gcloud config set project <프로젝트ID>

# 결제 연결
gcloud billing accounts list
gcloud billing projects link <프로젝트ID> --billing-account=<결제계정ID>

# Compute Engine API 활성화
gcloud services enable compute.googleapis.com
```

## 2. VM 인스턴스 생성

### 2.1 콘솔에서 생성
https://console.cloud.google.com → Compute Engine → VM 인스턴스 → 인스턴스 만들기

| 설정 | 값 |
|------|---|
| 이름 | `blog-aggregator` |
| 리전 | `us-central1 (Iowa)` ← Free Tier 대상 |
| 영역 | `us-central1-a` |
| 시리즈 | E2 |
| 머신 유형 | **e2-micro** (vCPU 0.25개, 메모리 1GB) |

**부팅 디스크** → 변경:

| 설정 | 값 |
|------|---|
| 운영체제 | Ubuntu 22.04 LTS |
| 디스크 유형 | 표준 영구 디스크 |
| 크기 | 30GB |

**방화벽:**
- [x] **HTTP 트래픽 허용** ← 반드시 체크!

> 체크하지 않으면 외부에서 접속 불가. 나중에 CLI로 추가 가능 (트러블슈팅 #3 참고)

### 2.2 외부 IP 확인
```bash
gcloud compute instances list
```

## 3. 배포

### 3.1 프로젝트 업로드 (로컬에서)
```bash
cd ~/Dropbox/03_code/a_0306_blog
bash deploy/upload_gcp.sh blog-aggregator us-central1-a
```

> `upload_gcp.sh`는 tar 압축 → gcloud scp 전송 → 서버 압축 해제 방식
> (`gcloud compute scp`는 `--exclude` 미지원이므로 tar 사용)

### 3.2 서버 셋업
```bash
gcloud compute ssh blog-aggregator --zone=us-central1-a
sudo bash /opt/blog-aggregator/deploy/setup.sh
```

`setup.sh`가 자동으로 처리하는 것:
- Python 3.11 + venv + pip install
- Nginx 설정
- systemd 서비스 등록 (User를 현재 사용자로 자동 설정)
- data 디렉토리 생성
- iptables 방화벽 설정

### 3.3 비밀번호 설정
```bash
sudo nano /etc/systemd/system/blog-aggregator.service
# ADMIN_PASSWORD, SECRET_KEY 변경

sudo systemctl daemon-reload
sudo systemctl restart blog-aggregator
```

### 3.4 접속 확인
```
http://<외부IP>/           → 공개 페이지
http://<외부IP>/admin/     → 관리자 페이지
```

## 4. 코드 업데이트 시

```bash
# 1. 로컬에서 업로드
bash deploy/upload_gcp.sh blog-aggregator us-central1-a

# 2. 서버 재시작
gcloud compute ssh blog-aggregator --zone=us-central1-a \
    --command='sudo systemctl restart blog-aggregator'
```

## 5. 운영 명령어

```bash
# SSH 접속
gcloud compute ssh blog-aggregator --zone=us-central1-a

# 서비스 상태
sudo systemctl status blog-aggregator

# 로그 확인 (실시간)
sudo journalctl -u blog-aggregator -f

# 서비스 재시작
sudo systemctl restart blog-aggregator

# 서버에서 외부 IP 확인
curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google"
```

> 서버 안에서 `gcloud compute instances list`는 권한 부족으로 실패함. 외부 IP는 메타데이터 API로 확인.

## 6. 트러블슈팅

### #1. SSH Permission Denied
```
ubuntu@34.67.226.176: Permission denied (publickey).
```
**원인:** Oracle Cloud용 `upload.sh`는 `SSH_USER="ubuntu"` 고정. GCP 사용자명은 다름.
**해결:** `upload_gcp.sh` 사용 (`gcloud compute scp`가 사용자명 자동 처리)

### #2. gcloud compute scp --exclude 미지원
**원인:** `gcloud compute scp`는 scp 래퍼로 `--exclude` 옵션 없음
**해결:** `upload_gcp.sh`를 tar 압축 → 전송 → 해제 방식으로 변경

### #3. PERMISSION_DENIED: compute.googleapis.com
```
ERROR: PERMISSION_DENIED: Permission denied to enable service [compute.googleapis.com]
```
**원인:** 존재하지 않는 프로젝트 ID가 설정됨 (프로젝트 ID는 전 세계 유일해야 함)
**해결:**
```bash
gcloud projects list                    # 실제 프로젝트 확인
gcloud projects create <고유ID> --name="Blog Aggregator"
gcloud config set project <고유ID>
gcloud billing projects link <고유ID> --billing-account=<결제계정ID>
gcloud services enable compute.googleapis.com
```

### #4. sqlite3.OperationalError: unable to open database file
**원인:** `upload_gcp.sh`에서 `data/blog.db` 제외 → `data/` 디렉토리 자체가 서버에 없음
**해결:** `setup.sh`에 `mkdir -p $APP_DIR/data` 추가. 수동 수정:
```bash
gcloud compute ssh blog-aggregator --zone=us-central1-a \
    --command="mkdir -p /opt/blog-aggregator/data && sudo systemctl restart blog-aggregator"
```

### #5. systemd 서비스 User 권한 문제
**원인:** `blog-aggregator.service`의 `User=ubuntu` — GCP에서는 ubuntu 사용자 없음
**해결:** `setup.sh`가 자동으로 `SUDO_USER`를 감지하여 서비스 파일의 User를 치환.
수동 확인:
```bash
grep "^User=" /etc/systemd/system/blog-aggregator.service
# User=boon 등 실제 사용자명이어야 함
```

### #6. 브라우저 접속 불가 (HTTP 방화벽)
**원인:** 인스턴스 생성 시 "HTTP 트래픽 허용" 미체크 → GCP 방화벽에 80포트 규칙 없음
**확인:**
```bash
gcloud compute firewall-rules list   # default-allow-http 규칙 존재 여부
```
**해결:**
```bash
# 방화벽 규칙 추가
gcloud compute firewall-rules create default-allow-http \
    --allow tcp:80 \
    --target-tags http-server

# VM에 태그 추가
gcloud compute instances add-tags blog-aggregator \
    --zone=us-central1-a --tags=http-server
```

## 7. Oracle Cloud와 차이점

| | Oracle Cloud | GCP |
|--|-------------|-----|
| 업로드 | `upload.sh` (IP + SSH키) | `upload_gcp.sh` (인스턴스명) |
| SSH 사용자 | `ubuntu` (고정) | Google 계정명 (자동) |
| SSH 키 | 수동 관리 | `gcloud` 자동 |
| 방화벽 | iptables + Security List (수동) | 콘솔 체크박스 or CLI |
| iptables REJECT | 있음 (수동 수정) | 없음 |
| 메모리 | 6GB | 1GB |
| 외부 IP | 무료 | 유동 IP 무료, 고정 IP ~$3.60/월 |
| 무료 기간 | 영구 | 90일 크레딧 후 유료 |

## 8. 비용

| 기간 | 항목 | 비용 |
|------|------|------|
| 첫 90일 | 전체 | $0 ($300 크레딧) |
| 이후 | VM (e2-micro) | $0 (Free Tier) |
| 이후 | 유동 외부 IP | $0 (VM 실행 중) |
| 이후 | 고정 외부 IP | ~$3.60/월 |
| 이후 | 디스크 30GB | $0 (Free Tier) |

> 유동 IP는 무료이나 VM 중지 시 IP가 변경될 수 있음.
> 완전 무료 유지: 외부 IP 제거 + Cloudflare Tunnel 사용 (도메인 ~$1/년)
