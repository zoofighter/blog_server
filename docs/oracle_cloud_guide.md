# Oracle Cloud 배포 가이드

## 1. Oracle Cloud 인스턴스 생성

### 1.1 계정 생성
1. https://cloud.oracle.com 접속
2. Free Tier 계정 생성 (신용카드 필요, 과금 없음)

### 1.2 VM 인스턴스 생성
1. OCI 콘솔 → **Compute** → **Instances** → **Create instance**
2. 설정:
   - **Name**: blog-aggregator
   - **Image**: Ubuntu 22.04 (Canonical)
   - **Shape**: VM.Standard.A1.Flex (Ampere) → **1 OCPU, 6GB RAM** (Always Free)
   - **Networking**: 기본 VCN 자동 생성
   - **SSH Key**: 공개키 업로드 또는 생성
3. **Create** 클릭

### 1.3 SSH 키 생성 (없는 경우)
```bash
ssh-keygen -t ed25519 -f ~/.ssh/oracle_key -C "oracle-cloud"
# 공개키 복사하여 인스턴스 생성 시 붙여넣기
cat ~/.ssh/oracle_key.pub
```

### 1.4 방화벽 규칙 (Security List)
OCI 콘솔 → **Networking** → **Virtual Cloud Networks** → VCN 클릭 → **Security Lists** → Default:

**Ingress Rule 추가:**
| Source CIDR | Protocol | Port | 설명 |
|-------------|----------|------|------|
| 0.0.0.0/0 | TCP | 80 | HTTP |

## 2. SSH 접속

```bash
# 인스턴스의 Public IP 확인 (OCI 콘솔 → Instances → 상세)
ssh -i ~/.ssh/oracle_key ubuntu@<서버IP>
```

## 3. 배포

### 3.1 로컬에서 업로드
```bash
# 프로젝트 루트에서 실행
bash deploy/upload.sh <서버IP> ~/.ssh/oracle_key
```

### 3.2 서버에서 셋업 (첫 배포만)
```bash
ssh -i ~/.ssh/oracle_key ubuntu@<서버IP>
sudo bash /opt/blog-aggregator/deploy/setup.sh
```

### 3.3 비밀번호 설정
```bash
sudo nano /etc/systemd/system/blog-aggregator.service
# ADMIN_PASSWORD, SECRET_KEY 변경

sudo systemctl daemon-reload
sudo systemctl restart blog-aggregator
```

### 3.4 접속 확인
```
http://<서버IP>/           → 공개 페이지
http://<서버IP>/admin/     → 관리자 페이지
```

## 4. 운영 명령어

```bash
# 서비스 상태 확인
sudo systemctl status blog-aggregator

# 로그 확인 (실시간)
sudo journalctl -u blog-aggregator -f

# 서비스 재시작
sudo systemctl restart blog-aggregator

# Nginx 상태
sudo systemctl status nginx
sudo nginx -t  # 설정 검증
```

## 5. 코드 업데이트 시

```bash
# 1. 로컬에서 업로드
bash deploy/upload.sh <서버IP> ~/.ssh/oracle_key

# 2. 서버에서 재시작
ssh -i ~/.ssh/oracle_key ubuntu@<서버IP> 'sudo systemctl restart blog-aggregator'
```

## 6. 트러블슈팅

### 6.1 HEAD 405 Method Not Allowed

#### 증상
배포 후 브라우저 접속 불가. Nginx 로그:
```
"HEAD / HTTP/1.1" 405 0
"GET / HTTP/1.1" 200
```

#### 로컬에서는 안 나고 서버에서만 발생한 이유

| 환경 | HEAD 요청 | 이유 |
|------|-----------|------|
| 로컬 | X | 브라우저는 GET만 전송 |
| 서버 | O | Nginx가 upstream 헬스체크 시 HEAD 전송 |

- FastAPI `@router.get("/")`는 GET만 처리, HEAD 자동 처리 안 함
- HEAD → 405 → Nginx가 upstream 비정상 판단 → 프록시 실패

#### 수정: `src/api/app.py`

ASGI 미들웨어로 HEAD를 GET으로 변환:
```python
class HeadMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "HEAD":
            scope["method"] = "GET"
        await self.app(scope, receive, send)

app.add_middleware(HeadMiddleware)
```

> `@app.middleware("http")` 방식은 라우팅 이후 실행되어 효과 없음. ASGI 레벨 미들웨어(`app.add_middleware`)는 라우팅 이전에 실행되므로 정상 동작.

---

## 7. 비용

| 항목 | 비용 |
|------|------|
| Ampere A1 (1 OCPU, 6GB) | $0 (Always Free) |
| Block Storage (50GB) | $0 (Always Free) |
| 네트워크 (10TB/월) | $0 (Always Free) |
| **합계** | **$0/월** |
