import psycopg2
from psycopg2 import pool
import json
import logging
from config import DATABASE_URL
from hsk_data import DATA_SOURCE

logger = logging.getLogger(__name__)

db_pool = None
try:
    if DATABASE_URL:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, dsn=DATABASE_URL)
except Exception as e:
    logger.error(f"❌ DB Error: {e}")

def get_conn(): return db_pool.getconn() if db_pool else None
def release_conn(conn): 
    if db_pool and conn: db_pool.putconn(conn)

def init_and_sync_db():
    conn = get_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(50) PRIMARY KEY, 
                    state JSONB, 
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words_new (
                    id SERIAL PRIMARY KEY, 
                    hanzi VARCHAR(50) NOT NULL, 
                    pinyin VARCHAR(100), 
                    meaning TEXT, 
                    field VARCHAR(20) NOT NULL,
                    UNIQUE(hanzi, field)
                );
            """)
            
            total_added = 0
            for field_name, word_list in DATA_SOURCE.items():
                for w in word_list:
                    cur.execute("""
                        INSERT INTO words_new (hanzi, pinyin, meaning, field) 
                        VALUES (%s, %s, %s, %s) 
                        ON CONFLICT (hanzi, field) DO NOTHING
                    """, (w['hanzi'], w['pinyin'], w['meaning'], field_name))
                    if cur.rowcount > 0: total_added += 1
            
            logger.info(f"✅ Đã đồng bộ Database. Thêm mới: {total_added} từ.")
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Init DB Failed: {e}")
        conn.rollback()
    finally: release_conn(conn)

def get_user_state(uid, cache):
    if uid in cache: return cache[uid]
    s = {
        "user_id": uid, "mode": "IDLE", 
        "learned": [], "session": [], 
        "next_time": 0, "waiting": False, 
        "fields": ["HSK1"], # Mặc định
        "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
    }
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

def get_random_words_by_fields(exclude_list, target_fields, count=1):
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            query = """
                SELECT hanzi, pinyin, meaning, field 
                FROM words_new 
                WHERE field = ANY(%s) 
                AND hanzi NOT IN %s 
                ORDER BY RANDOM() LIMIT %s
            """
            exclude_tuple = tuple(exclude_list) if exclude_list else ('',)
            cur.execute(query, (target_fields, exclude_tuple, count))
            return [{"Hán tự": r[0], "Pinyin": r[1], "Nghĩa": r[2], "Field": r[3]} for r in cur.fetchall()]
    finally: release_conn(conn)

def get_total_words_by_fields(target_fields):
    conn = get_conn()
    if not conn: return 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM words_new WHERE field = ANY(%s)", (target_fields,))
            return cur.fetchone()[0]
    finally: release_conn(conn)

# --- HÀM MỚI THÊM: Lấy thống kê tất cả các trường ---
def get_all_fields_stats():
    """Trả về danh sách: [('HSK1', 150), ('HSK2', 300)]"""
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT field, COUNT(*) FROM words_new GROUP BY field ORDER BY field")
            return cur.fetchall()
    finally: release_conn(conn)
