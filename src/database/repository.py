import sqlite3
from typing import Optional

from src.database.models import get_connection


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # --- blogs ---

    def create_blog(self, name: str, url: str, feed_url: str = None,
                    category: str = None, description: str = None) -> int:
        conn = self._conn()
        cursor = conn.execute(
            "INSERT INTO blogs (name, url, feed_url, category, description) VALUES (?, ?, ?, ?, ?)",
            (name, url, feed_url, category, description),
        )
        blog_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return blog_id

    def get_all_blogs(self, active_only: bool = False) -> list[dict]:
        conn = self._conn()
        if active_only:
            rows = conn.execute(
                "SELECT * FROM blogs WHERE active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM blogs ORDER BY name").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_blog(self, blog_id: int) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_blog(self, blog_id: int, **kwargs) -> None:
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [blog_id]
        conn = self._conn()
        conn.execute(f"UPDATE blogs SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_blog(self, blog_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
        conn.commit()
        conn.close()

    def bulk_create_blogs(self, blogs: list[dict]) -> int:
        """여러 블로그를 한 번에 등록한다. URL 중복은 건너뛴다. 등록 건수를 반환."""
        conn = self._conn()
        count = 0
        for b in blogs:
            existing = conn.execute(
                "SELECT 1 FROM blogs WHERE url = ?", (b.get("url", ""),)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO blogs (name, url, feed_url, category, description) VALUES (?, ?, ?, ?, ?)",
                (b.get("name", ""), b.get("url", ""), b.get("feed_url") or None,
                 b.get("category") or None, b.get("description") or None),
            )
            count += 1
        conn.commit()
        conn.close()
        return count

    def get_blog_post_counts(self) -> dict[int, int]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT blog_id, COUNT(*) as cnt FROM posts GROUP BY blog_id"
        ).fetchall()
        conn.close()
        return {r["blog_id"]: r["cnt"] for r in rows}

    # --- posts ---

    def create_post(self, blog_id: int, title: str, original_url: str,
                    summary: str = None, full_content: str = None,
                    author: str = None, published_date: str = None,
                    image_url: str = None, category: str = None,
                    language: str = "ko", summary_status: str = "pending",
                    registered_by: str = "manual") -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO posts
               (blog_id, title, original_url, summary, full_content, author,
                published_date, image_url, category, language, summary_status, registered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (blog_id, title, original_url, summary, full_content, author,
             published_date, image_url, category, language, summary_status, registered_by),
        )
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return post_id

    def get_posts(self, category: str = None, tag: str = None,
                  search: str = None, blog_id: int = None,
                  page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        conn = self._conn()
        conditions = []
        params = []

        if category:
            conditions.append("p.category = ?")
            params.append(category)
        if blog_id:
            conditions.append("p.blog_id = ?")
            params.append(blog_id)
        if search:
            conditions.append("(p.title LIKE ? OR p.summary LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            conditions.append(
                "p.id IN (SELECT pt.post_id FROM post_tags pt "
                "JOIN tags t ON pt.tag_id = t.id WHERE t.name = ?)"
            )
            params.append(tag)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM posts p {where}", params
        ).fetchone()[0]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT p.*, b.name as blog_name
                FROM posts p
                LEFT JOIN blogs b ON p.blog_id = b.id
                {where}
                ORDER BY p.published_date DESC NULLS LAST, p.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        conn.close()
        return [dict(r) for r in rows], total

    def get_post(self, post_id: int) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            """SELECT p.*, b.name as blog_name
               FROM posts p
               LEFT JOIN blogs b ON p.blog_id = b.id
               WHERE p.id = ?""",
            (post_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_post(self, post_id: int, **kwargs) -> None:
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [post_id]
        conn = self._conn()
        conn.execute(f"UPDATE posts SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_post(self, post_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()

    def post_exists_url(self, url: str) -> bool:
        conn = self._conn()
        row = conn.execute(
            "SELECT 1 FROM posts WHERE original_url = ?", (url,)
        ).fetchone()
        conn.close()
        return row is not None

    def get_related_posts(self, post_id: int, category: str, limit: int = 5) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT p.id, p.title, p.image_url, p.published_date, b.name as blog_name
               FROM posts p
               LEFT JOIN blogs b ON p.blog_id = b.id
               WHERE p.category = ? AND p.id != ?
               ORDER BY p.published_date DESC
               LIMIT ?""",
            (category, post_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- tags ---

    def create_or_get_tag(self, name: str) -> int:
        conn = self._conn()
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if row:
            tag_id = row["id"]
        else:
            cursor = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            tag_id = cursor.lastrowid
            conn.commit()
        conn.close()
        return tag_id

    def set_post_tags(self, post_id: int, tag_names: list[str]) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        for name in tag_names:
            row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
            if row:
                tag_id = row["id"]
            else:
                cursor = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
                tag_id = cursor.lastrowid
            conn.execute(
                "INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)",
                (post_id, tag_id),
            )
        conn.commit()
        conn.close()

    def get_post_tags(self, post_id: int) -> list[str]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT t.name FROM tags t
               JOIN post_tags pt ON t.id = pt.tag_id
               WHERE pt.post_id = ?
               ORDER BY t.name""",
            (post_id,),
        ).fetchall()
        conn.close()
        return [r["name"] for r in rows]

    def get_all_tags(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT t.name, COUNT(pt.post_id) as count
               FROM tags t
               LEFT JOIN post_tags pt ON t.id = pt.tag_id
               GROUP BY t.id
               ORDER BY count DESC"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- crawl logs ---

    def create_crawl_log(self, blog_id: int, status: str,
                         posts_found: int = 0, posts_added: int = 0,
                         error_message: str = None) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO crawl_logs (blog_id, status, posts_found, posts_added, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (blog_id, status, posts_found, posts_added, error_message),
        )
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id

    def get_crawl_logs(self, blog_id: int = None, limit: int = 50) -> list[dict]:
        conn = self._conn()
        if blog_id:
            rows = conn.execute(
                """SELECT cl.*, b.name as blog_name
                   FROM crawl_logs cl
                   LEFT JOIN blogs b ON cl.blog_id = b.id
                   WHERE cl.blog_id = ?
                   ORDER BY cl.crawled_at DESC LIMIT ?""",
                (blog_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cl.*, b.name as blog_name
                   FROM crawl_logs cl
                   LEFT JOIN blogs b ON cl.blog_id = b.id
                   ORDER BY cl.crawled_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_blogs_with_feed(self, active_only: bool = True) -> list[dict]:
        """피드 URL이 있는 활성 블로그 목록을 반환한다."""
        conn = self._conn()
        conditions = ["feed_url IS NOT NULL", "feed_url != ''"]
        if active_only:
            conditions.append("active = 1")
        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM blogs WHERE {where} ORDER BY name"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_blog_crawl_status(self, blog_id: int, error: str = None) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE blogs SET last_crawled_at = CURRENT_TIMESTAMP, crawl_error = ? WHERE id = ?",
            (error, blog_id),
        )
        conn.commit()
        conn.close()

    def get_crawl_stats(self) -> dict:
        conn = self._conn()
        total_with_feed = conn.execute(
            "SELECT COUNT(*) FROM blogs WHERE feed_url IS NOT NULL AND feed_url != '' AND active = 1"
        ).fetchone()[0]
        last_24h = conn.execute(
            "SELECT COUNT(*) FROM crawl_logs WHERE crawled_at > datetime('now', '-1 day')"
        ).fetchone()[0]
        success_24h = conn.execute(
            "SELECT COUNT(*) FROM crawl_logs WHERE status = 'success' AND crawled_at > datetime('now', '-1 day')"
        ).fetchone()[0]
        posts_added_24h = conn.execute(
            "SELECT COALESCE(SUM(posts_added), 0) FROM crawl_logs WHERE crawled_at > datetime('now', '-1 day')"
        ).fetchone()[0]
        conn.close()
        return {
            "total_with_feed": total_with_feed,
            "crawls_24h": last_24h,
            "success_24h": success_24h,
            "posts_added_24h": posts_added_24h,
        }

    # --- stats ---

    def get_stats(self) -> dict:
        conn = self._conn()
        total_posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        total_blogs = conn.execute("SELECT COUNT(*) FROM blogs WHERE active = 1").fetchone()[0]

        by_category = conn.execute(
            """SELECT category, COUNT(*) as count
               FROM posts
               GROUP BY category
               ORDER BY count DESC"""
        ).fetchall()

        recent_posts = conn.execute(
            """SELECT p.id, p.title, p.category, p.created_at, b.name as blog_name
               FROM posts p
               LEFT JOIN blogs b ON p.blog_id = b.id
               ORDER BY p.created_at DESC
               LIMIT 10"""
        ).fetchall()

        conn.close()
        return {
            "total_posts": total_posts,
            "total_blogs": total_blogs,
            "by_category": [dict(r) for r in by_category],
            "recent_posts": [dict(r) for r in recent_posts],
        }
