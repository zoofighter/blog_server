# 블로그 애그리게이션 플랫폼 - 구현 요약

**작성일**: 2026-03-06
**상태**: Phase 1 MVP 구현 완료

---

## 1. 프로젝트 개요

개인용 블로그 애그리게이션 플랫폼. 100개 블로그에서 콘텐츠를 수집·요약하여 큐레이션 블로그를 운영한다.

### 핵심 결정 사항
| 항목 | 결정 |
|------|------|
| 운영 방식 | Phase 1: 수동 관리 → Phase 2: 자동화 |
| 호스팅 | Oracle Cloud Free Tier (Ampere A1) |
| 프론트엔드 | Jinja2 서버 렌더링 + Tailwind CDN |
| 인증 | 환경변수 비밀번호 (개인용) |
| LLM 사용처 | 요약 생성만 (OpenAI gpt-4o-mini) |
| 분류/태깅 | 키워드 규칙 기반 (LLM 미사용) |

---

## 2. 구현된 파일 구조

```
a_0306_blog/
├── main.py                     # 앱 진입점 (uvicorn)
├── config.yaml                 # 설정 (DB, OpenAI, 관리자 비밀번호, 카테고리)
├── requirements.txt            # Python 의존성 10개
│
├── src/
│   ├── database/
│   │   ├── models.py           # SQLite 스키마 (blogs, posts, tags, post_tags)
│   │   └── repository.py      # Repository 클래스 - CRUD, 검색, 필터, 통계
│   ├── services/
│   │   ├── extractor.py        # URL → 메타데이터 추출 (og:title, 본문, 이미지)
│   │   ├── summarizer.py       # OpenAI 2-3문장 요약 + 폴백(첫 200자)
│   │   └── classifier.py       # 키워드 기반 카테고리 분류 + 태그 추출
│   └── api/
│       ├── app.py              # FastAPI 앱 생성, 미들웨어, 라우터 등록
│       ├── public.py           # 공개 라우트: 메인(카드 그리드), 상세, 검색
│       └── admin.py            # 관리자 라우트: 로그인, 대시보드, CRUD, 요약
│
├── templates/
│   ├── base.html               # 공통 레이아웃 (다크모드 토글, 네비게이션)
│   ├── index.html              # 메인 페이지 - 카드 그리드 (반응형 3/2/1단)
│   ├── post_detail.html        # 포스트 상세 (요약 + 원문 링크 + 관련 글)
│   └── admin/
│       ├── login.html          # 비밀번호 로그인
│       ├── dashboard.html      # 통계 대시보드 (포스트 수, 카테고리 분포)
│       ├── posts.html          # 포스트 관리 목록 (테이블)
│       ├── post_form.html      # 포스트 등록/수정 폼 (URL 추출 + AI 요약)
│       └── blogs.html          # 블로그 소스 관리 (추가/삭제/토글)
│
├── static/style.css            # 최소 커스텀 CSS (line-clamp, 스크롤바)
├── deploy/
│   ├── nginx.conf              # Nginx 리버스 프록시 + SSL 설정
│   └── blog-aggregator.service # systemd 서비스 파일
│
├── data/blog.db                # SQLite DB (자동 생성)
└── dosc/                       # 문서
    ├── prev_requirements.md    # 초기 요건정의서 v1
    ├── requirements_v2.md      # 수정된 요건정의서 v2
    └── implementation_summary.md  # 이 문서
```

---

## 3. 주요 기능

### 공개 페이지 (`/`)
- 카드 형식 타임라인 뷰 (반응형: 데스크탑 3단, 태블릿 2단, 모바일 1단)
- 카테고리 탭 필터 (art, ml, programming, data, tech, essay, other)
- 태그 필터, 전체 텍스트 검색
- 페이지네이션
- 포스트 상세 페이지 (요약 + 원문 링크 + 관련 글 추천)
- 다크모드 토글 (시스템 설정 자동 감지)

### 관리자 페이지 (`/admin/`)
- 비밀번호 인증 (환경변수 `ADMIN_PASSWORD`)
- **대시보드**: 총 포스트 수, 활성 블로그 수, 카테고리별 분포 차트, 최근 등록 이력
- **포스트 등록 플로우**:
  1. URL 입력 → [추출] 버튼 → 메타데이터 자동 채움 (제목, 본문, 이미지, 작성자, 발행일)
  2. 카테고리 자동 분류 (수동 수정 가능)
  3. [AI 요약 생성] 버튼 → OpenAI로 2-3문장 요약
  4. 확인 후 저장
- **포스트 관리**: 목록 조회, 수정, 삭제
- **블로그 소스 관리**: 추가, 활성화/비활성화 토글, 삭제

---

## 4. 기술 스택

| 계층 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| 웹 프레임워크 | FastAPI |
| 템플릿 | Jinja2 |
| CSS | Tailwind CSS (CDN) |
| 데이터베이스 | SQLite |
| HTTP 클라이언트 | httpx (async) |
| HTML 파싱 | BeautifulSoup4 + lxml |
| AI 요약 | OpenAI API (gpt-4o-mini) |
| 인증 | itsdangerous (세션), 환경변수 비밀번호 |
| 배포 | Nginx + systemd (Oracle Cloud) |

### 주요 의존성 (requirements.txt)
```
fastapi, uvicorn, jinja2, httpx, beautifulsoup4,
openai, python-multipart, pyyaml, itsdangerous, lxml
```

---

## 5. 데이터베이스 스키마

```sql
blogs     -- 블로그 소스 (id, name, url, feed_url, category, active, description)
posts     -- 포스트 (id, blog_id, title, original_url, summary, full_content,
          --         author, published_date, image_url, category, language,
          --         summary_status, registered_by, created_at)
tags      -- 태그 (id, name)
post_tags -- 포스트-태그 연결 (post_id, tag_id)
```

- `summary_status`: pending / completed / failed
- `registered_by`: manual (Phase 1) / auto (Phase 2)
- `language`: ko / en

---

## 6. API 라우트 목록

### 공개
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 메인 타임라인 (필터/검색/페이지네이션) |
| GET | `/post/{id}` | 포스트 상세 |

### 관리자
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

---

## 7. 실행 방법

```bash
# 가상환경 활성화
source venv/bin/activate

# 환경변수 설정
export ADMIN_PASSWORD=your-password
export OPENAI_API_KEY=sk-...       # AI 요약 사용 시
export SECRET_KEY=random-string    # 세션 암호화

# 서버 시작
python main.py
# → http://localhost:8000      (공개 페이지)
# → http://localhost:8000/admin/  (관리자)
```

---

## 8. 검증 결과

| 항목 | 상태 |
|------|------|
| 의존성 설치 | 완료 |
| 앱 생성 | 완료 (`from main import app` 성공) |
| 서버 시작 | 완료 (uvicorn 정상 기동) |
| 메인 페이지 (GET /) | 200 OK |
| 로그인 페이지 (GET /admin/login) | 200 OK |
| 로그인 인증 (POST /admin/login) | 302 Redirect (성공) |
| 미인증 접근 차단 | 302 → /admin/login |
| DB 자동 생성 | 완료 (data/blog.db) |

---

## 9. Phase 2 계획 (향후)

- [ ] RSS/Atom 자동 크롤링 (feedparser + APScheduler)
- [ ] 100개 블로그 RSS 피드 등록
- [ ] 자동 중복 제거
- [ ] 자동 품질 필터링
- [ ] 북마크 / 읽음 표시
- [ ] 캐싱 최적화
- [ ] 관련 글 추천 알고리즘 개선
- [ ] 프론트엔드 업그레이드 (React SPA 등)

---

## 10. 참고

- 기존 주식 프로젝트(`0224_a`)의 DB/API 패턴 재활용
  - `models.py`: get_connection, init_db 패턴
  - `repository.py`: Repository 클래스 구조
  - `api.py`: FastAPI 앱 구조, CORS, lifespan 패턴
  - `config.yaml`: YAML 설정 구조
