import psycopg2
from psycopg2 import pool
import json
import logging
from config import DATABASE_URL
try:
    from hsk_data import HSK_DATA
except ImportError:
    HSK_DATA = []

logger = logging.getLogger(__name__)

db_pool = None
try:
    if DATABASE_URL:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, dsn=DATABASE_URL)
        logger.info("✅ Database connected!")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")

def get_conn():
    return db_pool.getconn() if db_pool else None

def release_conn(conn):
    if db_pool and conn: db_pool.putconn(conn)

def init_db():
    conn = get_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (user_id VARCHAR(50) PRIMARY KEY, state JSONB, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")
            cur.execute("""CREATE TABLE IF NOT EXISTS words (id SERIAL PRIMARY KEY, hanzi VARCHAR(50) UNIQUE NOT NULL, pinyin VARCHAR(100), meaning TEXT, level INT DEFAULT 2);""")
            
            # Seed data
            cur.execute("SELECT COUNT(*) FROM words")
            if cur.fetchone()[0] == 0 and HSK_DATA:
                valid_data = [x for x in HSK_DATA if 'Hán tự' in x]
                if valid_data:
                    args_str = ','.join(cur.mogrify("(%s,%s,%s)", (x['Hán tự'], x['Pinyin'], x['Nghĩa'])).decode('utf-8') for x in valid_data)
                    cur.execute("INSERT INTO words (hanzi, pinyin, meaning) VALUES " + args_str)
        conn.commit()
    except Exception as e:
        logger.error(f"Init DB Error: {e}")
        conn.rollback()
    finally: release_conn(conn)

def get_user_state(uid, cache):
    if uid in cache: return cache[uid]
    s = {"user_id": uid, "mode": "IDLE", "learned": [], "session": [], "next_time": 0, "waiting": False, "temp_word": None, "last_greet": "", "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}}
    conn = get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM users WHERE user_id = %s", (uid,))
                row = cur.fetchone()
                if row and row[0]:
                    db_s = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    s.update(db_s)
        finally: release_conn(conn)
    cache[uid] = s
    return s

def save_user_state(uid, s, cache):
    cache[uid] = s
    conn = get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (user_id, state) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET state = EXCLUDED.state", (uid, json.dumps(s)))
            conn.commit()
        finally: release_conn(conn)

def get_random_words(exclude, count=1):
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            if exclude:
                cur.execute("SELECT hanzi, pinyin, meaning FROM words WHERE hanzi NOT IN %s ORDER BY RANDOM() LIMIT %s", (tuple(exclude), count))
            else:
                cur.execute("SELECT hanzi, pinyin, meaning FROM words ORDER BY RANDOM() LIMIT %s", (count,))
            return [{"Hán tự": r[0], "Pinyin": r[1], "Nghĩa": r[2]} for r in cur.fetchall()]
    except: return []
    finally: release_conn(conn)

def get_total_words():
    conn = get_conn()
    if not conn: return 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM words")
            return cur.fetchone()[0]
    finally: release_conn(conn)

def add_word(hanzi, pinyin, meaning):
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO words (hanzi, pinyin, meaning) VALUES (%s, %s, %s) ON CONFLICT (hanzi) DO NOTHING", (hanzi, pinyin, meaning))
        conn.commit(); return True
    except: return False
    finally: release_conn(conn)