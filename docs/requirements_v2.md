# 개인용 블로그 애그리게이션 플랫폼 요건정의서

## 1. 프로젝트 개요

### 1.1 목적
100개의 블로그(아트, 머신러닝 등 다양한 주제)에서 콘텐츠를 수집하고 요약하여 개인 큐레이션 블로그 구축

### 1.2 핵심 특징
- **규모**: 100개 블로그 소스
- **콘텐츠 형태**: 요약본 표시
- **운영 방식**: 1차 수동 큐레이션 → 2차 자동화 전환
- **사용자**: 개인용 (본인만 사용)
- **주제**: 아트, 머신러닝, 테크, 디자인 등 다양한 분야
- **호스팅**: Oracle Cloud Free Tier

### 1.3 개발 단계 전략
- **Phase 1 (수동 관리)**: 블로그 소스 및 포스트를 수동으로 등록·관리하며 핵심 기능(요약, 분류, 퍼블리싱) 구현
- **Phase 2 (자동화)**: 안정화 후 RSS 크롤링 및 스케줄링 자동화 도입

---

## 2. 기능 요구사항

### 2.1 블로그 소스 관리 (수동)

#### 블로그 등록 시스템
```yaml
필수 정보:
  - 블로그 URL
  - RSS/Atom 피드 URL (향후 자동화 대비)
  - 블로그 카테고리 (아트/머신러닝/테크/디자인/기타)
  - 활성화 상태 (active/inactive)

선택 정보:
  - 블로그 설명
  - 태그
```

#### 블로그 소스 CRUD
- 100개 블로그 목록 관리
- 카테고리별 그룹핑
- 일괄 활성화/비활성화
- 소스별 통계 (등록된 글 수 등)

### 2.2 콘텐츠 수집

#### Phase 1: 수동 등록
```yaml
수동 등록 방식:
  - 관리자 페이지에서 포스트 URL 입력
  - URL 입력 시 메타데이터 자동 추출 (제목, 본문, 이미지)
  - 추출된 내용 확인 후 저장

등록 데이터:
  - 제목
  - 원문 URL
  - 발행일
  - 원작자
  - 본문 내용
  - 이미지 (대표 이미지 1개)
  - 원본 카테고리/태그
```

#### Phase 2: 자동 수집 (향후)
```yaml
RSS/Atom 피드 크롤링:
  크롤링 스케줄:
    - 고우선순위: 매 1시간
    - 중우선순위: 매 3시간
    - 저우선순위: 매 12시간

웹 크롤링 (RSS 미제공 블로그):
  - Beautiful Soup 활용
  - 블로그 플랫폼별 파서 (Medium, Tistory, Velog 등)
  - robots.txt 준수
```

### 2.3 자동 요약 시스템

#### AI 기반 요약
```yaml
요약 엔진 옵션:
  Option 1: OpenAI GPT API
    - 모델: GPT-4o-mini (비용 효율적)
    - 요약 길이: 2-3문장 (150-200자)
    - 한글/영문 자동 감지

  Option 2: Claude API
    - 모델: Haiku (빠른 처리)
    - 배치 처리로 비용 절감

  Option 3: 오픈소스 모델
    - BART, T5, KoBART (한글)
    - 로컬 실행 (비용 무료, 속도 느림)

요약 규칙:
  - 핵심 내용 2-3문장 추출
  - 기술 용어 보존
  - 감정/의견보다 사실 중심
```

#### 폴백(Fallback) 전략
- AI 요약 실패 시: 첫 200자 자르기
- 이미지만 있는 포스트: 제목 + "이미지 콘텐츠"

### 2.4 자동 분류 및 태깅

#### 카테고리 자동 분류
```python
카테고리 정의:
  - Art & Design (아트, 디자인, 크리에이티브)
  - Machine Learning (ML, AI, 딥러닝)
  - Programming (개발, 코딩)
  - Data Science (데이터 분석, 시각화)
  - Tech News (기술 뉴스, 트렌드)
  - Essay & Thoughts (에세이, 생각)
  - Other (기타)

분류 방법:
  1. 소스 블로그의 사전 카테고리 활용
  2. 키워드 매칭
  3. AI 분류 (임베딩 기반 유사도)
```

#### 자동 태그 추출
- 키워드 추출 (TF-IDF, KeyBERT)
- 최대 5개 태그
- 중복 태그 통합

### 2.5 중복 제거 및 품질 관리

#### 중복 감지
```python
중복 기준:
  - URL 동일 (정규화 후 비교)
  - 제목 유사도 > 85%
  - 발행일 ± 1일 & 내용 유사도 > 70%

처리 방식:
  - 최신 것 유지
  - 또는 소스 우선순위가 높은 것 유지
```

#### 품질 필터링
```yaml
자동 제외 기준:
  - 광고성 포스트 (특정 키워드 감지)
  - 너무 짧은 글 (< 100자)
  - 깨진 이미지/링크
  - 스팸 키워드 포함
```

### 2.6 개인 블로그 퍼블리싱

#### 메인 페이지
- 최신 글 타임라인 (무한 스크롤)
- 카드 형식 레이아웃
  - 대표 이미지 (있는 경우)
  - 제목
  - 요약 (2-3줄)
  - 원본 블로그명
  - 발행일
  - 카테고리/태그
  - "원문 보기" 버튼

#### 필터링 및 검색
- 카테고리별 필터
- 태그별 필터
- 날짜 범위 선택
- 전체 텍스트 검색 (제목 + 요약)
- 소스 블로그별 필터

#### 상세 페이지
- 요약 + 원문 링크
- 원작자 크레딧
- 관련 글 추천 (같은 카테고리/태그)

### 2.7 관리자 페이지 (Phase 1 핵심)

#### 포스트 수동 등록
```yaml
등록 플로우:
  1. URL 입력
  2. 메타데이터 자동 추출 (제목, 본문, 이미지, 발행일)
  3. 소스 블로그 선택 (기등록 블로그) 또는 신규 블로그 등록
  4. 카테고리 확인/수정
  5. AI 요약 생성 (버튼 클릭)
  6. 요약 내용 확인/수정 후 저장
```

#### 블로그 소스 관리
- 블로그 추가/수정/삭제
- 카테고리 관리
- 태그 관리

#### 대시보드
- 등록된 총 포스트 수
- 카테고리별 분포
- 최근 등록 이력

---

## 3. 기술 스택

### 3.1 백엔드

#### 웹 서버 & API
```python
기술 스택:
  - Python 3.11+
  - FastAPI: REST API 서버
  - feedparser: RSS 파싱 (Phase 2)
  - BeautifulSoup4: URL 메타데이터 추출
  - httpx: HTTP 클라이언트
```

#### AI 요약
```python
옵션 A (클라우드):
  - OpenAI API (gpt-4o-mini)
  - 예상 비용: ~$5-10/월 (요약만 사용 시)

옵션 B (로컬):
  - Transformers (HuggingFace)
  - 모델: facebook/bart-large-cnn (영문)
  - 모델: gogamza/kobart-summarization (한글)
  - 비용: 무료, GPU 권장
```

#### 데이터베이스
```yaml
SQLite (개인용 충분):
  테이블 설계:
    - blogs: 블로그 소스 정보
    - posts: 수집된 포스트
    - categories: 카테고리
    - tags: 태그
    - post_tags: 포스트-태그 연결

대안 (확장 고려):
  - PostgreSQL: 전체 텍스트 검색 강력
```

### 3.2 프론트엔드

#### 옵션 A: 정적 사이트 생성기
```yaml
Next.js (SSG):
  장점:
    - 빠른 로딩 속도
    - 무료 호스팅 가능

  빌드 프로세스:
    - DB에서 데이터 추출
    - 매일 자동 빌드 (GitHub Actions)
    - 자동 배포
```

#### 옵션 B: 단일 페이지 애플리케이션
```yaml
React + FastAPI:
  장점:
    - 실시간 업데이트
    - 동적 필터링
    - 관리자 페이지와 통합 용이

  API 설계:
    - GET /api/posts?category=ml&page=1
    - GET /api/posts/{id}
    - GET /api/search?q=keyword
    - POST /api/posts (수동 등록)
    - POST /api/posts/{id}/summarize (요약 생성)
```

### 3.3 호스팅 (Oracle Cloud Free Tier)

```yaml
Oracle Cloud Always Free:
  컴퓨트:
    - AMD VM.Standard.E2.1.Micro: 1 OCPU, 1GB RAM (2개)
    - 또는 Ampere A1: 최대 4 OCPU, 24GB RAM
    - 용도: FastAPI 서버 + 크롤러 (Phase 2)

  스토리지:
    - Block Volume: 200GB (무료)
    - Object Storage: 10GB (무료)

  네트워크:
    - 10TB/월 아웃바운드 데이터 (무료)
    - 공용 IP 주소

  데이터베이스:
    - SQLite (VM 내 파일)
    - 또는 Oracle Autonomous DB (20GB 무료)

  추가 구성:
    - Nginx: 리버스 프록시 + 정적 파일 서빙
    - Let's Encrypt: SSL 인증서 (무료)
    - systemd: 프로세스 관리
```

---

## 4. 시스템 아키텍처

### 4.1 전체 구조도 (Phase 1: 수동 관리)

```
┌─────────────────────────────────────────┐
│         Oracle Cloud Free Tier          │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Nginx (리버스 프록시 + SSL)       │  │
│  └──────────┬────────────────────────┘  │
│             │                           │
│             ↓                           │
│  ┌───────────────────────────────────┐  │
│  │  FastAPI 서버                      │  │
│  │  - 공개 API (포스트 조회/검색)     │  │
│  │  - 관리자 API (포스트 등록/수정)   │  │
│  │  - URL 메타데이터 추출             │  │
│  │  - AI 요약 호출                    │  │
│  └──────────┬────────────────────────┘  │
│             │                           │
│             ↓                           │
│  ┌───────────────────────────────────┐  │
│  │  SQLite 데이터베이스               │  │
│  │  - 블로그 메타데이터               │  │
│  │  - 포스트 (요약)                   │  │
│  │  - 카테고리/태그                   │  │
│  └───────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘

관리자 → 관리자 페이지에서 URL 입력 → 메타데이터 추출 → 요약 생성 → DB 저장
방문자 → 공개 페이지에서 카드 뷰 열람 → 원문 링크 클릭
```

### 4.2 전체 구조도 (Phase 2: 자동화 추가)

```
┌─────────────────┐
│  100개 블로그    │
│  (RSS/Web)      │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│         Oracle Cloud Free Tier          │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  크롤링 스케줄러 (APScheduler)     │  │
│  │  - RSS 파서 (feedparser)           │  │
│  │  - 웹 크롤러 (BeautifulSoup)       │  │
│  └──────────┬────────────────────────┘  │
│             │                           │
│             ↓                           │
│  ┌───────────────────────────────────┐  │
│  │  데이터 처리 파이프라인            │  │
│  │  1. 중복 제거                      │  │
│  │  2. AI 요약 (GPT/로컬)            │  │
│  │  3. 카테고리 분류                  │  │
│  │  4. 태그 추출                      │  │
│  │  5. 품질 필터링                    │  │
│  └──────────┬────────────────────────┘  │
│             │                           │
│             ↓                           │
│  ┌───────────────────────────────────┐  │
│  │  FastAPI + SQLite                  │  │
│  └───────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### 4.3 데이터 흐름

```python
# Phase 1: 수동 등록 플로우
관리자가 URL 입력:
  1. URL에서 메타데이터 추출 (제목, 본문, 이미지)
  2. 중복 확인 (URL 기준)
  3. AI 요약 생성
  4. 카테고리 자동 분류 (수동 수정 가능)
  5. 태그 추출
  6. DB 저장

# Phase 2: 자동 수집 플로우 (향후)
Every 3 hours:
  1. 각 블로그 RSS 확인
  2. 신규 포스트 감지
  3. 중복 확인 (DB 조회)
  4. 신규면 처리 큐에 추가
  5. 자동 요약 → 분류 → 저장

# 웹 서빙
User request:
  1. DB 쿼리 (필터/정렬)
  2. JSON 반환 (API) 또는 HTML 렌더링
```

---

## 5. 데이터베이스 스키마

### 5.1 테이블 설계

```sql
-- 블로그 소스
CREATE TABLE blogs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    feed_url TEXT, -- Phase 2 자동화 대비
    category TEXT, -- 'art', 'ml', 'tech', etc.
    active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포스트
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    blog_id INTEGER,
    title TEXT NOT NULL,
    original_url TEXT UNIQUE NOT NULL,
    summary TEXT, -- AI 생성 요약
    full_content TEXT, -- 원본 내용 (선택적 저장)
    author TEXT,
    published_date TIMESTAMP,
    image_url TEXT,
    category TEXT, -- 자동 분류된 카테고리
    language TEXT DEFAULT 'ko', -- 'ko', 'en'
    summary_status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed'
    registered_by TEXT DEFAULT 'manual', -- 'manual', 'auto'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blog_id) REFERENCES blogs(id)
);

-- 태그
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- 포스트-태그 연결
CREATE TABLE post_tags (
    post_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- 크롤링 로그 (Phase 2)
CREATE TABLE crawl_logs (
    id INTEGER PRIMARY KEY,
    blog_id INTEGER,
    status TEXT, -- 'success', 'failed'
    posts_found INTEGER DEFAULT 0,
    error_message TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blog_id) REFERENCES blogs(id)
);
```

---

## 6. 주요 기능 상세 명세

### 6.1 URL 메타데이터 추출 (Phase 1 핵심)

```python
def extract_metadata(url):
    """URL에서 포스트 메타데이터 자동 추출"""
    response = httpx.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    return {
        'title': extract_title(soup),        # og:title 또는 <title>
        'content': extract_content(soup),     # 본문 텍스트
        'image': extract_image(soup),         # og:image
        'author': extract_author(soup),       # meta author
        'published': extract_date(soup),      # 발행일
    }
```

### 6.2 AI 요약 시스템

```python
# Option 1: OpenAI
def summarize_with_gpt(content, title):
    """GPT 기반 요약"""
    prompt = f"""
    다음 블로그 글을 2-3문장으로 요약해주세요.
    핵심 내용과 주요 키워드를 포함하세요.

    제목: {title}
    내용: {content[:2000]}  # 토큰 제한

    요약:
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3
    )

    return response.choices[0].message.content

# Option 2: 로컬 모델
def summarize_with_local_model(content):
    """로컬 Transformers 모델"""
    from transformers import pipeline

    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(content[:1024], max_length=100, min_length=30)

    return summary[0]['summary_text']
```

### 6.3 카테고리 자동 분류

```python
def classify_category(title, content, tags):
    """키워드 기반 카테고리 분류"""

    keywords = {
        'art': ['art', 'design', 'creative', '디자인', '아트', '일러스트', '그림'],
        'ml': ['machine learning', 'ml', 'ai', 'deep learning', '머신러닝', '딥러닝', '인공지능'],
        'programming': ['code', 'programming', 'dev', '코드', '개발', 'python', 'javascript'],
        'data': ['data', 'analytics', 'visualization', '데이터', '분석'],
        'tech': ['tech', 'technology', 'startup', '기술', '스타트업']
    }

    text = f"{title} {content} {' '.join(tags)}".lower()

    scores = {}
    for category, kws in keywords.items():
        scores[category] = sum(1 for kw in kws if kw in text)

    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        return 'other'
```

### 6.4 프론트엔드 API

```python
# FastAPI

# --- 공개 API ---
@app.get("/api/posts")
async def get_posts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
):
    """포스트 목록 조회"""
    ...

@app.get("/api/posts/{id}")
async def get_post(id: int):
    """포스트 상세 조회"""
    ...

@app.get("/api/stats")
async def get_stats():
    """대시보드 통계"""
    ...

# --- 관리자 API (Phase 1 핵심) ---
@app.post("/api/admin/extract")
async def extract_metadata(url: str):
    """URL에서 메타데이터 추출"""
    ...

@app.post("/api/admin/posts")
async def create_post(post: PostCreate):
    """포스트 수동 등록"""
    ...

@app.post("/api/admin/posts/{id}/summarize")
async def generate_summary(id: int):
    """AI 요약 생성"""
    ...

@app.put("/api/admin/posts/{id}")
async def update_post(id: int, post: PostUpdate):
    """포스트 수정"""
    ...

@app.delete("/api/admin/posts/{id}")
async def delete_post(id: int):
    """포스트 삭제"""
    ...

@app.post("/api/admin/blogs")
async def create_blog(blog: BlogCreate):
    """블로그 소스 등록"""
    ...
```

---

## 7. UI/UX 설계

### 7.1 공개 페이지 - 화면 구성

```
┌─────────────────────────────────────────┐
│  Logo  [검색창]          [카테고리 ▼]    │
├─────────────────────────────────────────┤
│  [All] [Art] [ML] [Tech] [Data] [Essay] │ ← 카테고리 탭
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ [이미지]                         │   │
│  │ 블로그 제목                      │   │
│  │ 요약 텍스트 2-3줄...             │   │
│  │ ML · Python  2026-03-06          │   │
│  │ 출처: Blog Name  [원문 보기 →]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ ...                             │   │
│  └─────────────────────────────────┘   │
│                                         │
│         [더 보기 ↓]                     │
└─────────────────────────────────────────┘
```

### 7.2 관리자 페이지 (Phase 1 핵심)

```
┌─────────────────────────────────────────┐
│  Admin  [대시보드] [포스트 등록] [소스]   │
├─────────────────────────────────────────┤
│                                         │
│  ┌─ 포스트 등록 ──────────────────────┐ │
│  │                                     │ │
│  │  URL: [________________________]    │ │
│  │        [메타데이터 추출]             │ │
│  │                                     │ │
│  │  제목: [자동 추출됨, 수정 가능]     │ │
│  │  블로그: [드롭다운 선택]            │ │
│  │  카테고리: [자동 분류, 수정 가능]   │ │
│  │  이미지: [미리보기]                 │ │
│  │                                     │ │
│  │  [AI 요약 생성]                     │ │
│  │  요약: [자동 생성됨, 수정 가능]     │ │
│  │                                     │ │
│  │         [저장]  [취소]              │ │
│  └─────────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

### 7.3 반응형 디자인

- 데스크탑: 3단 그리드
- 태블릿: 2단 그리드
- 모바일: 1단 리스트

### 7.4 다크모드

- 시스템 설정 따르기
- 수동 토글 옵션

---

## 8. 개발 로드맵

### Phase 1: MVP - 수동 관리 (4주)

**Week 1: 기반 구축**
- [ ] Oracle Cloud VM 세팅 (Ampere A1)
- [ ] Nginx + SSL (Let's Encrypt) 구성
- [ ] SQLite DB 스키마 생성
- [ ] FastAPI 프로젝트 구조 세팅

**Week 2: 관리자 기능**
- [ ] URL 메타데이터 추출 기능
- [ ] 포스트 수동 등록 API (CRUD)
- [ ] 블로그 소스 관리 API (CRUD)
- [ ] AI 요약 시스템 연동 (OpenAI 또는 로컬 모델 선택)

**Week 3: 공개 페이지**
- [ ] 포스트 목록 API (필터/검색/페이지네이션)
- [ ] 프론트엔드 기본 구조 (React 또는 서버 렌더링)
- [ ] 카드 레이아웃 타임라인 뷰
- [ ] 카테고리/태그 필터, 검색

**Week 4: 관리자 UI + 배포**
- [ ] 관리자 페이지 UI (포스트 등록 폼)
- [ ] 대시보드 (통계)
- [ ] 반응형 레이아웃
- [ ] 10-20개 블로그 시범 등록 및 테스트

### Phase 2: 자동화 도입 (3-4주)

**자동 수집**
- [ ] RSS 파서 구현 (feedparser)
- [ ] 크롤링 스케줄러 (APScheduler)
- [ ] 웹 크롤러 (RSS 미제공 블로그)
- [ ] 100개 블로그 RSS 피드 등록
- [ ] 중복 제거 자동화
- [ ] 품질 필터링 자동화

**기능 개선**
- [ ] 북마크 기능
- [ ] 읽음/안 읽음 표시
- [ ] 소스별 on/off 토글

### Phase 3: 고도화 (선택)

- [ ] 캐싱 최적화
- [ ] 이미지 최적화
- [ ] 관련 글 추천 알고리즘
- [ ] 이메일 다이제스트 (주간 요약)
- [ ] RSS 피드 제공
- [ ] PWA

---

## 9. 비용 예측

### Oracle Cloud Free Tier 사용

```yaml
Oracle Cloud (호스팅):
  - 컴퓨트 (Ampere A1): $0 (Always Free)
  - 스토리지 (200GB): $0 (Always Free)
  - 네트워크: $0 (10TB/월 무료)
  - SSL: $0 (Let's Encrypt)

OpenAI API (요약 - Phase 1 수동 등록 시):
  - 수동 등록: 하루 10-20건 가정
  - 월 300-600건 × ~$0.0003/건 = $0.10-0.20/월

OpenAI API (요약 - Phase 2 자동 수집 시):
  - 100개 블로그 × 3글/일 × 30일 = 9000글/월
  - 비용: ~$3-5/월

도메인 (선택):
  - 무료: Oracle Cloud 제공 IP 직접 사용
  - 유료: 연 $10-15 (커스텀 도메인)

총 예상 비용:
  - Phase 1: $0-1/월 (거의 무료)
  - Phase 2: $3-5/월
```

---

## 10. 리스크 및 대응 방안

### 10.1 기술적 리스크

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| Oracle Cloud VM 제한 | 리소스 부족 | Ampere A1 활용 (4 OCPU, 24GB), 경량 스택 유지 |
| AI API 비용 초과 | 예산 오버 | Phase 1은 수동이라 소량, 로컬 모델 전환 가능 |
| DB 용량 초과 | 성능 저하 | 오래된 데이터 아카이빙, 6개월 이상 삭제 |
| 블로그 구조 변경 (Phase 2) | 크롤링 실패 | 에러 모니터링, 파서 업데이트 |

### 10.2 법적 리스크

| 리스크 | 대응 방안 |
|--------|-----------|
| 저작권 침해 | - 요약만 표시<br>- 원문 링크 필수<br>- 원작자 명시<br>- 비공개 또는 개인용 명시 |
| robots.txt 위반 (Phase 2) | - robots.txt 파서 구현<br>- User-Agent 명시<br>- Crawl-delay 준수 |

### 10.3 운영 리스크

| 리스크 | 대응 방안 |
|--------|-----------|
| Oracle Cloud 서버 다운 | - systemd 자동 재시작<br>- 헬스체크 스크립트<br>- 로그 모니터링 |
| 수동 등록 피로 (Phase 1) | - UI 최적화로 등록 시간 최소화<br>- Phase 2 자동화로 전환 |

---

## 11. 성공 지표 (개인용)

### Phase 1 정량 지표
- [ ] Oracle Cloud 서버 안정 가동
- [ ] 관리자 페이지에서 포스트 등록 1분 이내 완료
- [ ] 20개 이상 블로그 소스 등록
- [ ] 100개 이상 포스트 축적
- [ ] 페이지 로딩 속도 < 2초

### Phase 2 정량 지표
- [ ] 100개 블로그 성공적 등록
- [ ] 일 평균 50-100개 신규 글 수집
- [ ] 크롤링 성공률 > 95%
- [ ] 요약 생성 성공률 > 90%

### 정성 지표
- [ ] 매일 접속하여 사용하는가?
- [ ] 요약 품질이 만족스러운가?
- [ ] 원하는 콘텐츠를 쉽게 찾는가?

---

## 12. Oracle Cloud 배포 가이드

### 12.1 VM 세팅

```bash
# Ampere A1 인스턴스 생성 (Always Free)
# Shape: VM.Standard.A1.Flex
# OCPU: 1-4, Memory: 6-24GB
# OS: Ubuntu 22.04

# 기본 패키지 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx

# 프로젝트 세팅
python3.11 -m venv /opt/blog-aggregator/venv
source /opt/blog-aggregator/venv/bin/activate
pip install fastapi uvicorn httpx beautifulsoup4 openai
```

### 12.2 Nginx 설정

```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /opt/blog-aggregator/static/;
    }
}
```

### 12.3 systemd 서비스

```ini
[Unit]
Description=Blog Aggregator API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/blog-aggregator
ExecStart=/opt/blog-aggregator/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 13. 참고 자료

### 유사 서비스
- Feedly (상용 RSS 리더)
- Inoreader
- Pocket (읽기 목록 관리)

### 기술 문서
- FastAPI: https://fastapi.tiangolo.com
- Feedparser: https://feedparser.readthedocs.io
- OpenAI API: https://platform.openai.com/docs
- Oracle Cloud Free Tier: https://www.oracle.com/cloud/free

---

## 14. 다음 단계

### 즉시 시작 가능한 작업
1. [ ] Oracle Cloud 계정 생성 및 Always Free VM 프로비저닝
2. [ ] 20개 블로그 리스트 작성 (Phase 1 시범용)
   - 블로그 이름, URL, RSS 피드, 카테고리
3. [ ] 기술 스택 최종 결정
   - AI 요약: OpenAI vs 로컬 모델
4. [ ] 프로젝트 저장소 생성 (GitHub)
5. [ ] 개발 환경 설정

### 의사결정 필요 사항
- **AI 요약 방식**: OpenAI ($1 미만/월) vs 로컬 모델 (무료)?
- **프론트엔드**: React SPA vs 서버 렌더링 (Jinja2)?
- **인증**: 관리자 페이지 접근 제어 방식 (간단한 비밀번호 vs OAuth)?

---

**문서 버전**: 2.0
**작성일**: 2026-03-06
**주요 변경**: 수동 관리 우선 전략, Oracle Cloud 호스팅 확정
**다음 업데이트**: 기술 스택 확정 후
