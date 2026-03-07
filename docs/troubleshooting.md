# 배포 트러블슈팅 기록

## 1. HEAD 405 Method Not Allowed

### 증상
배포 후 Nginx 로그에 HEAD 요청이 405 반환:
```
"HEAD / HTTP/1.0" 405 Method Not Allowed
"GET / HTTP/1.0" 200 OK
```

### 원인
- Nginx가 upstream(FastAPI) 헬스체크 시 HEAD 요청을 보냄
- FastAPI `@router.get("/")`는 GET만 처리하고 HEAD를 자동 처리하지 않음
- 로컬에서는 브라우저(GET만 사용)로 테스트하므로 발생하지 않음

### 시도한 수정 (실패)

**1차: `@app.middleware("http")` 방식**
```python
@app.middleware("http")
async def head_to_get(request, call_next):
    if request.method == "HEAD":
        request.scope["method"] = "GET"
    return await call_next(request)
```
- 결과: 실패 (HEAD 여전히 405)
- 원인: `@app.middleware("http")`는 라우팅 이후에 실행되어 이미 405 결정 후

**2차: `app.add_middleware()` 방식**
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
- 결과: 실패 (HEAD 여전히 405)
- 원인: `add_middleware` 호출 순서 문제. 가장 먼저 추가하면 가장 안쪽(라우터에 가까운) 미들웨어가 됨. CORSMiddleware, SessionMiddleware가 바깥에서 먼저 요청을 처리

### 최종 수정 (성공): `main.py` ASGI 래퍼

```python
# main.py
_fastapi_app = create_app(config)

async def app(scope, receive, send):
    """HEAD → GET 변환 래퍼. Nginx 헬스체크 호환."""
    if scope["type"] == "http" and scope["method"] == "HEAD":
        scope["method"] = "GET"
    await _fastapi_app(scope, receive, send)
```
- uvicorn이 `main:app`을 호출할 때 가장 먼저 실행
- FastAPI 미들웨어 체인과 무관하게 HEAD가 GET으로 변환됨

### 교훈
- FastAPI `add_middleware()` 순서: 마지막 추가 = 가장 바깥(먼저 실행)
- HTTP 미들웨어(`@app.middleware("http")`)는 라우팅 후 실행되므로 method 변환에 부적합
- 확실한 방법은 ASGI 앱 자체를 감싸는 것

---

## 2. iptables 포트 80 REJECT 순서 문제

### 증상
서버 내부에서는 정상 (curl localhost → 200), 외부에서 접속 불가 (curl → 000):
```bash
curl -s -o /dev/null -w "%{http_code}" http://<서버IP>/
# 결과: 000 (연결 실패)
```

### 원인
Oracle Cloud Ubuntu 기본 iptables 규칙에 REJECT가 포트 80 ACCEPT보다 먼저 위치:
```
4    ACCEPT  tcp  dpt:22          ← SSH 허용
5    REJECT  all                  ← 여기서 모든 트래픽 거부
6    ACCEPT  tcp  dpt:80          ← 도달 불가!
7    ACCEPT  tcp  dpt:80
8    ACCEPT  tcp  dpt:80
```
- `setup.sh`에서 `iptables -I INPUT 6`으로 추가했지만, REJECT가 5번에 있어서 6번 이후 규칙은 실행되지 않음
- iptables는 위에서 아래로 순서대로 처리하므로 REJECT에 먼저 걸림

### 수정
```bash
# 잘못된 위치의 규칙 삭제 (뒤에서부터)
sudo iptables -D INPUT 8
sudo iptables -D INPUT 7
sudo iptables -D INPUT 6

# REJECT(5번) 앞에 삽입
sudo iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT

# 저장
sudo netfilter-persistent save
```

올바른 순서:
```
4    ACCEPT  tcp  dpt:22
5    ACCEPT  tcp  dpt:80          ← REJECT 앞으로 이동
6    REJECT  all
```

### setup.sh 수정 필요
`deploy/setup.sh`의 iptables 명령도 수정 필요:
```bash
# 변경 전 (잘못됨)
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT

# 변경 후 (REJECT 앞에 삽입)
# REJECT 규칙의 위치를 찾아서 그 앞에 삽입
REJECT_LINE=$(iptables -L INPUT --line-numbers -n | grep REJECT | head -1 | awk '{print $1}')
iptables -I INPUT ${REJECT_LINE:-5} -p tcp --dport 80 -j ACCEPT
```

### 교훈
- Oracle Cloud Ubuntu는 기본 iptables에 REJECT 규칙이 포함되어 있음
- 포트 추가 시 반드시 REJECT 규칙 **앞에** 삽입해야 함
- `iptables -I INPUT <N>` 에서 N은 REJECT 규칙의 위치여야 함

---

## 디버깅 체크리스트

외부에서 접속이 안 될 때 순서대로 확인:

```bash
# 1. 앱 직접 테스트
curl http://127.0.0.1:8000/

# 2. Nginx 경유 테스트
curl http://localhost/

# 3. Nginx 상태
sudo systemctl status nginx
sudo nginx -t

# 4. Nginx 에러 로그
sudo tail -20 /var/log/nginx/error.log

# 5. iptables 규칙 순서 확인 (REJECT 위치 주의)
sudo iptables -L INPUT -n --line-numbers

# 6. OCI Security List 확인
# OCI 콘솔 → Networking → VCN → Security Lists → Ingress Rules → TCP 80

# 7. 외부 접속 테스트 (로컬 PC에서)
curl -v --connect-timeout 5 http://<서버IP>/
```
