import uvicorn
import logging
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

import database
import config
from logic import router, common, learning, quiz
from services import fb_service

logging.basicConfig(level=logging.INFO)
app = FastAPI()
USER_CACHE = {}

@app.on_event("startup")
def startup():
    database.init_and_sync_db()

@app.get("/")
def home():
    return PlainTextResponse("HSK Bot Running")

@app.get("/trigger_scan")
def trigger_scan():
    if common.is_sleep_mode(): return PlainTextResponse("SLEEP")
    
    conn = database.get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM users")
                for row in cur.fetchall():
                    if isinstance(row[0], str): s = json.loads(row[0])
                    else: s = row[0]
                    
                    uid = s["user_id"]
                    mode = s.get("mode", "IDLE")
                    
                    # Lấy thời gian hiện tại (Giờ và Phút)
                    now_ts = common.get_ts()
                    now_dt = common.get_vn_time()
                    current_hour = now_dt.hour
                    current_minute = now_dt.minute
                    today = common.get_today_str()
                    
                    next_time = s.get("next_time", 0)

                    # 1. Xử lý PRE_QUIZ (Hết giờ nghỉ -> Vào thi)
                    if mode == "PRE_QUIZ":
                        if now_ts >= next_time:
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                            USER_CACHE[uid] = s
                            quiz.start_quiz_level(uid, s, USER_CACHE, 1)
                        continue

                    # 2. Xử lý SHORT_BREAK (Hết giờ nghỉ -> Học tiếp)
                    if mode == "SHORT_BREAK":
                        if now_ts >= next_time:
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nQuay lại học tiếp nhé.")
                            s["mode"] = "AUTO"
                            s["waiting"] = False
                            USER_CACHE[uid] = s
                            database.save_user_state(uid, s, USER_CACHE)
                            learning.send_next_word(uid, s, USER_CACHE)
                        continue

                    # 3. CHÚC NGỦ NGON (Chính xác lúc 23:59)
                    if current_hour == 23 and current_minute == 59:
                        if s.get("last_goodnight") != today:
                            fb_service.send_text(uid, "🌙 **23:59 RỒI**\nChúc bạn ngủ ngon và hẹn gặp lại sáng mai! 💤")
                            s["last_goodnight"] = today
                            database.save_user_state(uid, s, USER_CACHE)

                    # 4. CHÀO BUỔI SÁNG (Chính xác lúc 06:01)
                    if current_hour == 6 and current_minute == 1:
                        if s.get("last_greet") != today:
                            fb_service.send_text(uid, "☀️ **06:01 - CHÀO BUỔI SÁNG**\nChúc bạn ngày mới tốt lành! Gõ 'Bắt đầu' để học nhé.")
                            s["last_greet"] = today
                            database.save_user_state(uid, s, USER_CACHE)

        finally: database.release_conn(conn)
            
    return PlainTextResponse("SCAN OK")

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
