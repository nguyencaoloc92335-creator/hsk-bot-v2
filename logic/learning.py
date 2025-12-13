import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    if len(state["session"]) >= 6:
        from logic import quiz
        quiz.start_quiz_level(uid, state, cache, 1)
        return

    # Lấy danh sách trường user đang chọn
    target_fields = state.get("fields", ["HSK2"])
    
    # Lấy từ ngẫu nhiên thuộc trường đó
    w = database.get_random_words_by_fields(state.get("learned", []), target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Bạn đã học hết từ trong kho **{target_fields}**!\nHãy chọn kho khác (VD: 'Chọn HSK1') hoặc Reset.")
        return
    
    word = w[0]
    state["session"].append(word)
    state["learned"].append(word['Hán tự'])
    state["current_word"] = word['Hán tự']
    
    # Gọi AI tạo câu ví dụ và bóc tách từ mới
    ai_data = ai_service.generate_sentence_with_annotation(word)
    
    # Tạo nội dung tin nhắn
    total = database.get_total_words_by_fields(target_fields)
    
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/6 | Kho: {','.join(target_fields)})\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 Nghĩa: {word['Nghĩa']}\n"
           f"🏷️ Cấp độ: {word['Field']}\n"
           f"──────────────\n"
           f"💡 **Ví dụ:**\n"
           f"{ai_data['sentence_han']}\n"
           f"({ai_data['sentence_pinyin']})\n"
           f"👉 {ai_data['sentence_viet']}\n")

    # Nếu AI phát hiện từ lạ trong câu ví dụ -> Hiển thị thêm
    if ai_data.get('new_words'):
        msg += "\n📝 **Từ vựng bổ sung trong câu:**\n"
        for nw in ai_data['new_words']:
            msg += f"- {nw['han']} ({nw['pinyin']}): {nw['viet']}\n"

    msg += f"\n👉 Gõ lại từ **{word['Hán tự']}** để học."
    
    fb_service.send_text(uid, msg)
    
    # Gửi Audio
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    # Gửi Audio câu ví dụ luôn cho xịn
    threading.Thread(target=lambda: (time.sleep(2), fb_service.send_audio(uid, ai_data['sentence_han']))).start()
    
    state["waiting"] = True
    state["next_time"] = 0
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    if state["waiting"]:
        cur = state.get("current_word","")
        if (cur in text) or (text.lower() in ["hiểu","ok","tiếp"]):
            state["next_time"] = common.get_ts() + 540 # 9 phút
            state["waiting"] = False
            fb_service.send_text(uid, "✅ Đã thuộc. Hẹn 9p nữa.")
            database.save_user_state(uid, state, cache)
        else:
            fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** nhé.")
