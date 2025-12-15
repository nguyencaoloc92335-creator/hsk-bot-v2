import uvicorn
import logging
import json
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

import database
import config
from logic import router, common, learning, quiz, pause, system, menu, selection
from services import fb_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HSK_BOT")
app = FastAPI()
USER_CACHE = {}

async def run_scan_logic():
    # Lấy thời gian hiện tại
    now_ts = common.get_ts()
    now_dt = common.get_vn_time()
    today = common.get_today_str()

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

                # ==============================================
                # === XỬ LÝ 3 CHẾ ĐỘ NGHỈ (PAUSED) ===
                # ==============================================
                if mode == "PAUSED":
                    pause_info = s.get("pause_info", {})
                    if not pause_info: # Lỗi dữ liệu -> Resume
                        s["mode"] = "AUTO"
                        database.save_user_state(uid, s, USER_CACHE)
                        continue

                    p_type = pause_info.get("type", "INDEFINITE")

                    # --- LOẠI 1: NGHỈ KHÔNG THỜI HẠN (Nhắc mỗi 30p) ---
                    if p_type == "INDEFINITE":
                        last_rem = pause_info.get("last_remind", 0)
                        # 30 phút = 1800 giây
                        if (now_ts - last_rem) >= 1800:
                            fb_service.send_text(uid, "⏰ **Đã 30 phút trôi qua.**\nBạn đã nghỉ đủ chưa? Quay lại học nhé?", buttons=["Học tiếp"])
                            # Cập nhật lại mốc nhắc
                            pause_info["last_remind"] = now_ts
                            s["pause_info"] = pause_info
                            database.save_user_state(uid, s, USER_CACHE)

                    # --- LOẠI 2: NGHỈ CÓ THỜI HẠN (Nhắc tại n/2 và n) ---
                    elif p_type == "FIXED":
                        start_at = pause_info.get("start_at", 0)
                        duration = pause_info.get("duration", 0)
                        end_at = pause_info.get("end_at", 0)
                        halfway_reminded = pause_info.get("halfway_reminded", False)
                        
                        halfway_point = start_at + (duration / 2)

                        # A. Nhắc nhở tại điểm giữa (n/2)
                        if now_ts >= halfway_point and not halfway_reminded:
                            fb_service.send_text(uid, "🔔 **Đã qua một nửa thời gian nghỉ.**\nChuẩn bị tinh thần quay lại nhé!")
                            pause_info["halfway_reminded"] = True
                            s["pause_info"] = pause_info
                            database.save_user_state(uid, s, USER_CACHE)
                        
                        # B. Hết giờ (n) -> Gọi dậy và Resume
                        if now_ts >= end_at:
                            fb_service.send_text(uid, "⏰ **HẾT GIỜ NGHỈ RỒI!**\nQuay lại bàn học ngay nào! 💪", buttons=["Học tiếp"])
                            pause.resume(uid, s, USER_CACHE)

                    # --- LOẠI 3: KHÔNG LÀM PHIỀN (Chỉ nhắc khi hết giờ) ---
                    elif p_type == "DND":
                        end_at = pause_info.get("end_at", 0)
                        
                        # Chỉ khi Hết giờ mới gọi
                        if now_ts >= end_at:
                            fb_service.send_text(uid, "⏰ **KẾT THÚC DND!**\nĐã hết thời gian không làm phiền. Học tiếp nhé?", buttons=["Học tiếp"])
                            pause.resume(uid, s, USER_CACHE)
                    
                    # Khi đang Pause thì bỏ qua các logic bên dưới
                    continue 
                # ==============================================


                # (Các logic Short Break, Pre Quiz, Idle Reminder giữ nguyên như cũ)
                # ...
                # Logic Short Break
                if mode == "SHORT_BREAK":
                    if now_ts >= next_time:
                        fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nQuay lại học tiếp nhé.")
                        s["mode"] = "AUTO"; s["waiting"] = False
                        database.save_user_state(uid, s, USER_CACHE)
                        learning.send_next_word(uid, s, USER_CACHE)
                        continue

                # Logic Pre Quiz
                if mode == "PRE_QUIZ":
                    if now_ts >= next_time:
                        fb_service.send_text(uid, "🔔 **HẾT GIỜ GIẢI LAO!**\nBắt đầu bài kiểm tra 12 từ vừa học nhé.")
                        quiz.start_quiz_level(uid, s, USER_CACHE, 1)
                        continue

                # Logic Reminder (Chỉ chạy khi KHÔNG Pause)
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
                            fb_service.send_text(uid, "⏰ **Đang thi dở kìa!**\nLàm nốt bài kiểm tra nha. 💪")
                        else:
                            fb_service.send_text(uid, "⏰ **Đừng bỏ cuộc!**\nQuay lại học tiếp đi bạn ơi. 🚀")
                        s["last_remind"] = now_ts
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
def home(): return PlainTextResponse("HSK Bot Running (Pause V2)")

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
