from logic import common, add_word, learning, quiz, pause # <--- Import thêm pause
from services import ai_service, fb_service
import database

# ... (Các list lệnh cũ giữ nguyên) ...
CMD_PAUSE = ["nghỉ", "nghỉ ngơi", "break", "stop", "dừng", "bận"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp", "resume", "back", "quay lại"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    current_mode = state.get("mode", "IDLE")

    # 1. LỆNH TOÀN CỤC (Ưu tiên cao nhất)
    
    # --- XỬ LÝ NGHỈ & TIẾP TỤC ---
    # Nếu user muốn nghỉ (kể cả khi đang nghỉ rồi mà nhắn lại để sửa giờ)
    # Kiểm tra xem câu có chứa từ khóa nghỉ không (dùng regex hoặc in list)
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20: 
        pause.handle_pause(uid, text, state, cache)
        return

    # Nếu user muốn quay lại
    if msg in CMD_RESUME or (current_mode == "PAUSED" and msg in ["ok", "có", "hoc", "học"]):
        pause.resume(uid, state, cache)
        return
    # -----------------------------

    # ... (Giữ nguyên các lệnh Menu, Start, Add, Reset cũ của bạn ở đây) ...
    # Copy lại đoạn code cũ vào đây
    # ...

    # 2. XỬ LÝ THEO STATE
    if current_mode == "PAUSED":
        # Nếu đang nghỉ mà user nhắn linh tinh (không phải lệnh Resume)
        # Thì bot nhắc nhẹ hoặc AI trả lời (tùy bạn). 
        # Ở đây cho AI trả lời cho đỡ chán, nhưng nhắc user là đang Pause.
        fb_service.send_text(uid, "⏸️ Bot đang chế độ Tạm dừng.\nGõ **'Tiếp'** để học lại.")
        return

    # ... (Các phần logic cũ: ADD, QUIZ, AUTO...) ...
    
    # Phần gọi AI cũ
    ai_reply = ai_service.chat_reply(text)
    fb_service.send_text(uid, ai_reply)
