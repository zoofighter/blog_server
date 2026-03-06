# 개인용 블로그 애그리게이션 플랫폼 요건정의서

## 1. 프로젝트 개요

### 1.1 목적
100개의 블로그(아트, 머신러닝 등 다양한 주제)에서 콘텐츠를 자동 수집하고 요약하여 개인 큐레이션 블로그 구축

### 1.2 핵심 특징
- **규모**: 100개 블로그 소스
- **콘텐츠 형태**: 요약본 표시
- **운영 방식**: 자동 큐레이션
- **사용자**: 개인용 (본인만 사용)
- **주제**: 아트, 머신러닝, 테크, 디자인 등 다양한 분야

---

## 2. 기능 요구사항

### 2.1 블로그 소스 관리

#### 블로그 등록 시스템
```yaml
필수 정보:
  - 블로그 URL
  - RSS/Atom 피드 URL
  - 블로그 카테고리 (아트/머신러닝/테크/디자인/기타)
  - 크롤링 우선순위 (high/medium/low)
  - 활성화 상태 (active/inactive)

선택 정보:
  - 블로그 설명
  - 태그
  - 업데이트 주기
```

#### 블로그 소스 CRUD
- 100개 블로그 목록 관리
- 카테고리별 그룹핑
- 일괄 활성화/비활성화
- 소스별 통계 (수집된 글 수, 마지막 업데이트 등)

### 2.2 자동 콘텐츠 수집

#### RSS/Atom 피드 크롤링
```python
크롤링 스케줄:
  - 고우선순위: 매 1시간
  - 중우선순위: 매 3시간
  - 저우선순위: 매 12시간

수집 데이터:
  - 제목
  - 원문 URL
  - 발행일
  - 원작자
  - 본문 내용
  - 이미지 (대표 이미지 1개)
  - 원본 카테고리/태그
```

#### 웹 크롤링 (RSS 미제공 블로그)
- Beautiful Soup / Scrapy 활용
- 블로그 플랫폼별 파서 (Medium, Tistory, Velog 등)
- robots.txt 준수

### 2.3 자동 요약 시스템

#### AI 기반 요약
```yaml
요약 엔진 옵션:
  Option 1: OpenAI GPT API
    - 모델: GPT-4-mini (비용 효율적)
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
  - 제목 유사도 > 85%
  - URL 동일
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

---

## 3. 기술 스택 제안

### 3.1 백엔드

#### 크롤링 & 데이터 처리
```python
기술 스택:
  - Python 3.11+
  - Scrapy: 크롤링 프레임워크
  - feedparser: RSS 파싱
  - BeautifulSoup4: HTML 파싱
  - Celery + Redis: 비동기 작업 스케줄링
  - APScheduler: 크롤링 스케줄러
```

#### AI 요약
```python
옵션 A (클라우드):
  - OpenAI API (gpt-4o-mini)
  - 예상 비용: 100개 블로그 × 3글/일 × 30일 = 9000글/월
  - 비용: ~$5-10/월 (요약만 사용 시)

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
  - MongoDB: 비정형 데이터 유연
```

### 3.2 프론트엔드

#### 옵션 A: 정적 사이트 생성기
```yaml
Gatsby / Next.js (SSG):
  장점:
    - 빠른 로딩 속도
    - SEO 최적화 (개인용이라 불필요)
    - 무료 호스팅 (Vercel, Netlify)

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
    - 대시보드 추가 용이

  API 설계:
    - GET /api/posts?category=ml&page=1
    - GET /api/posts/{id}
    - GET /api/search?q=keyword
```

### 3.3 호스팅 (개인용)

```yaml
저비용 옵션:
  백엔드:
    - 라즈베리파이 / 개인 서버
    - 또는 Fly.io 무료 티어
    - 또는 Oracle Cloud 평생 무료

  프론트엔드:
    - Vercel / Netlify (무료)
    - GitHub Pages
    - Cloudflare Pages

  데이터베이스:
    - SQLite (로컬 파일)
    - 또는 Supabase 무료 티어
```

---

## 4. 시스템 아키텍처

### 4.1 전체 구조도

```
┌─────────────────┐
│  100개 블로그    │
│  (RSS/Web)      │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│   크롤링 엔진 (Scrapy)       │
│   - RSS 파서                 │
│   - 웹 크롤러                │
│   - 스케줄러 (Celery)        │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│   데이터 처리 파이프라인     │
│   1. 중복 제거               │
│   2. AI 요약 (GPT/로컬)      │
│   3. 카테고리 분류           │
│   4. 태그 추출               │
│   5. 품질 필터링             │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│   데이터베이스 (SQLite)      │
│   - 블로그 메타데이터        │
│   - 포스트 (요약)            │
│   - 카테고리/태그            │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│   웹 프론트엔드              │
│   - 타임라인 뷰              │
│   - 검색/필터                │
│   - 대시보드                 │
└─────────────────────────────┘
```

### 4.2 데이터 흐름

```python
# 크롤링 주기
Every 3 hours:
  1. 각 블로그 RSS 확인
  2. 신규 포스트 감지
  3. 중복 확인 (DB 조회)
  4. 신규면 처리 큐에 추가

# 처리 파이프라인
For each new post:
  1. 본문 추출/정제
  2. AI 요약 생성 (비동기)
  3. 카테고리 분류
  4. 태그 추출
  5. DB 저장
  6. 캐시 갱신

# 웹 서빙
User request:
  1. DB 쿼리 (필터/정렬)
  2. 캐시 확인
  3. JSON 반환 (API) 또는 HTML 렌더링
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
    feed_url TEXT,
    category TEXT, -- 'art', 'ml', 'tech', etc.
    priority TEXT DEFAULT 'medium', -- 'high', 'medium', 'low'
    active BOOLEAN DEFAULT TRUE,
    crawl_interval INTEGER DEFAULT 180, -- minutes
    last_crawled TIMESTAMP,
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
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

-- 크롤링 로그
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

### 6.1 크롤링 스케줄러

```python
# pseudocode
class BlogCrawler:
    def schedule_crawls():
        """우선순위 기반 크롤링 스케줄"""
        high_priority = Blog.filter(priority='high', active=True)
        medium_priority = Blog.filter(priority='medium', active=True)
        low_priority = Blog.filter(priority='low', active=True)

        schedule_task(crawl_blogs, high_priority, interval='1h')
        schedule_task(crawl_blogs, medium_priority, interval='3h')
        schedule_task(crawl_blogs, low_priority, interval='12h')

    def crawl_blog(blog):
        """개별 블로그 크롤링"""
        try:
            if blog.feed_url:
                posts = parse_rss(blog.feed_url)
            else:
                posts = scrape_web(blog.url)

            for post in posts:
                if not is_duplicate(post):
                    process_post.delay(post)  # Celery 비동기 작업

            log_success(blog, len(posts))
        except Exception as e:
            log_error(blog, str(e))
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

    # 가장 높은 점수의 카테고리 반환
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        return 'other'
```

### 6.4 프론트엔드 API

```python
# FastAPI 예시
@app.get("/api/posts")
async def get_posts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
):
    """포스트 목록 조회"""
    query = Post.query()

    if category:
        query = query.filter(category=category)
    if tag:
        query = query.join(PostTag).filter(tag_name=tag)
    if search:
        query = query.filter(
            title.contains(search) | summary.contains(search)
        )

    total = query.count()
    posts = query.order_by(published_date.desc()) \
                 .offset((page-1)*per_page) \
                 .limit(per_page) \
                 .all()

    return {
        'posts': [post.to_dict() for post in posts],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }

@app.get("/api/stats")
async def get_stats():
    """대시보드 통계"""
    return {
        'total_posts': Post.count(),
        'total_blogs': Blog.filter(active=True).count(),
        'posts_today': Post.filter(scraped_at > today).count(),
        'by_category': Post.group_by(category).count(),
        'recent_blogs': Blog.order_by(last_crawled.desc()).limit(10)
    }
```

---

## 7. UI/UX 설계

### 7.1 화면 구성

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
│  │ 💡 ML · Python  📅 2024-02-23   │   │
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

### 7.2 반응형 디자인

- 데스크탑: 3단 그리드
- 태블릿: 2단 그리드
- 모바일: 1단 리스트

### 7.3 다크모드

- 시스템 설정 따르기
- 수동 토글 옵션

---

## 8. 개발 로드맵

### Phase 1: MVP (4주)

**Week 1: 크롤링 엔진**
- [ ] 블로그 소스 관리 시스템
- [ ] RSS 파서 구현
- [ ] 기본 웹 크롤러 (5-10개 블로그 테스트)
- [ ] SQLite DB 스키마 생성

**Week 2: 데이터 처리**
- [ ] 중복 제거 로직
- [ ] 요약 시스템 (OpenAI 또는 로컬 모델 선택)
- [ ] 카테고리 분류 알고리즘
- [ ] 태그 추출

**Week 3: 백엔드 API**
- [ ] FastAPI 서버 구축
- [ ] RESTful API 구현
- [ ] 크롤링 스케줄러 (Celery)
- [ ] 전체 100개 블로그 등록

**Week 4: 프론트엔드**
- [ ] React/Next.js 기본 구조
- [ ] 타임라인 뷰
- [ ] 검색/필터 기능
- [ ] 반응형 레이아웃

### Phase 2: 고도화 (2-3주)

**기능 개선**
- [ ] 대시보드 (통계, 차트)
- [ ] 북마크 기능
- [ ] 읽음/안 읽음 표시
- [ ] 소스별 on/off 토글

**성능 최적화**
- [ ] 캐싱 (Redis)
- [ ] 이미지 최적화 (CDN)
- [ ] DB 인덱싱
- [ ] 페이지네이션 개선

**AI 고도화**
- [ ] 더 나은 요약 품질
- [ ] 관련 글 추천 알고리즘
- [ ] 주제 클러스터링

### Phase 3: 추가 기능 (선택)

- [ ] 모바일 앱 (PWA)
- [ ] 이메일 다이제스트 (주간 요약)
- [ ] RSS 피드 제공
- [ ] 내보내기 (Markdown, PDF)
- [ ] 소셜 공유

---

## 9. 비용 예측

### 9.1 클라우드 서비스 사용 시

```yaml
OpenAI API (요약):
  - 9000 글/월 × $0.0001/글 = $0.90/월
  - 여유분 포함: ~$2/월

호스팅:
  - 프론트엔드: $0 (Vercel 무료)
  - 백엔드: $0 (Oracle Free Tier)
  - DB: $0 (SQLite 또는 Supabase 무료)

총 예상 비용: $2-5/월
```

### 9.2 로컬 서버 사용 시

```yaml
하드웨어:
  - 라즈베리파이 4 (8GB): 1회 $75
  - 또는 기존 PC 활용: $0

전기세:
  - 24/7 가동: ~$3/월

AI 모델:
  - 로컬 실행: $0 (GPU 권장)

총 비용: $3/월 (전기세만)
```

---

## 10. 리스크 및 대응 방안

### 10.1 기술적 리스크

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| 블로그 구조 변경 | 크롤링 실패 | 에러 모니터링, 파서 업데이트 |
| RSS 피드 중단 | 콘텐츠 수집 불가 | 웹 크롤링으로 자동 전환 |
| AI API 비용 초과 | 예산 오버 | 로컬 모델로 전환, 요약 빈도 조절 |
| DB 용량 초과 | 성능 저하 | 오래된 데이터 아카이빙, 6개월 이상 삭제 |

### 10.2 법적 리스크

| 리스크 | 대응 방안 |
|--------|-----------|
| 저작권 침해 | - 요약만 표시 (fair use)<br>- 원문 링크 필수<br>- 원작자 명시<br>- 개인용 명시 |
| robots.txt 위반 | - robots.txt 파서 구현<br>- User-Agent 명시<br>- Crawl-delay 준수 |

### 10.3 운영 리스크

| 리스크 | 대응 방안 |
|--------|-----------|
| 서버 다운타임 | - 헬스체크 스크립트<br>- 자동 재시작<br>- 로그 모니터링 |
| 크롤링 과부하 | - Rate limiting<br>- 우선순위 기반 스케줄링 |

---

## 11. 성공 지표 (개인용)

### 정량 지표
- [ ] 100개 블로그 성공적 등록
- [ ] 일 평균 50-100개 신규 글 수집
- [ ] 크롤링 성공률 > 95%
- [ ] 요약 생성 성공률 > 90%
- [ ] 페이지 로딩 속도 < 2초

### 정성 지표
- [ ] 매일 접속하여 사용하는가?
- [ ] 요약 품질이 만족스러운가?
- [ ] 원하는 콘텐츠를 쉽게 찾는가?
- [ ] 새로운 블로그 발견에 도움이 되는가?

---

## 12. 참고 자료

### 유사 서비스
- Feedly (상용 RSS 리더)
- Inoreader
- Pocket (읽기 목록 관리)

### 기술 문서
- Scrapy: https://docs.scrapy.org
- Feedparser: https://feedparser.readthedocs.io
- OpenAI API: https://platform.openai.com/docs
- Transformers: https://huggingface.co/docs/transformers

### 데이터셋
- Common Crawl (블로그 데이터)
- 한국어 요약 데이터셋 (KoBERT)

---

## 13. 다음 단계

### 즉시 시작 가능한 작업
1. [ ] 100개 블로그 리스트 작성 (Excel/CSV)
   - 블로그 이름, URL, RSS 피드, 카테고리
2. [ ] 기술 스택 최종 결정
   - AI 요약: OpenAI vs 로컬 모델
   - 호스팅: 클라우드 vs 로컬 서버
3. [ ] 프로젝트 저장소 생성 (GitHub)
4. [ ] 개발 환경 설정
   - Python 가상환경
   - 필요한 라이브러리 설치

### 의사결정 필요 사항
- **AI 요약 방식**: 월 $2 지불하고 OpenAI 사용? 또는 무료 로컬 모델?
- **호스팅**: 클라우드 서비스? 또는 개인 서버?
- **프론트엔드**: 정적 사이트? 또는 동적 웹앱?

---

**문서 버전**: 1.0
**작성일**: 2024-02-23
**다음 업데이트**: 기술 스택 확정 후
