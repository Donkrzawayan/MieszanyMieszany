from datetime import datetime
import sqlite3

import pytz

from config import DATABASE, TIMEZONE


def create_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS played_counter (
                guild_id INTEGER NOT NULL UNIQUE, 
                count INTEGER DEFAULT 0 NOT NULL
        )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS voice_meeting (
                guild_id INTEGER NOT NULL, 
                start DATETIME NOT NULL, 
                end DATETIME NOT NULL
        )"""
        )


def increment_song_counter(guild_id):
    with sqlite3.connect(DATABASE) as cur:
        cur.execute("INSERT OR IGNORE INTO played_counter (guild_id) VALUES(?)", (guild_id,))
        cur.execute("UPDATE played_counter SET count = count + 1 WHERE guild_id = ?", (guild_id,))


def get_count(guild_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count FROM played_counter WHERE guild_id=?", (guild_id,))
        count = cur.fetchone()[0]
    return count


def add_meeting(guild_id, start, end):
    with sqlite3.connect(DATABASE) as cur:
        cur.execute("INSERT INTO voice_meeting (guild_id, start, end) VALUES(?,?,?)", (guild_id, start, end))


def top3_meetings(guild_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT datetime(start), (JULIANDAY(end) - JULIANDAY(start)) * 24 * 60 * 60 
            FROM voice_meeting 
            WHERE guild_id=? 
            ORDER BY (JULIANDAY(end) - JULIANDAY(start)) DESC""",
            (guild_id,),
        )
        top3 = []
        for start, duration in cur.fetchmany(3):
            start = _convert_from_utc(start)
            duration = hhmmss_format(duration)
            top3.append((start, duration))
        return top3


def _convert_from_utc(time):
    utc = pytz.utc
    dest = pytz.timezone(TIMEZONE)
    time_utc = datetime.strptime(time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
    time_dest = time_utc.astimezone(dest)
    return time_dest.strftime("%Y-%m-%d %H:%M:%S")


def hhmmss_format(sec):
    sec = int(sec)
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    seconds = sec % 60
    return f"{hours}:{minutes:02}:{seconds:02}"
