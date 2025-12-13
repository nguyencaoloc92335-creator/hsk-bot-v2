import uvicorn
import logging
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

# --- THÊM ĐOẠN NÀY ĐỂ KHÔNG BỊ LỖI 404 TRANG CHỦ ---
@app.get("/")
def home():
    return PlainTextResponse("Server HSK Bot is Running!")
# ---------------------------------------------------

@app.get("/trigger_scan")
def trigger_scan():
    if common.is_sleep_mode():
        return PlainTextResponse("SLEEPING MODE")
    
    conn = database.get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM users")
                for row in cur.fetchall():
                    if isinstance(row[0], str): import json; s = json.loads(row[0])
                    else: s = row[0]
                    
                    uid = s["user_id"]
                    
                    # Chào buổi sáng
                    today = common.get_today_str()
                    if s.get("last_greet") != today:
                        fb_service.send_text(uid, "☀️ Chào buổi sáng! Gõ 'Bắt đầu' để học.")
                        s["last_greet"] = today
                        database.save_user_state(uid, s, USER_CACHE)
                        continue 

                    # Gửi bài học
                    if s["mode"]=="AUTO" and not s["waiting"] and s["next_time"]>0:
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
