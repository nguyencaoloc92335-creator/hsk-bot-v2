import uvicorn
import logging
import json
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

import database
import config
# Import đầy đủ module
from logic import router, common, learning, quiz, pause, system, menu, selection
from services import fb_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HSK_BOT")
app = FastAPI()
USER_CACHE = {}

async def run_scan_logic():
    # [ĐÃ XÓA] Logic kiểm tra giờ ngủ. Bot luôn thức.
    
    # Lấy giờ hiện tại để dùng cho các logic khác (như chào hỏi)
    now_dt = common.get_vn_time()
    today = common.get_today_str()
    now_ts = common.get_ts()

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
                next_time = s.get("next_time", 0)

                # === 1. XỬ LÝ CHẾ ĐỘ TẠM DỪNG (QUAN TRỌNG) ===
                if mode == "PAUSED":
                    pause_info = s.get("pause_info", {})
                    # Nếu dữ liệu lỗi -> Tự resume
                    if not pause_info: 
                        s["mode"] = "AUTO"
                        database.save_user_state(uid, s, USER_CACHE)
                        continue

                    p_type = pause_info.get("type", "FIXED")

                    # -> Nếu là KHÔNG LÀM PHIỀN (DND): Bỏ qua luôn user này, không làm gì cả
                    if p_type == "DND":
                        continue 
                    
                    # -> Nếu là NGHỈ CÓ HẸN GIỜ (FIXED 30p)
                    if p_type == "FIXED":
                        end_at = pause_info.get("end_at", 0)
                        if now_ts >= end_at:
                            fb_service.send_text(uid, "⏰ **HẾT 30 PHÚT NGHỈ!**\nQuay lại học tiếp nhé! 💪", buttons=["Học tiếp"])
                            pause.resume(uid, s, USER_CACHE)
                    
                    # Khi đang nghỉ (và không phải DND) thì vẫn bỏ qua các logic nhắc nhở bên dưới
                    continue 
                # ==============================================

                # 2. Logic Short Break
                if mode == "SHORT_BREAK":
                    if now_ts >= next_time:
                        fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nQuay lại học tiếp nhé.")
                        s["mode"] = "AUTO"; s["waiting"] = False
                        database.save_user_state(uid, s, USER_CACHE)
                        learning.send_next_word(uid, s, USER_CACHE)
                        continue

                # 3. Logic Pre Quiz
                if mode == "PRE_QUIZ":
                    if now_ts >= next_time:
                        fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                        quiz.start_quiz_level(uid, s, USER_CACHE, 1)
                        continue
                
                # 4. Logic Chào sáng (Vẫn giữ để chào cho lịch sự, nhưng không chặn học)
                if now_dt.hour == 6 and now_dt.minute == 1:
                    if s.get("last_greet") != today:
                        fb_service.send_text(uid, "☀️ **06:01 - CHÀO BUỔI SÁNG**\nChúc bạn ngày mới năng lượng! Sẵn sàng thì gõ 'Tiếp' nhé.")
                        s["last_greet"] = today
                        database.save_user_state(uid, s, USER_CACHE)

                # 5. Logic Nhắc nhở (Idle Reminder)
                target_modes = ["AUTO", "QUIZ", "REVIEWING"]
                need_remind = False
                if mode in target_modes:
                    if mode == "AUTO":
                        if s.get("waiting", False): need_remind = True
                    else: need_remind = True 
                
                if need_remind:
                    last_act = s.get("last_interaction", now_ts)
                    last_rem = s.get("last_remind", 0)
                    
                    if (now_ts - last_act) >= 600 and (now_ts - last_rem) >= 600:
                        if mode == "QUIZ":
                            fb_service.send_text(uid, "⏰ **Đang thi dở kìa!**\nBạn ơi quay lại làm nốt bài kiểm tra nha. Cố lên! 💪")
                        else:
                            fb_service.send_text(uid, "⏰ **Đừng bỏ cuộc giữa chừng!**\nQuay lại học tiếp đi bạn ơi, đang đà phấn đấu! 🚀")
                        
                        s["last_remind"] = now_ts
                        database.save_user_state(uid, s, USER_CACHE)

                # 6. Chúc ngủ ngon (Optional)
                if now_dt.hour == 23 and now_dt.minute == 59:
                    if s.get("last_goodnight") != today:
                        fb_service.send_text(uid, "🌙 **23:59 RỒI**\nChúc bạn ngủ ngon! Bot vẫn trực, học lúc nào cũng được nhé. 💤")
                        s["last_goodnight"] = today
                        database.save_user_state(uid, s, USER_CACHE)

    except Exception as e:
        logger.error(f"Scan Error: {e}")
    finally:
        database.release_conn(conn)

@app.on_event("startup")
async def startup_event():
    database.init_and_sync_db()
    asyncio.create_task(background_timer())

async def background_timer():
    logger.info("⏳ Timer Started: Scanning every 60s...")
    while True:
        await asyncio.sleep(60)
        await run_scan_logic()

@app.get("/")
def home(): return PlainTextResponse("HSK Bot Running (No Sleep Mode)")

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
