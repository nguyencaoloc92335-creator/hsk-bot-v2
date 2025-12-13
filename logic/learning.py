import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    # Lấy fields người dùng chọn
    target_fields = state.get("fields", ["HSK1"])
    
    # Lấy 1 từ mới từ DB
    current_session_hanzi = [x['Hán tự'] for x in state['session']]
    exclude_list = state.get("learned", []) + current_session_hanzi
    
    w = database.get_random_words_by_fields(exclude_list, target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Bạn đã học hết từ vựng trong kho này rồi!")
        return
    
    word = w[0]
    state["session"].append(word)
    state["current_word"] = word['Hán tự']
    
    # Tạo tin nhắn thẻ từ
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/12)\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"🏷️ {word['Field']}\n"
           f"──────────────\n"
           f"👉 Gõ lại từ **{word['Hán tự']}** để học.")
    
    fb_service.send_text(uid, msg)
    
    # Gửi Audio
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    
    state["waiting"] = True
    state["mode"] = "AUTO"
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    """Xử lý khi user gõ lại từ để học"""
    cur = state.get("current_word", "")
    msg = text.lower().strip()
    
    # Chấp nhận gõ đúng từ hoặc lệnh xác nhận
    if (cur in text) or (msg in ["hiểu", "ok", "tiếp", "next"]):
        # Lưu từ vào danh sách đã học lâu dài
        if cur not in state["learned"]:
            state["learned"].append(cur)
        
        count = len(state["session"])
        
        # LOGIC MỚI: Cứ 2 từ nghỉ 9 phút, đủ 12 từ thì nghỉ chờ thi
        
        # 1. Nếu đã đủ 12 từ -> Chuyển sang chế độ Chờ Kiểm Tra (PRE_QUIZ)
        if count >= 12:
            state["mode"] = "PRE_QUIZ"
            state["next_time"] = common.get_ts() + 540 # 9 phút
            fb_service.send_text(uid, "🛑 **ĐỦ 12 TỪ**\nBạn hãy nghỉ ngơi 9 phút để não bộ ghi nhớ.\nSau đó chúng ta sẽ làm bài kiểm tra tổng kết nhé!")
            database.save_user_state(uid, state, cache)
            return

        # 2. Nếu là bội số của 2 (2, 4, 6, 8, 10) -> Nghỉ ngắn (SHORT_BREAK)
        if count % 2 == 0:
            state["mode"] = "SHORT_BREAK" # <--- Trạng thái mới
            state["next_time"] = common.get_ts() + 540 # 9 phút (540 giây)
            
            # Gửi tin nhắn tổng kết 2 từ vừa học
            words_2 = state["session"][-2:]
            review_msg = "\n".join([f"- {w['Hán tự']}: {w['Nghĩa']}" for w in words_2])
            
            fb_service.send_text(uid, f"☕ **GIẢI LAO 9 PHÚT**\nĐã học xong 2 từ:\n{review_msg}\n\n⏳ Bot sẽ tự gọi bạn dậy học tiếp sau 9 phút nữa.")
            database.save_user_state(uid, state, cache)
            return
            
        # 3. Nếu chưa rơi vào mốc nghỉ -> Gửi từ tiếp theo
        fb_service.send_text(uid, "✅ Chính xác! Từ tiếp theo:")
        time.sleep(1)
        send_next_word(uid, state, cache)
        
    else:
        fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** để nhớ mặt chữ nhé.")

# Các hàm khác như send_review_list, handle_review_confirm có thể giữ lại hoặc bỏ tùy bạn, 
# nhưng với logic trên thì chúng không còn được gọi nữa.
