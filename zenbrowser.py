import sqlite3
import tempfile
import shutil
import configparser
import urllib.parse
import os
import logging
from pathlib import Path
from typing import List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class ZenBrowserDatabase:
    """Handles interaction with the Zen Browser SQLite database."""

    def __init__(self):
        self.order: Optional[str] = None
        self.limit: Optional[int] = None
        self.search_type: str = "both"
        self.conn: Optional[sqlite3.Connection] = None
        self.temp_db_path: Optional[str] = None

        db_location = self.search_places()

        if db_location:
            try:
                # Create a temporary copy to avoid database locking issues
                fd, self.temp_db_path = tempfile.mkstemp()
                os.close(fd)
                shutil.copyfile(db_location, self.temp_db_path)

                self.conn = sqlite3.connect(self.temp_db_path)
                self.conn.create_function("hostname", 1, self._get_hostname)
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
        else:
            logger.error("Zen Browser database (places.sqlite) could not be located.")

    def search_places(self) -> Optional[Path]:
        """Locates the 'places.sqlite' file in Zen Browser profile directories."""
        possible_paths = [
            Path.home() / ".zen",
            Path.home() / ".var/app/app.zen_browser.zen/.zen"
        ]

        zen_path = next((p for p in possible_paths if p.exists()), None)
        if not zen_path:
            logger.debug("Zen Browser configuration directory not found in standard locations.")
            return None

        conf_path = zen_path / "profiles.ini"
        if not conf_path.exists():
            logger.error(f"profiles.ini not found at {conf_path}")
            return None

        profile = configparser.RawConfigParser()
        profile.read(conf_path)

        prof_path = None
        if profile.has_section("Profile0"):
            prof_path = profile.get("Profile0", "Path", fallback=None)

        if not prof_path:
            for section in profile.sections():
                if section.startswith("Profile") and profile.has_option(section, "Path"):
                    prof_path = profile.get(section, "Path")
                    break

        if not prof_path:
            logger.error("No profile path found in profiles.ini")
            return None

        # Handle both relative and absolute paths in profiles.ini
        is_relative = profile.getint("Profile0", "IsRelative", fallback=1) == 1
        sql_path = (zen_path / prof_path if is_relative else Path(prof_path)) / "places.sqlite"

        if not sql_path.exists():
            logger.error(f"places.sqlite not found at {sql_path}")
            return None

        logger.debug(f"Found Zen Browser database at: {sql_path}")
        return sql_path

    @staticmethod
    def _get_hostname(url: str) -> str:
        """Extracts hostname from a given URL."""
        return urllib.parse.urlsplit(url).netloc

    def search(self, query_str: str) -> List[Tuple[Any, ...]]:
        """Searches for bookmarks and history matching the query string."""
        if not self.conn:
            return []

        terms = query_str.strip().split()
        if not terms:
            return []

        term_conditions = []
        params = []
        for term in terms:
            term_conditions.append(
                "((url LIKE ?) OR (moz_bookmarks.title LIKE ?) OR (moz_places.title LIKE ?))"
            )
            like_term = f"%{term}%"
            params.extend([like_term, like_term, like_term])

        where_clause = " AND ".join(term_conditions)

        # Filtering based on search_type
        if self.search_type == "bookmarks":
            where_clause += " AND moz_bookmarks.id IS NOT NULL"
        elif self.search_type == "history":
            where_clause += " AND moz_bookmarks.id IS NULL"

        order_by_dict = {
            "frecency": "frecency",
            "visit": "visit_count",
            "recent": "last_visit_date",
        }
        order_by = order_by_dict.get(self.order, "frecency")

        query = f"""SELECT 
            url, 
            CASE WHEN moz_bookmarks.title IS NOT NULL AND moz_bookmarks.title <> '' 
                THEN moz_bookmarks.title
                ELSE moz_places.title 
            END AS label,
            CASE WHEN moz_bookmarks.title IS NOT NULL AND moz_bookmarks.title <> '' 
                THEN 1
                ELSE 0 
            END AS is_bookmark
            FROM moz_places
                LEFT OUTER JOIN moz_bookmarks ON(moz_bookmarks.fk = moz_places.id)
            WHERE {where_clause}
            ORDER BY is_bookmark DESC, {order_by} DESC
            LIMIT ?;"""
        
        # Use provided limit, but allow 0. Default to 5 if None.
        limit = self.limit if self.limit is not None else 5
        params.append(limit)

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []

    def close(self):
        """Closes the database connection and removes the temporary file."""
        if self.conn:
            self.conn.close()
            self.conn = None
        
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception as e:
                logger.error(f"Error removing temporary database file: {e}")
            finally:
                self.temp_db_path = None
