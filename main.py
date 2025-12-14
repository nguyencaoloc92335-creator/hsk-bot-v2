import uvicorn
import logging
import json
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

import database
import config
from logic import router, common, learning, quiz
from services import fb_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HSK_BOT")
app = FastAPI()
USER_CACHE = {}

# --- HÀM QUÉT HỆ THỐNG (CORE LOGIC) ---
async def run_scan_logic():
    """Hàm này sẽ chạy mỗi 60 giây để kiểm tra giờ"""
    
    # 1. Kiểm tra giờ ngủ (0h - 6h sáng thì không làm phiền, TRỪ việc chúc ngủ ngon lúc 23:59)
    now_dt = common.get_vn_time()
    current_hour = now_dt.hour
    current_minute = now_dt.minute
    
    # Nếu đang giờ ngủ (0-5h), bỏ qua logic học tập, chỉ giữ logic hệ thống nếu cần
    is_sleeping = 0 <= current_hour < 6

    conn = database.get_conn()
    if not conn: return

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT state FROM users")
            rows = cur.fetchall() # Lấy hết data ra trước để tránh lock DB lâu
            
            for row in rows:
                if isinstance(row[0], str): s = json.loads(row[0])
                else: s = row[0]
                
                uid = s["user_id"]
                mode = s.get("mode", "IDLE")
                now_ts = common.get_ts()
                next_time = s.get("next_time", 0)
                today = common.get_today_str()

                # --- A. LOGIC HẸN GIỜ (CHỈ CHẠY KHI KHÔNG NGỦ) ---
                if not is_sleeping:
                    # 1. Hết giờ nghỉ giải lao ngắn (SHORT_BREAK) -> Học tiếp
                    if mode == "SHORT_BREAK":
                        if now_ts >= next_time:
                            logger.info(f"User {uid}: End Short Break")
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nQuay lại học tiếp nhé.")
                            
                            s["mode"] = "AUTO"
                            s["waiting"] = False
                            USER_CACHE[uid] = s
                            database.save_user_state(uid, s, USER_CACHE)
                            
                            # Gửi từ mới ngay
                            learning.send_next_word(uid, s, USER_CACHE)
                            continue

                    # 2. Hết giờ nghỉ chờ thi (PRE_QUIZ) -> Vào thi
                    if mode == "PRE_QUIZ":
                        if now_ts >= next_time:
                            logger.info(f"User {uid}: Start Quiz")
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                            
                            USER_CACHE[uid] = s
                            quiz.start_quiz_level(uid, s, USER_CACHE, 1)
                            continue
                    
                    # 3. Chào buổi sáng (6:01)
                    if current_hour == 6 and current_minute == 1:
                        if s.get("last_greet") != today:
                            fb_service.send_text(uid, "☀️ **06:01 - CHÀO BUỔI SÁNG**\nChúc bạn ngày mới tốt lành! Gõ 'Bắt đầu' để học nhé.")
                            s["last_greet"] = today
                            database.save_user_state(uid, s, USER_CACHE)

                # --- B. LOGIC HỆ THỐNG (CHẠY KỂ CẢ KHI SẮP NGỦ) ---
                
                # 4. Chúc ngủ ngon (23:59)
                if current_hour == 23 and current_minute == 59:
                    if s.get("last_goodnight") != today:
                        fb_service.send_text(uid, "🌙 **23:59 RỒI**\nChúc bạn ngủ ngon và hẹn gặp lại sáng mai! 💤")
                        s["last_goodnight"] = today
                        database.save_user_state(uid, s, USER_CACHE)

    except Exception as e:
        logger.error(f"Scan Error: {e}")
    finally:
        database.release_conn(conn)

# --- BACKGROUND TIMER ---
@app.on_event("startup")
async def startup_event():
    database.init_and_sync_db()
    # Khởi chạy vòng lặp background
    asyncio.create_task(background_timer())

async def background_timer():
    """Vòng lặp vĩnh cửu, chạy mỗi 60s"""
    logger.info("⏳ Timer Started: Scanning every 60s...")
    while True:
        await asyncio.sleep(60) # Chờ 60 giây
        await run_scan_logic()  # Chạy logic kiểm tra

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return PlainTextResponse("HSK Bot Running with Auto-Timer")

@app.get("/trigger_scan")
async def trigger_scan_manual():
    """Endpoint để gọi thủ công nếu muốn test ngay"""
    await run_scan_logic()
    return PlainTextResponse("Manual Scan OK")

@app.post("/webhook")
async def webhook(req: Request, bg: BackgroundTasks):
    try:
        d = await req.json()
        if 'entry' in d:
            for e in d['entry']:
                for m in e.get('messaging', []):
                    if 'message' in m:
                        bg.add_task(router.process_message, m['sender']['id'], m['message'].get('text', ''), USER_CACHE)
    except: pass
    return PlainTextResponse("OK")

@app.get("/webhook")
def verify(req: Request):
    if req.query_params.get("hub.verify_token") == config.VERIFY_TOKEN:
        return PlainTextResponse(req.query_params.get("hub.challenge"))
    return PlainTextResponse("Error", 403)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
