import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    # Nếu học đủ 6 từ -> chuyển sang Quiz
    if len(state["session"]) >= 6:
        from logic import quiz
        quiz.start_quiz_level(uid, state, cache, 1)
        return

    # Lấy fields người dùng chọn
    target_fields = state.get("fields", ["HSK1"])
    
    # Lấy từ mới từ DB
    w = database.get_random_words_by_fields(state.get("learned", []), target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Bạn đã học hết từ vựng trong kho **{', '.join(target_fields)}**!\nHãy chọn kho khác (VD: 'Chọn HSK2').")
        return
    
    word = w[0]
    # Cập nhật session
    state["session"].append(word)
    state["learned"].append(word['Hán tự'])
    state["current_word"] = word['Hán tự']
    
    # Gọi AI (Dù AI lỗi thì hàm này đã có backup)
    ai_data = ai_service.generate_sentence_with_annotation(word)
    
    # Soạn tin nhắn
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/6)\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"🏷️ Kho: {word['Field']}\n"
           f"──────────────\n"
           f"💡 **Ví dụ:**\n"
           f"{ai_data.get('sentence_han', '...')}\n"
           f"{ai_data.get('sentence_pinyin', '')}\n"
           f"👉 {ai_data.get('sentence_viet', '')}\n")

    # Nếu có từ vựng bổ sung
    new_words = ai_data.get('new_words', [])
    if new_words and isinstance(new_words, list) and len(new_words) > 0:
        msg += "\n📝 **Từ vựng trong câu:**\n"
        for nw in new_words:
            # Kiểm tra kỹ từng field
            h = nw.get('han', '')
            p = nw.get('pinyin', '')
            v = nw.get('viet', '')
            if h: msg += f"- {h} ({p}): {v}\n"

    msg += f"\n👉 Gõ lại từ **{word['Hán tự']}** để học."
    
    fb_service.send_text(uid, msg)
    
    # Gửi Audio (Chạy ngầm)
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    
    # Gửi Audio câu ví dụ (nếu có câu ví dụ xịn)
    if len(ai_data.get('sentence_han', '')) > 1:
        threading.Thread(target=lambda: (time.sleep(2), fb_service.send_audio(uid, ai_data['sentence_han']))).start()
    
    state["waiting"] = True
    state["next_time"] = 0
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    if state["waiting"]:
        cur = state.get("current_word", "")
        # Chấp nhận gõ lại từ hoặc các lệnh xác nhận
        if (cur in text) or (text.lower() in ["hiểu", "ok", "tiếp", "next"]):
            state["next_time"] = common.get_ts() + 540 # 9 phút
            state["waiting"] = False
            fb_service.send_text(uid, "✅ Đã thuộc. Hẹn 9p nữa ôn tập.")
            database.save_user_state(uid, state, cache)
        else:
            fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** để nhớ mặt chữ nhé.")
