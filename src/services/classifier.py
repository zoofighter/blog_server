"""키워드 기반 카테고리 분류 및 태그 추출 서비스."""

import re
from collections import Counter

CATEGORY_KEYWORDS = {
    "art": [
        "art", "design", "creative", "illustration", "typography", "ux", "ui",
        "디자인", "아트", "일러스트", "그림", "타이포", "크리에이티브",
    ],
    "ml": [
        "machine learning", "deep learning", "neural network", "transformer",
        "llm", "gpt", "bert", "diffusion", "reinforcement learning",
        "머신러닝", "딥러닝", "인공지능", "신경망",
    ],
    "programming": [
        "programming", "code", "software", "algorithm", "api", "framework",
        "python", "javascript", "typescript", "rust", "go", "java", "react", "vue",
        "개발", "코딩", "프로그래밍", "알고리즘",
    ],
    "data": [
        "data science", "data engineering", "analytics", "visualization",
        "pandas", "sql", "spark", "etl", "dashboard",
        "데이터", "분석", "시각화",
    ],
    "tech": [
        "technology", "startup", "product", "cloud", "devops", "kubernetes",
        "docker", "aws", "infrastructure",
        "기술", "스타트업", "클라우드", "인프라",
    ],
    "essay": [
        "essay", "opinion", "thought", "reflection", "life", "career",
        "에세이", "생각", "회고", "커리어", "일상",
    ],
}

# 태그 추출에서 제외할 불용어
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "and", "or", "but", "not", "for", "with", "from", "about", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "것", "수", "등", "및", "또는", "그", "이", "저",
    "하는", "있는", "되는", "한", "할", "하고", "있다", "된다",
}


def classify_category(title: str, content: str) -> str:
    """제목과 본문을 분석하여 카테고리를 분류한다."""
    text = f"{title} {content[:1000]}".lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[category] = score

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "other"


def extract_tags(title: str, content: str, max_tags: int = 5) -> list[str]:
    """제목과 본문에서 주요 키워드를 태그로 추출한다."""
    text = f"{title} {content[:2000]}"

    # 영문 단어 추출
    en_words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{2,}", text)
    # 한글 단어 추출 (2글자 이상)
    ko_words = re.findall(r"[가-힣]{2,}", text)

    words = [w.lower() for w in en_words if w.lower() not in STOP_WORDS]
    words += [w for w in ko_words if w not in STOP_WORDS]

    counter = Counter(words)
    return [word for word, _ in counter.most_common(max_tags)]
