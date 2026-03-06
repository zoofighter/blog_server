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
    """)

    # blogs 테이블에 크롤링 관련 컬럼 추가 (이미 존재하면 무시)
    for col in ["last_crawled_at", "crawl_error"]:
        try:
            conn.execute(f"ALTER TABLE blogs ADD COLUMN {col} TEXT")
        except Exception:
            pass

    conn.commit()
    conn.close()
