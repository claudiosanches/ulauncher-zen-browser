import sqlite3
import tempfile
import shutil
import configparser
import os
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class ZenBrowserDatabase:

    def __init__(self):
        #   Results order
        self.order = None

        #   Results number
        self.limit = None

        #   Set database location
        db_location = self.searchPlaces()

        if db_location is None:
            logger.error("Zen Browser database not found")
            return

        #   Temporary  file
        #   Using FF63 the DB was locked for exclusive use of FF
        #   TODO:   Regular updates of the temporary file
        temporary_db_location = tempfile.mktemp()
        shutil.copyfile(db_location, temporary_db_location)

        #   Open Zen Browser database
        self.conn = sqlite3.connect(temporary_db_location)

        #   External functions
        self.conn.create_function("hostname", 1, self.__getHostname)

    def searchPlaces(self):
        #   Zen Browser folder path
        zen_path = os.path.expanduser("~/.zen/")
        if not os.path.exists(zen_path):
            zen_path = os.path.expanduser("~/.var/app/app.zen_browser.zen/.zen/")

        #   Zen Browser profiles configuration file path
        conf_path = os.path.join(zen_path, "profiles.ini")

        # Debug
        logger.debug("Config path %s" % conf_path)
        if not os.path.exists(conf_path):
            logger.error("Zen Browser profiles.ini not found at %s" % conf_path)
            return None

        #   Profile config parse
        profile = configparser.RawConfigParser()
        profile.read(conf_path)
        
        # Zen Browser might have different profile naming, but usually Profile0 works for default
        try:
            prof_path = profile.get("Profile0", "Path")
        except (configparser.NoSectionError, configparser.NoOptionError):
            try:
                # Try finding any section that starts with Profile and has a Path
                for section in profile.sections():
                    if section.startswith("Profile") and profile.has_option(section, "Path"):
                        prof_path = profile.get(section, "Path")
                        break
                else:
                    logger.error("No profile path found in profiles.ini")
                    return None
            except Exception as e:
                logger.error("Error reading profiles.ini: %s" % e)
                return None

        #   Sqlite db directory path
        sql_path = os.path.join(zen_path, prof_path)
        sql_path = os.path.join(sql_path, "places.sqlite")

        # Debug
        logger.debug("Sql path %s" % sql_path)
        if not os.path.exists(sql_path):
            logger.error("Zen Browser places.sqlite not found at %s" % sql_path)
            return None

        return sql_path

    #   Get hostname from url
    def __getHostname(self, string):
        return urllib.parse.urlsplit(string).netloc

    def search(self, query_str):
        if not hasattr(self, 'conn'):
            return []

        #   Search subquery
        terms = query_str.split(" ")
        term_where = []
        for term in terms:
            term_where.append(
                f'((url LIKE "%{term}%") OR (moz_bookmarks.title LIKE "%{term}%") OR (moz_places.title LIKE "%{term}%"))'
            )

        where = " AND ".join(term_where)

        #    Order subquery
        order_by_dict = {
            "frequency": "frequency",
            "visit": "visit_count",
            "recent": "last_visit_date",
        }
        order_by = order_by_dict.get(self.order, "url")

        query = f"""SELECT 
            url, 
            CASE WHEN moz_bookmarks.title <> '' 
                THEN moz_bookmarks.title
                ELSE moz_places.title 
            END AS label,
            CASE WHEN moz_bookmarks.title <> '' 
                THEN 1
                ELSE 0 
            END AS is_bookmark
            FROM moz_places
                LEFT OUTER JOIN moz_bookmarks ON(moz_bookmarks.fk = moz_places.id)
            WHERE {where}
            ORDER BY is_bookmark DESC, {order_by} DESC
            LIMIT {self.limit};"""

        #   Query execution
        rows = []
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error("Error in query (%s) execution: %s" % (query, e))
        return rows

    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()
