from logic import common, add_word, learning, quiz, pause
from services import ai_service, fb_service
import database

# Danh sách lệnh
GREETINGS = ["hi", "hello", "chào", "xin chào", "hi bot", "alo"]
CMD_MENU = ["menu", "hướng dẫn", "help", "lệnh"]
CMD_START = ["bắt đầu", "start", "học", "tiếp tục"]
CMD_ADD = ["thêm từ", "thêm", "add"]
CMD_RESET = ["reset", "học lại", "xóa data"]

# Lệnh Nghỉ & Resume
CMD_PAUSE = ["nghỉ", "nghỉ ngơi", "break", "stop", "dừng", "bận", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp", "resume", "back", "quay lại", "ok", "có"]

def process_message(uid, text, cache):
    # 1. KIỂM TRA GIỜ NGỦ 0H-6H
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h). Mai quay lại nhé!")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    current_mode = state.get("mode", "IDLE")

    # ====================================================
    # PHẦN 1: XỬ LÝ NGHỈ & TIẾP TỤC (ƯU TIÊN CAO NHẤT)
    # ====================================================
    
    # Nếu user muốn quay lại học (Resume)
    if msg in CMD_RESUME:
        if current_mode == "PAUSED":
            pause.resume(uid, state, cache)
            return

    # Nếu user muốn Nghỉ (Pause)
    # Check xem câu có chứa từ khóa nghỉ và ngắn gọn (dưới 30 ký tự)
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 30:
        pause.handle_pause(uid, text, state, cache)
        return
        
    # Nếu đang PAUSED mà nhắn linh tinh -> Nhắc user
    if current_mode == "PAUSED":
        fb_service.send_text(uid, "⏸️ Bạn đang chế độ Tạm dừng.\nGõ **'Tiếp'** để học lại nhé.")
        return

    # ====================================================
    # PHẦN 2: CÁC LỆNH MENU / SYSTEM
    # ====================================================

    if msg in CMD_MENU:
        menu_text = (
            "📜 **DANH SÁCH LỆNH:**\n"
            "------------------\n"
            "▶️ **Bắt đầu**: Vào học\n"
            "⏸️ **Nghỉ [phút]**: Tạm dừng (VD: Nghỉ 15p)\n"
            "➕ **Thêm từ**: Thêm từ mới\n"
            "🔄 **Reset**: Xóa dữ liệu học lại\n"
        )
        fb_service.send_text(uid, menu_text)
        return

    if msg in CMD_ADD:
        state["mode"] = "ADD_1"
        fb_service.send_text(uid, "📝 Nhập **Hán tự** bạn muốn thêm:")
        database.save_user_state(uid, state, cache)
        return

    if msg in CMD_START:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    if msg in CMD_RESET:
        new_state = {
            "user_id": uid, "mode": "IDLE", "learned": [], "session": [], 
            "next_time": 0, "waiting": False, "temp_word": None, "last_greet": "", 
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
        }
        database.save_user_state(uid, new_state, cache)
        fb_service.send_text(uid, "🔄 Đã Reset. Gõ 'Bắt đầu' để học.")
        return

    if msg in GREETINGS:
        fb_service.send_text(uid, "👋 Chào bạn! Gõ 'Menu' hoặc 'Bắt đầu' nhé.")
        return

    # ====================================================
    # PHẦN 3: XỬ LÝ THEO TRẠNG THÁI (ADD, QUIZ, AUTO)
    # ====================================================

    if current_mode.startswith("ADD_"):
        add_word.handle(uid, text, state, cache)
        return

    if current_mode == "QUIZ":
        quiz.handle_answer(uid, text, state, cache)
        return

    if current_mode == "AUTO":
        if state.get("waiting"):
            learning.handle_auto_reply(uid, text, state, cache)
            return

    # ====================================================
    # PHẦN 4: AI CHAT (CUỐI CÙNG)
    # ====================================================
    
    ai_reply = ai_service.chat_reply(text)
    fb_service.send_text(uid, ai_reply)
