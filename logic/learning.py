import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    # Logic kiểm tra giờ ngủ đã có ở Router/Cron, nhưng check lại cho chắc
    if common.is_sleep_mode(): return

    # Nếu học đủ 6 từ -> Sang Quiz
    if len(state["session"]) >= 6:
        from logic import quiz
        quiz.start_quiz_level(uid, state, cache, 1)
        return

    # Lấy từ mới
    w = database.get_random_words(state.get("learned", []), 1)
    if not w: 
        fb_service.send_text(uid, "🎉 Hết từ vựng! Reset hoặc thêm từ mới.")
        return
    
    word = w[0]
    state["session"].append(word)
    state["learned"].append(word['Hán tự'])
    state["current_word"] = word['Hán tự'] # Lưu từ hiện tại để check
    
    ex = ai_service.generate_example(word)
    total = database.get_total_words()
    
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/6 | Kho: {total})\n\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"----------------\n"
           f"VD: {ex['han']}\n👉 {ex['viet']}\n\n"
           f"👉 Gõ lại từ **{word['Hán tự']}** để học.")
    
    fb_service.send_text(uid, msg)
    
    # Gửi audio (chạy thread để không block)
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    threading.Thread(target=lambda: (time.sleep(2), fb_service.send_audio(uid, ex['han']))).start()
    
    state["waiting"] = True
    state["next_time"] = 0
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    if state["waiting"]:
        cur = state.get("current_word","")
        # Chấp nhận gõ đúng từ hoặc các lệnh xác nhận
        if (cur in text) or (text.lower() in ["hiểu","ok","tiếp"]):
            state["next_time"] = common.get_ts() + 540 # 9 phút
            state["waiting"] = False
            fb_service.send_text(uid, "✅ Đã thuộc. Hẹn 9p nữa.")
            database.save_user_state(uid, state, cache)
        else:
            fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** nhé.")
    else:
        # Đang chờ timer mà user nhắn
        if "tiếp" in text.lower():
            send_next_word(uid, state, cache)
        else:
            fb_service.send_text(uid, ai_service.chat_reply(text))