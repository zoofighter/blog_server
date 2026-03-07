# GCP 배포 트러블슈팅 기록

## 1. SSH Permission Denied

### 증상
```
ubuntu@34.67.226.176: Permission denied (publickey).
```

### 원인
- `upload.sh`가 `SSH_USER="ubuntu"`로 고정 (Oracle Cloud 전용)
- GCP Ubuntu 이미지의 기본 사용자명은 Google 계정 이메일의 `@` 앞부분

### 해결
- Oracle Cloud용 `upload.sh` 대신 GCP용 `upload_gcp.sh` 생성
- `gcloud compute scp` 사용 → IP, SSH 키, 사용자명 자동 처리

---

## 2. gcloud compute scp --exclude 미지원

### 증상
`gcloud compute scp --exclude` 옵션이 존재하지 않아 실행 실패

### 원인
- `gcloud compute scp`는 `scp` 래퍼로, rsync의 `--exclude` 옵션 미지원

### 해결
`upload_gcp.sh`를 tar 방식으로 변경:
1. 로컬에서 tar 압축 (불필요 파일 제외)
2. `gcloud compute scp`로 tar 파일 전송
3. 서버에서 압축 해제

---

## 3. PERMISSION_DENIED: compute.googleapis.com

### 증상
```
ERROR: (gcloud.compute.scp) PERMISSION_DENIED: Permission denied to enable service [compute.googleapis.com]
```

### 원인
존재하지 않는 프로젝트 ID가 설정되어 있었음:
```
gcloud config set project blog-aggregator  ← 프로젝트 목록에 없는 ID
```

`gcloud projects list` 결과에 `blog-aggregator`가 없었음.

### 해결
새 프로젝트 생성 → 결제 연결 → API 활성화:
```bash
gcloud projects create blog-agg-2026 --name="Blog Aggregator"
gcloud config set project blog-agg-2026
gcloud billing projects link blog-agg-2026 --billing-account=<결제계정ID>
gcloud services enable compute.googleapis.com
```

### 참고
- GCP 프로젝트 ID는 **전 세계에서 유일**해야 함
- `blog-aggregator`는 이미 다른 사람이 사용 중
- 프로젝트 ID와 프로젝트 이름은 다름 (ID가 고유)

---

## 4. gcloud CLI 미설치

### 증상
`gcloud` 명령어를 찾을 수 없음

### 해결
```bash
brew install google-cloud-sdk
gcloud auth login
gcloud config set project <프로젝트ID>
```

---

## 5. sqlite3.OperationalError: unable to open database file

### 증상
```
sqlite3.OperationalError: unable to open database file
```
앱 시작 시 DB 파일을 열 수 없어 크래시

### 원인
- `upload_gcp.sh`에서 `data/blog.db`를 제외하고 업로드
- `data/` 디렉토리 안에 다른 파일이 없으면 tar에 포함되지 않음
- 서버에 `data/` 디렉토리 자체가 존재하지 않음

### 해결
```bash
gcloud compute ssh blog-aggregator --zone=us-central1-a \
    --command="mkdir -p /opt/blog-aggregator/data && sudo systemctl restart blog-aggregator"
```

`deploy/setup.sh`에도 `mkdir -p $APP_DIR/data` 추가하여 재발 방지.

---

## Oracle Cloud vs GCP 배포 차이 요약

| 항목 | Oracle Cloud | GCP |
|------|-------------|-----|
| 업로드 스크립트 | `upload.sh` (IP + SSH키) | `upload_gcp.sh` (인스턴스명) |
| SSH 사용자 | `ubuntu` (고정) | Google 계정명 (자동) |
| SSH 키 관리 | 수동 (키 파일) | `gcloud` 자동 |
| 방화벽 | iptables + Security List | 콘솔 체크박스 |
| API 활성화 | 불필요 | Compute Engine API 활성화 필요 |
| 프로젝트/결제 | 불필요 | 프로젝트 생성 + 결제 연결 필요 |

---

## GCP 배포 전 체크리스트

```bash
# 1. gcloud 설치 확인
gcloud --version

# 2. 로그인
gcloud auth login

# 3. 프로젝트 확인 (목록에 있는 ID 사용)
gcloud projects list
gcloud config set project <프로젝트ID>

# 4. 결제 연결 확인
gcloud billing projects describe <프로젝트ID>

# 5. Compute Engine API 활성화
gcloud services enable compute.googleapis.com

# 6. VM 인스턴스 존재 확인
gcloud compute instances list

# 7. 배포
bash deploy/upload_gcp.sh <인스턴스명> <영역>
```

=====

3. 프로젝트 업로드

bash deploy/upload_gcp.sh blog-aggregator us-central1-a
4. 서버 셋업

gcloud compute ssh blog-aggregator --zone=us-central1-a
sudo bash /opt/blog-aggregator/deploy/setup.sh
5. 접속 확인

# 외부 IP 확인
gcloud compute instances list
# 브라우저에서 http://<외부IP>/ 접속