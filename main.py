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
    
    now_dt = common.get_vn_time()
    current_hour = now_dt.hour
    current_minute = now_dt.minute
    is_sleeping = 0 <= current_hour < 6

    conn = database.get_conn()
    if not conn: return

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT state FROM users")
            rows = cur.fetchall()
            
            for row in rows:
                if isinstance(row[0], str): s = json.loads(row[0])
                else: s = row[0]
                
                uid = s["user_id"]
                mode = s.get("mode", "IDLE")
                now_ts = common.get_ts()
                next_time = s.get("next_time", 0)
                today = common.get_today_str()

                # --- A. LOGIC HẸN GIỜ (KHI KHÔNG NGỦ) ---
                if not is_sleeping:
                    # 1. Short Break
                    if mode == "SHORT_BREAK":
                        if now_ts >= next_time:
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nQuay lại học tiếp nhé.")
                            s["mode"] = "AUTO"
                            s["waiting"] = False
                            USER_CACHE[uid] = s
                            database.save_user_state(uid, s, USER_CACHE)
                            learning.send_next_word(uid, s, USER_CACHE)
                            continue

                    # 2. Pre Quiz
                    if mode == "PRE_QUIZ":
                        if now_ts >= next_time:
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                            USER_CACHE[uid] = s
                            quiz.start_quiz_level(uid, s, USER_CACHE, 1)
                            continue
                    
                    # 3. Chào buổi sáng (06:01)
                    if current_hour == 6 and current_minute == 1:
                        if s.get("last_greet") != today:
                            fb_service.send_text(uid, "☀️ **06:01 - CHÀO BUỔI SÁNG**\nChúc bạn ngày mới tốt lành! Gõ 'Bắt đầu' để học nhé.")
                            s["last_greet"] = today
                            database.save_user_state(uid, s, USER_CACHE)

                    # ========================================================
                    # 4. NHẮC NHỞ NGƯỜI DÙNG QUÊN TRẢ LỜI (IDLE REMINDER)
                    # ========================================================
                    # Chỉ nhắc khi Mode là: AUTO (đang chờ), QUIZ (đang thi), REVIEWING (đang xem list)
                    target_modes = ["AUTO", "QUIZ", "REVIEWING"]
                    
                    # Kiểm tra kỹ hơn: AUTO thì phải đang waiting=True mới nhắc
                    need_remind = False
                    if mode in target_modes:
                        if mode == "AUTO":
                            if s.get("waiting", False): need_remind = True
                        else:
                            need_remind = True # QUIZ và REVIEWING luôn cần user phản hồi
                    
                    if need_remind:
                        last_act = s.get("last_interaction", now_ts) # Lần cuối user nhắn
                        last_rem = s.get("last_remind", 0)           # Lần cuối bot nhắc
                        
                        # Nếu đã im lặng hơn 10 phút (600s)
                        if (now_ts - last_act) >= 600:
                            # Và khoảng cách với lần nhắc trước cũng > 10 phút (để nhắc lại mỗi 10p)
                            if (now_ts - last_rem) >= 600:
                                if mode == "QUIZ":
                                    fb_service.send_text(uid, "⏰ **Đang thi dở kìa!**\nBạn ơi quay lại làm nốt bài kiểm tra nha. Cố lên! 💪")
                                else:
                                    fb_service.send_text(uid, "⏰ **Đừng bỏ cuộc giữa chừng!**\nQuay lại học tiếp đi bạn ơi, đang đà phấn đấu! 🚀")
                                
                                # Cập nhật thời gian nhắc gần nhất
                                s["last_remind"] = now_ts
                                database.save_user_state(uid, s, USER_CACHE)


                # --- B. LOGIC HỆ THỐNG (CHẠY KỂ CẢ KHI SẮP NGỦ) ---
                # 5. Chúc ngủ ngon (23:59)
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
    asyncio.create_task(background_timer())

async def background_timer():
    logger.info("⏳ Timer Started: Scanning every 60s...")
    while True:
        await asyncio.sleep(60)
        await run_scan_logic()

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return PlainTextResponse("HSK Bot Running with Idle Reminder")

@app.get("/trigger_scan")
async def trigger_scan_manual():
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
