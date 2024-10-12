import sqlite3

from config import DATABASE


class StatsHolder:
    def create_db(self):
        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS played_counter ("
                "guild_id INTEGER NOT NULL UNIQUE, count INTEGER DEFAULT 0 NOT NULL)"
            )

    def increment_song_counter(self, guild_id):
        with sqlite3.connect(DATABASE) as cur:
            cur.execute("INSERT OR IGNORE INTO played_counter (guild_id) VALUES(?)", (guild_id,))
            cur.execute("UPDATE played_counter SET count = count + 1 WHERE guild_id = ?", (guild_id,))

    def get_count(self, guild_id):
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count FROM played_counter WHERE guild_id=?", (guild_id,))
            count = cur.fetchone()[0]
        return count
