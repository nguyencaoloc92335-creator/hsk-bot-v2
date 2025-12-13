import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    # Lấy fields người dùng chọn
    target_fields = state.get("fields", ["HSK1"])
    
    # Lấy 1 từ mới từ DB (trừ những từ đã học trong session này)
    # Lưu ý: exclude_list phải bao gồm cả state['learned'] cũ và state['session'] hiện tại
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

def send_review_list(uid, state, cache, start_idx, end_idx):
    """Gửi danh sách ôn tập (Review List)"""
    words_to_review = state["session"][start_idx:end_idx]
    
    msg = "📝 **DANH SÁCH ÔN TẬP**\nBạn hãy đọc lướt qua các từ vừa học:\n"
    msg += "──────────────────\n"
    for w in words_to_review:
        msg += f"• {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}\n"
    msg += "──────────────────\n"
    
    if len(state["session"]) == 12:
        msg += "🛑 **Đã đủ 12 từ.**\nGõ **'OK'** để nghỉ giải lao 9 phút trước khi kiểm tra."
    else:
        msg += "👉 Gõ **'OK'** hoặc **'Tiếp'** để học 6 từ tiếp theo."
        
    fb_service.send_text(uid, msg)
    state["mode"] = "REVIEWING" # Chuyển sang chế độ xem lại
    state["waiting"] = False
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
        
        # LOGIC MỚI:
        # 1. Nếu đủ 6 từ -> Gửi Review List (1-6)
        if count == 6:
            fb_service.send_text(uid, "✅ Tốt lắm! Đã xong 6 từ đầu tiên.")
            send_review_list(uid, state, cache, 0, 6)
            return

        # 2. Nếu đủ 12 từ -> Gửi Review List (7-12)
        if count == 12:
            fb_service.send_text(uid, "✅ Tuyệt vời! Đã xong 6 từ tiếp theo.")
            send_review_list(uid, state, cache, 6, 12)
            return
            
        # 3. Nếu chưa đủ các mốc trên -> Gửi từ tiếp theo ngay lập tức (Gửi lần lượt)
        fb_service.send_text(uid, "✅ Đúng rồi! Từ tiếp theo nè:")
        time.sleep(1) # Nghỉ 1s cho đỡ spam
        send_next_word(uid, state, cache)
        
    else:
        fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** để nhớ mặt chữ nhé.")

def handle_review_confirm(uid, text, state, cache):
    """Xử lý khi user gõ OK ở màn hình Review List"""
    msg = text.lower().strip()
    if msg not in ["ok", "có", "tiếp", "tiếp tục", "xong"]:
        fb_service.send_text(uid, "👉 Gõ **'OK'** để tiếp tục.")
        return

    count = len(state["session"])
    
    # Nếu đang ở mốc 6 từ -> Học tiếp từ số 7
    if count == 6:
        fb_service.send_text(uid, "🚀 Vào học 6 từ tiếp theo nhé!")
        send_next_word(uid, state, cache)
        
    # Nếu đang ở mốc 12 từ -> Chuyển sang chế độ Chờ Kiểm Tra (PRE_QUIZ)
    elif count == 12:
        state["mode"] = "PRE_QUIZ"
        state["next_time"] = common.get_ts() + 540 # 9 phút (540 giây)
        
        fb_service.send_text(uid, "☕ **GIẢI LAO**\nBạn đã học đủ 12 từ. Hãy nghỉ ngơi, 9 phút nữa mình sẽ gửi bài kiểm tra nhé!")
        database.save_user_state(uid, state, cache)
