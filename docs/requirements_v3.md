# 개인용 블로그 애그리게이션 플랫폼 요건정의서 v3

## 1. 프로젝트 개요

### 1.1 목적
100개의 블로그(아트, 머신러닝 등 다양한 주제)에서 콘텐츠를 수집하고 요약하여 개인 큐레이션 블로그 구축

### 1.2 핵심 특징
- **규모**: 100개 블로그 소스 (현재 35개 등록 완료)
- **콘텐츠 형태**: AI 요약본 표시 + 원문 링크
- **운영 방식**: Phase 1 수동 큐레이션 (완료) → Phase 2 자동화 (예정)
- **사용자**: 개인용 (본인만 사용)
- **주제**: art, ml, programming, data, tech, essay, other
- **호스팅**: Oracle Cloud Free Tier (Ampere A1)

### 1.3 개발 단계

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 1 | 수동 블로그/포스트 관리 MVP | **완료** |
| Phase 2 | RSS 크롤링 + 스케줄러 자동화 | 예정 |
| Phase 3 | 고도화 (캐싱, 추천, PWA 등) | 미정 |

---

## 2. 확정된 기술 스택

### 2.1 백엔드

| 항목 | 기술 | 비고 |
|------|------|------|
| 언어 | Python 3.9+ | |
| 웹 프레임워크 | FastAPI | 비동기, 자동 API 문서 |
| HTTP 클라이언트 | httpx (async) | URL 메타데이터 추출 |
| HTML 파싱 | BeautifulSoup4 + lxml | og:tags, 본문 추출 |
| 데이터베이스 | SQLite | 개인용 충분, 파일 기반 |
| 세션 관리 | itsdangerous | 서명 기반 쿠키 세션 |
| 설정 | PyYAML | config.yaml |

### 2.2 AI 요약 (멀티 프로바이더)

config.yaml의 `llm.provider`로 선택:

| 프로바이더 | 모델 | 용도 |
|-----------|------|------|
| **openai** (기본) | gpt-4o-mini | 클라우드 API, ~$0.10-0.20/월 |
| claude | claude-haiku-4-5 | Anthropic API 대안 |
| ollama | llama3 | 로컬 실행, 무료 |
| none | - | AI 미사용, 첫 200자 폴백 |

**LLM 사용처**: 요약 생성만 (분류/태깅은 키워드 규칙 기반)

### 2.3 프론트엔드

| 항목 | 기술 | 비고 |
|------|------|------|
| 템플릿 | Jinja2 (서버 렌더링) | 추후 React SPA 업그레이드 가능 |
| CSS | Tailwind CSS (CDN) | 빌드 불필요 |
| 레이아웃 | 반응형 카드 그리드 | 3단/2단/1단 |
| 다크모드 | 시스템 설정 + 수동 토글 | localStorage 저장 |

### 2.4 호스팅 (Oracle Cloud Free Tier)

```yaml
컴퓨트: Ampere A1 (최대 4 OCPU, 24GB RAM)
스토리지: Block Volume 200GB
네트워크: 10TB/월 아웃바운드
SSL: Let's Encrypt (무료)
웹 서버: Nginx 리버스 프록시
프로세스 관리: systemd
```

### 2.5 인증
- 환경변수 `ADMIN_PASSWORD`로 관리자 비밀번호 설정
- itsdangerous 서명 쿠키 기반 세션
- 개인용이므로 OAuth 불필요

---

## 3. 구현 완료 기능 (Phase 1)

### 3.1 공개 페이지

#### 메인 타임라인 (`GET /`)
- 카드 형식 그리드 레이아웃 (대표 이미지, 제목, 요약, 출처, 발행일)
- 카테고리 탭 필터 (All, Art, ML, Programming, Data, Tech, Essay, Other)
- 태그 필터
- 전체 텍스트 검색 (제목 + 요약)
- 페이지네이션 (20건/페이지)
- 반응형: 데스크탑 3단 → 태블릿 2단 → 모바일 1단

#### 포스트 상세 (`GET /post/{id}`)
- AI 요약 표시
- 원문 링크 ("원문 보기" 버튼)
- 원작자 크레딧
- 관련 글 추천 (같은 카테고리)

#### 다크모드
- 시스템 설정 자동 감지
- 수동 토글 (localStorage 저장)

### 3.2 관리자 페이지

#### 인증
- 비밀번호 로그인 (`/admin/login`)
- 세션 기반 접근 제어 (미인증 시 리디렉트)

#### 대시보드 (`/admin/`)
- 총 포스트 수, 활성 블로그 수
- 카테고리별 분포
- 최근 등록 이력

#### 포스트 수동 등록 플로우
```
1. URL 입력 → [메타데이터 추출] 버튼 (AJAX)
   → 제목, 본문, 이미지, 작성자, 발행일 자동 채움
2. 소스 블로그 선택 (드롭다운)
3. 카테고리 자동 분류 (키워드 기반, 수동 수정 가능)
4. [AI 요약 생성] 버튼 (AJAX)
   → 2-3문장 요약 자동 생성
5. 확인/수정 후 [저장]
```

#### 포스트 관리
- 목록 조회 (테이블)
- 수정, 삭제

#### 블로그 소스 관리
- 블로그 추가 (이름, URL, 피드URL, 카테고리, 설명)
- 활성/비활성 토글
- 삭제
- **CSV 일괄 관리**:
  - CSV 내보내기 (UTF-8 BOM, 엑셀 호환)
  - CSV 가져오기 (중복 URL 자동 스킵)
  - CSV 템플릿 다운로드

### 3.3 서비스 계층

#### URL 메타데이터 추출 (`extractor.py`)
- httpx async 요청 → BeautifulSoup 파싱
- 추출 항목: og:title, article 본문, og:image, meta author, 발행일
- 타임아웃 15초, User-Agent 설정

#### AI 요약 (`summarizer.py`)
- 멀티 프로바이더 (openai / claude / ollama / none)
- 본문 3000자 제한 후 요약 요청
- 시스템 프롬프트: 2-3문장 요약, 기술 용어 보존, 사실 중심, 원문 언어 유지
- 폴백: 첫 200자 자르기

#### 카테고리 분류 + 태그 추출 (`classifier.py`)
- 키워드 매칭 기반 카테고리 자동 분류 (LLM 미사용)
- 정규식 기반 단어 빈도 태그 추출 (최대 5개)
- 카테고리: art, ml, programming, data, tech, essay, other

---

## 4. 프로젝트 구조

```
a_0306_blog/
├── main.py                     # 앱 진입점 (uvicorn)
├── config.yaml                 # 설정 (DB, LLM, 관리자, 서버, 카테고리)
├── requirements.txt            # Python 의존성
│
├── src/
│   ├── database/
│   │   ├── models.py           # SQLite 스키마 (blogs, posts, tags, post_tags)
│   │   └── repository.py       # Repository 클래스 - CRUD, 검색, 필터, 통계
│   ├── services/
│   │   ├── extractor.py        # URL → 메타데이터 추출
│   │   ├── summarizer.py       # 멀티 프로바이더 AI 요약
│   │   └── classifier.py       # 키워드 기반 분류 + 태그
│   └── api/
│       ├── app.py              # FastAPI 앱 생성, 미들웨어
│       ├── public.py           # 공개 라우트
│       └── admin.py            # 관리자 라우트
│
├── templates/
│   ├── base.html               # 공통 레이아웃
│   ├── index.html              # 메인 카드 그리드
│   ├── post_detail.html        # 포스트 상세
│   └── admin/
│       ├── login.html          # 로그인
│       ├── dashboard.html      # 대시보드
│       ├── posts.html          # 포스트 관리
│       ├── post_form.html      # 포스트 등록/수정 폼
│       └── blogs.html          # 블로그 소스 관리 + CSV
│
├── static/style.css            # 커스텀 CSS (최소)
├── deploy/
│   ├── nginx.conf              # Nginx 설정
│   └── blog-aggregator.service # systemd 서비스
│
├── data/
│   ├── blog.db                 # SQLite DB (자동 생성)
│   └── blogs_sample.csv        # 샘플 블로그 CSV
│
└── docs/
    ├── prev_requirements.md    # 요건정의서 v1
    ├── requirements_v2.md      # 요건정의서 v2
    ├── requirements_v3.md      # 요건정의서 v3 (이 문서)
    ├── implementation_summary.md  # 구현 요약
    └── prev_list.csv           # 초기 블로그 URL 목록 (35개)
```

---

## 5. 데이터베이스 스키마

```sql
-- 블로그 소스
CREATE TABLE blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    feed_url TEXT,
    category TEXT DEFAULT 'other',
    active BOOLEAN DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포스트
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blog_id INTEGER REFERENCES blogs(id),
    title TEXT NOT NULL,
    original_url TEXT UNIQUE NOT NULL,
    summary TEXT,
    full_content TEXT,
    author TEXT,
    published_date TEXT,
    image_url TEXT,
    category TEXT DEFAULT 'other',
    language TEXT DEFAULT 'ko',
    summary_status TEXT DEFAULT 'pending',  -- pending / completed / failed
    registered_by TEXT DEFAULT 'manual',    -- manual / auto
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 태그
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- 포스트-태그 연결
CREATE TABLE post_tags (
    post_id INTEGER REFERENCES posts(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (post_id, tag_id)
);
```

---

## 6. API 라우트

### 공개

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 메인 타임라인 (카테고리/태그 필터, 검색, 페이지네이션) |
| GET | `/post/{id}` | 포스트 상세 |

### 관리자 (인증 필요)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET/POST | `/admin/login` | 로그인 |
| GET | `/admin/logout` | 로그아웃 |
| GET | `/admin/` | 대시보드 |
| GET | `/admin/posts` | 포스트 목록 |
| GET | `/admin/posts/new` | 등록 폼 |
| POST | `/admin/posts/extract` | URL 메타데이터 추출 (AJAX) |
| POST | `/admin/posts/summarize` | AI 요약 생성 (AJAX) |
| POST | `/admin/posts` | 포스트 저장 |
| GET | `/admin/posts/{id}/edit` | 수정 폼 |
| POST | `/admin/posts/{id}` | 포스트 수정 |
| POST | `/admin/posts/{id}/delete` | 포스트 삭제 |
| GET | `/admin/blogs` | 블로그 소스 목록 |
| POST | `/admin/blogs` | 블로그 추가 |
| POST | `/admin/blogs/{id}/delete` | 블로그 삭제 |
| POST | `/admin/blogs/{id}/toggle` | 활성/비활성 토글 |
| GET | `/admin/blogs/export` | CSV 내보내기 |
| POST | `/admin/blogs/import` | CSV 가져오기 |
| GET | `/admin/blogs/template` | CSV 템플릿 다운로드 |

---

## 7. 설정 파일 (`config.yaml`)

```yaml
database:
  path: "data/blog.db"

llm:
  provider: "openai"  # openai | claude | ollama | none

  openai:
    api_key: ""        # 환경변수 OPENAI_API_KEY 우선
    model: "gpt-4o-mini"
    temperature: 0.3
    max_tokens: 200

  claude:
    api_key: ""        # 환경변수 ANTHROPIC_API_KEY 우선
    model: "claude-haiku-4-5-20251001"
    max_tokens: 200

  ollama:
    base_url: "http://localhost:11434"
    model: "llama3"

admin:
  password: "0000"     # 환경변수 ADMIN_PASSWORD 우선

server:
  host: "0.0.0.0"
  port: 8000

categories:
  - art
  - ml
  - programming
  - data
  - tech
  - essay
  - other
```

---

## 8. 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export ADMIN_PASSWORD=your-password
export OPENAI_API_KEY=sk-...       # AI 요약 사용 시
export SECRET_KEY=random-string    # 세션 암호화

# 서버 시작
python main.py
# → http://localhost:8000        (공개 페이지)
# → http://localhost:8000/admin/ (관리자 페이지)
```

---

## 9. 현재 상태

### 등록된 블로그 (35개)

| 플랫폼 | 수 |
|--------|-----|
| Naver 블로그 | 20 |
| Brunch | 6 |
| Tistory | 3 |
| 기타 (yozm, kmu1988 등) | 6 |

### Phase 1 검증 결과

| 항목 | 상태 |
|------|------|
| 의존성 설치 | 완료 |
| 앱 생성 및 서버 기동 | 완료 |
| 메인 페이지 (GET /) | 200 OK |
| 관리자 로그인 | 302 Redirect (성공) |
| 미인증 접근 차단 | 302 → /admin/login |
| DB 자동 생성 | 완료 |
| 블로그 35개 등록 | 완료 |
| CSV 가져오기/내보내기 | 완료 |
| 멀티 LLM 프로바이더 | 완료 |

---

## 10. Phase 2 계획: RSS 자동화

### 10.1 개요
등록된 블로그의 RSS/Atom 피드를 주기적으로 크롤링하여 신규 포스트를 자동 수집·요약·분류한다.

### 10.2 신규 컴포넌트

```
src/
├── services/
│   ├── crawler.py        # RSS 크롤러 (feedparser)
│   └── feed_finder.py    # RSS 피드 URL 자동 탐색
└── scheduler.py          # APScheduler 설정
```

### 10.3 RSS 크롤러 (`crawler.py`)
```yaml
기능:
  - feedparser로 RSS/Atom 파싱
  - 신규 포스트 감지 (URL 중복 확인)
  - 포스트별 처리: 메타데이터 추출 → AI 요약 → 카테고리 분류 → 태그 → DB 저장
  - 크롤링 로그 기록

에러 처리:
  - 피드 접근 불가: 로그 기록 후 스킵
  - 요약 실패: 폴백 (첫 200자)
  - 개별 포스트 실패: 해당 건만 스킵, 나머지 계속 처리
```

### 10.4 피드 탐색 (`feed_finder.py`)
```yaml
기능:
  - 블로그 URL에서 RSS 피드 URL 자동 탐색
  - <link rel="alternate" type="application/rss+xml"> 태그 탐색
  - 일반적 피드 경로 시도 (/feed, /rss, /atom.xml 등)
  - 플랫폼별 패턴 (Naver, Tistory, Brunch, Medium 등)
```

### 10.5 스케줄러 (`scheduler.py`)
```yaml
APScheduler (BackgroundScheduler):
  기본 주기: 3시간마다 전체 블로그 크롤링
  활성(active=true) 블로그만 대상
  동시 실행 방지 (max_instances=1)
```

### 10.6 DB 변경

```sql
-- 크롤링 로그 (신규 테이블)
CREATE TABLE crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blog_id INTEGER REFERENCES blogs(id),
    status TEXT,            -- success / failed
    posts_found INTEGER DEFAULT 0,
    posts_added INTEGER DEFAULT 0,
    error_message TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- blogs 테이블 컬럼 추가
ALTER TABLE blogs ADD COLUMN last_crawled_at TIMESTAMP;
ALTER TABLE blogs ADD COLUMN crawl_error TEXT;
```

### 10.7 관리자 UI 변경
- 대시보드에 크롤링 상태/로그 표시
- 블로그별 "지금 크롤링" 수동 트리거 버튼
- 크롤링 성공률, 마지막 크롤링 시각 표시
- 피드 URL 자동 탐색 버튼

### 10.8 추가 의존성
```
feedparser>=6.0
apscheduler>=3.10
```

---

## 11. Phase 3 계획 (미정)

- [ ] 캐싱 최적화 (Redis 또는 인메모리)
- [ ] 이미지 최적화 (리사이징, 지연 로딩)
- [ ] 관련 글 추천 알고리즘 개선 (임베딩 기반)
- [ ] 북마크 / 읽음 표시
- [ ] 이메일 다이제스트 (주간 요약)
- [ ] 자체 RSS 피드 제공
- [ ] PWA
- [ ] 프론트엔드 업그레이드 (React SPA)
- [ ] 중복 제거 고도화 (제목 유사도)
- [ ] 품질 필터링 (광고성/스팸 자동 제외)

---

## 12. 비용 예측

```yaml
Oracle Cloud (호스팅):
  - 컴퓨트 (Ampere A1): $0 (Always Free)
  - 스토리지 (200GB): $0 (Always Free)
  - 네트워크 (10TB/월): $0 (Always Free)
  - SSL (Let's Encrypt): $0

LLM API (요약):
  Phase 1 (수동): 월 ~300건 × ~$0.0003 = ~$0.10/월
  Phase 2 (자동): 월 ~9000건 × ~$0.0003 = ~$3-5/월
  Ollama (대안): $0 (로컬 실행)

도메인 (선택):
  - 무료: Oracle Cloud IP 직접 사용
  - 유료: 연 $10-15

총 예상 비용:
  Phase 1: $0-1/월
  Phase 2: $3-5/월
```

---

## 13. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Oracle Cloud VM 리소스 제한 | 성능 저하 | Ampere A1 활용, 경량 스택 |
| AI API 비용 초과 | 예산 오버 | Ollama 전환 가능, none 옵션 |
| 블로그 구조 변경 (Phase 2) | 크롤링 실패 | 에러 모니터링, 파서 업데이트 |
| 저작권 | 법적 문제 | 요약만 표시, 원문 링크 필수, 개인용 |
| 서버 다운 | 서비스 중단 | systemd 자동 재시작, 로그 모니터링 |

---

## 14. 참고

### 재활용한 패턴 (기존 주식 프로젝트 `0224_a`)
| 원본 파일 | 재활용 내용 |
|-----------|------------|
| `src/database/models.py` | get_connection(), init_db() 패턴 |
| `src/database/repository.py` | Repository 클래스 구조, CRUD 패턴 |
| `api.py` | FastAPI 앱 구조, CORS, lifespan |
| `config.yaml` | YAML 설정 구조 |

### 주요 의존성
```
fastapi>=0.115    uvicorn[standard]>=0.30    jinja2>=3.1
httpx>=0.27       beautifulsoup4>=4.12       lxml>=5.0
openai>=1.50      python-multipart>=0.0.9    pyyaml>=6.0
itsdangerous>=2.1
```

---

**문서 버전**: 3.0
**작성일**: 2026-03-06
**주요 변경**: Phase 1 구현 완료 반영, 기술 스택 확정, 멀티 LLM 프로바이더, CSV 관리, Phase 2 상세 계획
**이전 버전**: requirements_v2.md
