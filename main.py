import uvicorn
import logging
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

# Import các module
import database
import config
from logic import router, common, learning
from services import fb_service

logging.basicConfig(level=logging.INFO)
app = FastAPI()
USER_CACHE = {}

@app.on_event("startup")
def startup():
    database.init_db()

@app.get("/")
def home():
    return PlainTextResponse("Server HSK Bot is Running!")

@app.get("/trigger_scan")
def trigger_scan():
    # 1. Cronjob ngủ 0h-6h
    if common.is_sleep_mode():
        return PlainTextResponse("SLEEPING MODE")
    
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

                    # --- LOGIC XỬ LÝ PAUSE (MỚI) ---
                    if mode == "PAUSED":
                        p_info = s.get("pause_info", {})
                        now = common.get_ts()
                        
                        # Case 1: Nghỉ CỐ ĐỊNH (FIXED)
                        if p_info.get("type") == "FIXED":
                            end_at = p_info.get("end_at", 0)
                            if now >= end_at:
                                fb_service.send_text(uid, "⏰ **Hết giờ giải lao rồi!**\nBạn đã sẵn sàng học tiếp chưa? (Gõ 'Tiếp' nhé)")
                                # Chuyển sang nhắc mỗi 30p nếu user chưa dậy
                                s["pause_info"]["type"] = "INDEFINITE"
                                s["pause_info"]["last_remind"] = now
                                database.save_user_state(uid, s, USER_CACHE)
                        
                        # Case 2: Nghỉ KHÔNG CỐ ĐỊNH (INDEFINITE)
                        elif p_info.get("type") == "INDEFINITE":
                            last_remind = p_info.get("last_remind", 0)
                            # Nhắc mỗi 30 phút (1800 giây)
                            if now >= last_remind + 1800:
                                fb_service.send_text(uid, "🔔 30 phút trôi qua rồi.\nBạn đã rảnh để học tiếp chưa? (Gõ 'Tiếp' để quay lại)")
                                s["pause_info"]["last_remind"] = now
                                database.save_user_state(uid, s, USER_CACHE)
                        
                        # Đã xử lý Pause xong, bỏ qua các logic dưới
                        continue 
                    # -------------------------------
                    
                    # 2. Chào buổi sáng
                    today = common.get_today_str()
                    if s.get("last_greet") != today:
                        fb_service.send_text(uid, "☀️ Chào buổi sáng! Gõ 'Bắt đầu' để học.")
                        s["last_greet"] = today
                        database.save_user_state(uid, s, USER_CACHE)
                        continue 

                    # 3. Gửi bài học (Auto)
                    if mode == "AUTO" and not s.get("waiting") and s.get("next_time", 0) > 0:
                        if common.get_ts() >= s["next_time"]:
                            USER_CACHE[uid] = s
                            learning.send_next_word(uid, s, USER_CACHE)
        finally:
            database.release_conn(conn)
            
    return PlainTextResponse("SCAN OK")

@app.post("/webhook")
async def webhook(req: Request, bg: BackgroundTasks):
    try:
        d = await req.json()
        if 'entry' in d:
            for e in d['entry']:
                for m in e.get('messaging', []):
                    if 'message' in m:
                        uid = m['sender']['id']
                        text = m['message'].get('text', '')
                        bg.add_task(router.process_message, uid, text, USER_CACHE)
    except: pass
    return PlainTextResponse("EVENT_RECEIVED")

@app.get("/webhook")
def verify(req: Request):
    if req.query_params.get("hub.verify_token") == config.VERIFY_TOKEN:
        return PlainTextResponse(req.query_params.get("hub.challenge"))
    return PlainTextResponse("Error", 403)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
