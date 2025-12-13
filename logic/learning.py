import threading
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    if len(state["session"]) >= 6:
        from logic import quiz
        quiz.start_quiz_level(uid, state, cache, 1)
        return

    target_fields = state.get("fields", ["HSK1"])
    w = database.get_random_words_by_fields(state.get("learned", []), target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Bạn đã học hết từ trong kho **{', '.join(target_fields)}**!")
        return
    
    word = w[0]
    state["session"].append(word)
    state["learned"].append(word['Hán tự'])
    state["current_word"] = word['Hán tự']
    
    # Không gọi AI tạo ví dụ nữa
    total = database.get_total_words_by_fields(target_fields)
    
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/6 | Kho: {','.join(target_fields)})\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"🏷️ Cấp độ: {word['Field']}\n"
           f"──────────────\n"
           f"👉 Gõ lại từ **{word['Hán tự']}** để học.")
    
    fb_service.send_text(uid, msg)
    
    # Gửi Audio từ vựng
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    
    state["waiting"] = True
    state["next_time"] = 0
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    if state["waiting"]:
        cur = state.get("current_word", "")
        # Chấp nhận user gõ từ, hoặc gõ các lệnh xác nhận
        if (cur in text) or (text.lower() in ["hiểu", "ok", "tiếp", "next", "nhớ rồi"]):
            state["next_time"] = common.get_ts() + 540 # 9 phút
            state["waiting"] = False
            fb_service.send_text(uid, "✅ Đã thuộc. Hẹn 9 phút nữa ôn tập.")
            database.save_user_state(uid, state, cache)
        else:
            fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** để nhớ mặt chữ nhé.")
