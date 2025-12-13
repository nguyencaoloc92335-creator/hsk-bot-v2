import uvicorn
import logging
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

import database
import config
from logic import router, common, learning, quiz # <--- Import thêm quiz
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

                    # 1. Xử lý PRE_QUIZ (Chờ 9 phút sau khi học 12 từ)
                    if mode == "PRE_QUIZ":
                        next_time = s.get("next_time", 0)
                        now = common.get_ts()
                        
                        # Nếu đã hết giờ chờ -> Bắt đầu thi
                        if now >= next_time:
                            fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                            USER_CACHE[uid] = s
                            quiz.start_quiz_level(uid, s, USER_CACHE, 1) # Bắt đầu Level 1
                        continue

                    # 2. Xử lý Pause (Như bài trước - giữ nguyên)
                    if mode == "PAUSED":
                        # ... (Logic pause cũ của bạn) ...
                        pass # Bạn giữ nguyên code phần Pause ở bài trước nhé

                    # 3. Chào buổi sáng (Giữ nguyên)
                    today = common.get_today_str()
                    if s.get("last_greet") != today:
                        fb_service.send_text(uid, "☀️ Chào buổi sáng! Gõ 'Bắt đầu' để học.")
                        s["last_greet"] = today
                        database.save_user_state(uid, s, USER_CACHE)

                    # Lưu ý: Logic AUTO cũ (waiting time 9p cho từng từ) đã bị loại bỏ 
                    # vì giờ chúng ta dồn 9p vào cuối 12 từ.
                    
        finally: database.release_conn(conn)
            
    return PlainTextResponse("SCAN OK")

# ... (Phần webhook giữ nguyên) ...
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
