# Twitter/Threads 소셜 포스트 독립 페이지 구현 계획

## Context
블로그 애그리게이터에 Twitter(X)와 Threads 소셜 포스트를 블로그와 독립적으로 표시하는 기능을 추가한다. 관리자가 수동으로 URL을 붙여넣어 등록하고, `/social` 페이지에서 플랫폼 탭(All/Twitter/Threads)으로 전환하며 카드형 그리드로 30개 이상 표시한다.

## 수정/생성 파일 목록

| Action | File | Description |
|--------|------|-------------|
| Modify | `src/database/models.py` | `social_posts` 테이블 추가 |
| Modify | `src/database/repository.py` | 소셜 포스트 CRUD 메서드 6개 추가 |
| Create | `src/services/social_extractor.py` | Twitter oEmbed / Threads OG태그 메타데이터 추출 |
| Modify | `src/api/public.py` | `GET /social` 라우트 추가 |
| Modify | `src/api/admin.py` | 소셜 관리 라우트 5개 추가 |
| Create | `templates/social.html` | 공개 소셜 페이지 (탭 + 카드 그리드) |
| Create | `templates/admin/social.html` | 관리자 소셜 포스트 목록 |
| Create | `templates/admin/social_form.html` | 관리자 소셜 포스트 등록 폼 |
| Modify | `templates/base.html` | 네비게이션에 "Social" 링크 추가 |
| Modify | `templates/admin/*.html` (5개) | 관리자 네비게이션에 "소셜" 링크 추가 |

## 구현 상세

### 1. DB 스키마 - `src/database/models.py`
`init_db()`의 `executescript` 블록에 추가:
```sql
CREATE TABLE IF NOT EXISTS social_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK(platform IN ('twitter', 'threads')),
    original_url TEXT UNIQUE NOT NULL,
    author_handle TEXT,
    author_name TEXT,
    content TEXT,
    image_url TEXT,
    embed_html TEXT,
    posted_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_posted ON social_posts(posted_date DESC);
```

### 2. Repository - `src/database/repository.py`
`# --- social posts ---` 섹션 추가, 메서드 6개:
- `create_social_post(platform, original_url, author_handle, author_name, content, image_url, embed_html, posted_date) -> int`
- `get_social_posts(platform=None, page=1, per_page=30) -> tuple[list[dict], int]`
- `get_social_post(post_id) -> Optional[dict]`
- `delete_social_post(post_id) -> None`
- `social_post_exists_url(url) -> bool`
- `get_social_post_counts() -> dict` (total, twitter, threads)

### 3. 메타데이터 추출 서비스 - `src/services/social_extractor.py` (신규)
- `detect_platform(url)` - URL에서 twitter/threads 판별 (x.com, twitter.com, threads.net)
- `extract_social_metadata(url)` - 플랫폼별 분기
- Twitter: `https://publish.twitter.com/oembed?url=...` oEmbed API
- Threads: HTML fetch 후 `og:description`, `og:image` OG 태그 파싱
- URL에서 핸들 추출: `@username` 정규식
- 기존 `httpx`, `beautifulsoup4` 의존성 사용 (추가 설치 불필요)

### 4. 공개 라우트 - `src/api/public.py`
```python
@router.get("/social")
async def social_page(request, platform=None, page=Query(1, ge=1)):
    # per_page=30, platform 필터, 페이지네이션
```

### 5. 관리자 라우트 - `src/api/admin.py`
- `GET /admin/social` - 소셜 포스트 목록 (테이블, 페이지네이션)
- `GET /admin/social/new` - 등록 폼
- `POST /admin/social/extract` - URL 메타데이터 추출 (AJAX)
- `POST /admin/social` - 소셜 포스트 생성
- `POST /admin/social/{id}/delete` - 삭제

### 6. 공개 템플릿 - `templates/social.html`
- `base.html` 상속
- 플랫폼 탭 (All / Twitter / Threads) - X/Threads SVG 아이콘 포함
- 3열 카드 그리드 (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)
- 카드 구조: 이미지 -> 플랫폼 배지 + 작성자 핸들 -> 텍스트(line-clamp-3) -> 날짜
- 전체 카드가 `<a>` 태그로 원문 URL 링크 (`target="_blank"`)
- 페이지네이션 (기존 블로그 패턴 동일)
- 빈 상태: "등록된 소셜 포스트가 없습니다" + 관리자 링크

### 7. 관리자 템플릿
**`templates/admin/social.html`** - 목록 페이지:
- 테이블: 플랫폼, 작성자, 내용 미리보기, 날짜, 삭제 버튼
- 상단 "+ 등록" 버튼
- 페이지네이션

**`templates/admin/social_form.html`** - 등록 폼:
- Step 1: URL 붙여넣기 + "추출" 버튼 (AJAX로 메타데이터 자동 채우기)
- Step 2: 폼 필드 (플랫폼, URL, 핸들, 이름, 내용, 이미지 URL, 날짜)
- embed_html은 hidden 필드
- 기존 `admin/post_form.html` 패턴 동일

### 8. 네비게이션 업데이트
- `base.html` 네비: 다크모드 버튼 앞에 `<a href="/social">Social</a>` 추가
- 관리자 템플릿 5개: `nav_extra` 블록에 `<a href="/admin/social">소셜</a>` 추가
  - `admin/dashboard.html`
  - `admin/posts.html`
  - `admin/post_form.html`
  - `admin/blogs.html`
  - `admin/crawl.html`

### 9. CSV 일괄 등록/내보내기 (Phase 2)
- `GET /admin/social/export` — 전체 소셜 포스트 CSV 내보내기 (UTF-8 BOM)
- `POST /admin/social/import` — CSV 파일 가져오기 (URL 중복 건너뜀)
- `GET /admin/social/template` — 빈 CSV 템플릿 다운로드
- CSV 컬럼: platform, original_url, author_handle, author_name, content, image_url, posted_date
- Repository: `bulk_create_social_posts(posts) -> int`, `get_all_social_posts() -> list[dict]`

### 10. URL 일괄 크롤링 (Phase 2)
- `POST /admin/social/crawl` — URL 목록(줄바꿈 구분)에서 메타데이터 자동 추출 후 일괄 등록
- 각 URL에 대해 `extract_social_metadata()` 호출, 중복/실패 건너뜀
- `asyncio.sleep(1)` 레이트 리밋
- 관리자 UI: textarea + "일괄 추출" 버튼, 결과 메시지(등록/실패 건수)

## 참고 사항
- Twitter oEmbed는 게시 날짜를 반환하지 않음 -> posted_date 수동 입력 또는 빈값
- Threads는 안정적인 공개 oEmbed API 없음 -> OG 태그 fallback
- 모든 필드는 폼에서 수동 편집 가능 (추출 실패 시 직접 입력)
- 추가 패키지 설치 불필요 (httpx, bs4 이미 사용 중)

## 검증 방법 (Phase 1 & 2)
1. 서버 실행 (`python main.py`) 후 `/social` 접속 - 빈 상태 확인
2. `/admin/social/new`에서 Twitter URL 붙여넣기 -> 추출 -> 등록
3. `/admin/social/new`에서 Threads URL 붙여넣기 -> 추출 -> 등록
4. `/social` 페이지에서 All/Twitter/Threads 탭 전환 확인
5. 30개 이상 등록 후 페이지네이션 동작 확인
6. 카드 클릭 시 원문 URL로 새 탭 열림 확인
7. `/admin/social/template` → CSV 템플릿 다운로드 확인
8. CSV에 소셜 포스트 작성 → import → 등록 건수 확인, 재 import → 중복 건너뜀
9. `/admin/social/export` → 등록된 포스트 CSV 다운로드 확인
10. URL 목록 textarea에 Twitter/Threads URL 붙여넣기 → 일괄 추출 → 등록 확인

---

## Phase 3: 계정 기반 자동 크롤링

### Context
개별 URL 등록 대신, Twitter/Threads **계정**을 등록하면 해당 계정의 글을 자동으로 수집하여 표시한다.
블로그 소스(`blogs`) → 크롤러(`crawler.py`) → 포스트(`posts`) 패턴을 따라,
소셜 계정(`social_accounts`) → 소셜 크롤러(`social_crawler.py`) → 소셜 포스트(`social_posts`) 구조로 구현.

### 수정/생성 파일 목록

| Action | File | Description |
|--------|------|-------------|
| Modify | `src/database/models.py` | `social_accounts`, `social_crawl_logs` 테이블 추가 + `social_posts`에 `account_id` 컬럼 |
| Modify | `src/database/repository.py` | 소셜 계정 CRUD 10개 + 크롤 로그 3개 메서드 추가, 기존 소셜 포스트 메서드 수정 |
| Create | `src/services/social_crawler.py` | 계정 기반 크롤러 (Nitter RSS/HTML + Threads OG) |
| Modify | `src/scheduler.py` | 소셜 크롤링 스케줄 job 추가 |
| Modify | `config.yaml` | `social_interval_hours` 설정 추가 |
| Modify | `src/api/admin.py` | 소셜 계정 관리 라우트 9개 추가 |
| Create | `templates/admin/social_accounts.html` | 관리자 소셜 계정 관리 페이지 |
| Modify | `templates/admin/*.html` (8개) | 네비게이션에 "소셜 계정" 링크 추가 |
| Modify | `src/api/public.py` | `/social` 라우트에 `account_id` 필터 추가 |
| Modify | `templates/social.html` | 계정 필터 칩 추가 |

### 11. DB 스키마 — `social_accounts` + `social_crawl_logs`
`init_db()` executescript에 추가:
```sql
CREATE TABLE IF NOT EXISTS social_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK(platform IN ('twitter', 'threads')),
    handle TEXT NOT NULL,
    display_name TEXT,
    profile_url TEXT NOT NULL,
    feed_url TEXT,
    description TEXT,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_handle ON social_accounts(handle, platform);

CREATE TABLE IF NOT EXISTS social_crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    status TEXT NOT NULL,
    posts_found INTEGER DEFAULT 0,
    posts_added INTEGER DEFAULT 0,
    error_message TEXT,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES social_accounts(id) ON DELETE CASCADE
);
```
- `social_posts`에 `account_id INTEGER` 컬럼 ALTER TABLE 추가
- `social_accounts`에 `last_crawled_at`, `crawl_error` TEXT 컬럼 ALTER TABLE 추가

### 12. Repository — 소셜 계정 CRUD + 크롤 로그
`# --- social accounts ---` 섹션:
- `create_social_account()`, `get_all_social_accounts()`, `get_social_account()`
- `update_social_account()`, `delete_social_account()`, `social_account_exists()`
- `get_active_social_accounts()`, `update_social_account_crawl_status()`
- `get_social_account_post_counts()`, `bulk_create_social_accounts()`

`# --- social crawl logs ---` 섹션:
- `create_social_crawl_log()`, `get_social_crawl_logs()`, `get_social_crawl_stats()`

기존 수정:
- `create_social_post()` — `account_id` 파라미터 추가
- `get_social_posts()` — `account_id` 필터 추가

### 13. 소셜 크롤러 서비스 — `src/services/social_crawler.py` (신규)
- `crawl_all_social_accounts(repo, config)` — 모든 활성 계정 순회 크롤링
- `crawl_social_account(account, repo, config)` — 단일 계정 크롤링
- Twitter: Nitter RSS (`feedparser`) → Nitter HTML 스크래핑 폴백
  - Nitter 인스턴스 순회 (`nitter.net`, `nitter.privacydev.net`, `nitter.poast.org`)
  - Nitter URL → `x.com` URL 변환
- Threads: 프로필 페이지에서 포스트 링크 추출 → 개별 포스트 OG 태그 (best-effort)
- URL 중복 체크, rate limit (`asyncio.sleep(2)`), 크롤 로그 기록

### 14. 스케줄러 연동 — `src/scheduler.py`
- `_run_social_crawl()` 함수 추가
- 기존 RSS 크롤링 job 아래에 소셜 크롤링 job 추가 (`social_interval_hours`, 기본 6시간)

### 15. 관리자 라우트 — `src/api/admin.py`
- `GET /admin/social-accounts` — 계정 목록 + 크롤 통계 + 최근 로그
- `POST /admin/social-accounts` — 계정 등록 (profile_url/feed_url 자동 생성)
- `POST /admin/social-accounts/{id}/toggle` — 활성/비활성
- `POST /admin/social-accounts/{id}/delete` — 삭제
- `POST /admin/social-accounts/crawl/all` — 전체 크롤링
- `POST /admin/social-accounts/{id}/crawl` — 단일 계정 크롤링
- `GET /admin/social-accounts/export` — CSV 내보내기
- `POST /admin/social-accounts/import` — CSV 가져오기
- `GET /admin/social-accounts/template` — CSV 템플릿

### 16. 관리자 템플릿 — `templates/admin/social_accounts.html` (신규)
- 크롤 통계 카드, 전체 크롤링 버튼
- 계정 등록 폼 (platform, handle, display_name, description)
- CSV 관리 (가져오기/내보내기/템플릿)
- 계정 테이블 (크롤/토글/삭제 버튼)
- 최근 크롤 로그

### 17. 네비게이션 업데이트
- 모든 관리자 템플릿 nav_extra에 `<a href="/admin/social-accounts">소셜 계정</a>` 추가
- `admin/social.html` 상단에 계정 관리 안내 배너 추가

### 18. 공개 페이지 계정 필터
- `GET /social` 라우트에 `account_id` 파라미터 추가
- `templates/social.html`에 계정 필터 칩 추가

### 검증 방법 (Phase 3)
1. `python main.py` 실행 → DB 마이그레이션 자동 적용 확인
2. `/admin/social-accounts` 접속 → 빈 계정 목록 확인
3. Twitter 계정 등록 → 계정 목록 표시
4. "크롤링" 버튼 → Nitter에서 트윗 수집 → 포스트 추가
5. `/social` 페이지에서 수집된 트윗 카드 표시
6. 계정 필터 칩으로 특정 계정 포스트만 표시
7. 계정 토글/삭제 동작 확인
8. CSV 계정 가져오기/내보내기 동작 확인
9. 기존 개별 URL 등록 (`/admin/social/new`) 여전히 동작

### 참고 사항 (Phase 3)
- Nitter 인스턴스 가용성이 불안정할 수 있음 → 다수 인스턴스 폴백
- Threads 프로필은 JS 렌더링으로 포스트 추출이 제한적 → best-effort
- 기존 `social_posts`의 `account_id = NULL` 데이터는 개별 등록 포스트로 유지
