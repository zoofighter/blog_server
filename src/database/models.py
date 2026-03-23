import os
import sqlite3


def get_db_path(config: dict) -> str:
    return config.get("database", {}).get("path", "data/blog.db")


def get_connection(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            feed_url TEXT,
            category TEXT,
            active INTEGER DEFAULT 1,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blog_id INTEGER,
            title TEXT NOT NULL,
            original_url TEXT UNIQUE NOT NULL,
            summary TEXT,
            full_content TEXT,
            author TEXT,
            published_date DATETIME,
            image_url TEXT,
            category TEXT,
            language TEXT DEFAULT 'ko',
            summary_status TEXT DEFAULT 'pending',
            registered_by TEXT DEFAULT 'manual',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (blog_id) REFERENCES blogs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
        CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_date DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON posts(blog_id);
        CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(original_url);

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS crawl_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blog_id INTEGER,
            status TEXT NOT NULL,
            posts_found INTEGER DEFAULT 0,
            posts_added INTEGER DEFAULT 0,
            error_message TEXT,
            crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (blog_id) REFERENCES blogs(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_crawl_logs_blog ON crawl_logs(blog_id);
        CREATE INDEX IF NOT EXISTS idx_crawl_logs_at ON crawl_logs(crawled_at DESC);

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

        CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_handle
            ON social_accounts(handle, platform);

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

        CREATE INDEX IF NOT EXISTS idx_social_crawl_logs_account ON social_crawl_logs(account_id);
        CREATE INDEX IF NOT EXISTS idx_social_crawl_logs_at ON social_crawl_logs(crawled_at DESC);
    """)

    # blogs 테이블에 크롤링 관련 컬럼 추가 (이미 존재하면 무시)
    for col in ["last_crawled_at", "crawl_error"]:
        try:
            conn.execute(f"ALTER TABLE blogs ADD COLUMN {col} TEXT")
        except Exception:
            pass

    # social_posts 테이블에 account_id 컬럼 추가
    for col in ["account_id"]:
        try:
            conn.execute(f"ALTER TABLE social_posts ADD COLUMN {col} INTEGER REFERENCES social_accounts(id)")
        except Exception:
            pass

    # social_accounts 테이블에 크롤링 상태 컬럼 추가
    for col in ["last_crawled_at", "crawl_error"]:
        try:
            conn.execute(f"ALTER TABLE social_accounts ADD COLUMN {col} TEXT")
        except Exception:
            pass

    # Bluesky 플랫폼 지원을 위한 CHECK 제약 마이그레이션
    _migrate_platform_check(conn)

    conn.commit()
    conn.close()


def _migrate_platform_check(conn):
    """social_posts, social_accounts 테이블의 platform CHECK 제약을 확장한다."""
    # 이미 마이그레이션 완료 여부 확인
    try:
        conn.execute("INSERT INTO social_posts (platform, original_url) VALUES ('bluesky', '__migrate_test__')")
        conn.execute("DELETE FROM social_posts WHERE original_url = '__migrate_test__'")
        conn.commit()
        return  # bluesky 이미 허용됨
    except Exception:
        conn.rollback()

    # FK 비활성화 후 테이블 재생성
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS social_posts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('twitter', 'threads', 'bluesky')),
            original_url TEXT UNIQUE NOT NULL,
            author_handle TEXT,
            author_name TEXT,
            content TEXT,
            image_url TEXT,
            embed_html TEXT,
            posted_date DATETIME,
            account_id INTEGER REFERENCES social_accounts(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO social_posts_new
            SELECT id, platform, original_url, author_handle, author_name,
                   content, image_url, embed_html, posted_date, account_id, created_at
            FROM social_posts;

        DROP TABLE social_posts;
        ALTER TABLE social_posts_new RENAME TO social_posts;

        CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform);
        CREATE INDEX IF NOT EXISTS idx_social_posts_posted ON social_posts(posted_date DESC);
    """)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS social_accounts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('twitter', 'threads', 'bluesky')),
            handle TEXT NOT NULL,
            display_name TEXT,
            profile_url TEXT NOT NULL,
            feed_url TEXT,
            description TEXT,
            active INTEGER DEFAULT 1,
            last_crawled_at TEXT,
            crawl_error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO social_accounts_new
            SELECT id, platform, handle, display_name, profile_url,
                   feed_url, description, active, last_crawled_at, crawl_error, created_at
            FROM social_accounts;

        DROP TABLE social_accounts;
        ALTER TABLE social_accounts_new RENAME TO social_accounts;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_handle
            ON social_accounts(handle, platform);
    """)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
