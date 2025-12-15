import psycopg2
from psycopg2 import pool
import json
import logging
from config import DATABASE_URL
from hsk_data import DATA_SOURCE #

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
            # 1. Tạo bảng Users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(50) PRIMARY KEY, 
                    state JSONB, 
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 2. Tạo bảng Words
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words_new (
                    id SERIAL PRIMARY KEY, 
                    hanzi VARCHAR(50) NOT NULL, 
                    pinyin VARCHAR(100), 
                    meaning TEXT, 
                    field VARCHAR(50) NOT NULL,
                    UNIQUE(hanzi, field)
                );
            """)

            # 3. Tạo bảng Custom Lists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS custom_lists (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    list_name VARCHAR(100),
                    word_ids JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Đồng bộ dữ liệu
            data_to_sync = DATA_SOURCE if isinstance(DATA_SOURCE, dict) else {"HSK_CHUNG": DATA_SOURCE}
            total_added = 0
            for field_name, word_list in data_to_sync.items():
                for w in word_list:
                    hanzi = w.get('hanzi') or w.get('Hán tự')
                    pinyin = w.get('pinyin') or w.get('Pinyin')
                    meaning = w.get('meaning') or w.get('Nghĩa')
                    if not hanzi: continue
                    
                    cur.execute("""
                        INSERT INTO words_new (hanzi, pinyin, meaning, field) 
                        VALUES (%s, %s, %s, %s) 
                        ON CONFLICT (hanzi, field) DO NOTHING
                    """, (hanzi, pinyin, meaning, field_name))
                    if cur.rowcount > 0: total_added += 1
            
            logger.info(f"✅ DB Synced. Added: {total_added} words.")
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Init DB Failed: {e}")
        conn.rollback()
    finally: release_conn(conn)

# --- USER STATE ---
def get_user_state(uid, cache):
    if uid in cache: return cache[uid]
    
    all_fields = ["HSK1"]
    conn = get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT field FROM words_new")
                rows = cur.fetchall()
                if rows: all_fields = [r[0] for r in rows]
        finally: release_conn(conn)

    s = {
        "user_id": uid, "mode": "IDLE", 
        "learned": [], "session": [], 
        "next_time": 0, "waiting": False, 
        "fields": all_fields,
        "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0},
        "custom_learn": {"active": False, "queue": []}
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

# --- WORD QUERIES ---

def get_random_words_by_fields(exclude_list, target_fields, count=1):
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            query = """
                SELECT hanzi, pinyin, meaning, field, id
                FROM words_new 
                WHERE field = ANY(%s) 
                AND hanzi NOT IN %s 
                ORDER BY RANDOM() LIMIT %s
            """
            exclude_tuple = tuple(exclude_list) if exclude_list else ('',)
            cur.execute(query, (target_fields, exclude_tuple, count))
            return [{"Hán tự": r[0], "Pinyin": r[1], "Nghĩa": r[2], "Field": r[3], "id": r[4]} for r in cur.fetchall()]
    finally: release_conn(conn)

def get_total_words_by_fields(target_fields):
    conn = get_conn()
    if not conn: return 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM words_new WHERE field = ANY(%s)", (target_fields,))
            return cur.fetchone()[0]
    finally: release_conn(conn)

def get_all_fields_stats():
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT field, COUNT(*) FROM words_new GROUP BY field ORDER BY field")
            return cur.fetchall()
    finally: release_conn(conn)

# --- [MỚI] HÀM ĐẾM TIẾN ĐỘ CHÍNH XÁC ---
def get_count_learned_in_fields(learned_list, target_fields):
    """Đếm xem có bao nhiêu từ trong learned_list thuộc về target_fields"""
    if not learned_list or not target_fields: return 0
    conn = get_conn()
    if not conn: return 0
    try:
        with conn.cursor() as cur:
            # Chỉ đếm những từ vừa có trong danh sách đã học, vừa thuộc kho đang chọn
            query = "SELECT COUNT(*) FROM words_new WHERE hanzi = ANY(%s) AND field = ANY(%s)"
            cur.execute(query, (learned_list, target_fields))
            return cur.fetchone()[0]
    finally: release_conn(conn)

# --- CUSTOM LIST QUERIES ---

def get_all_words_by_field_raw(field_name):
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, hanzi, meaning FROM words_new WHERE field = %s ORDER BY id", (field_name,))
            return [{"id": r[0], "hanzi": r[1], "meaning": r[2]} for r in cur.fetchall()]
    finally: release_conn(conn)

def get_words_by_ids(id_list):
    if not id_list: return []
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT hanzi, pinyin, meaning, field, id FROM words_new WHERE id = ANY(%s)", (id_list,))
            return [{"Hán tự": r[0], "Pinyin": r[1], "Nghĩa": r[2], "Field": r[3], "id": r[4]} for r in cur.fetchall()]
    finally: release_conn(conn)

def create_custom_list(uid, name, word_ids):
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO custom_lists (user_id, list_name, word_ids) VALUES (%s, %s, %s)", 
                        (uid, name, json.dumps(word_ids)))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Create List Error: {e}")
        return False
    finally: release_conn(conn)
