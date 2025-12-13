from logic import common, add_word, learning, quiz
from services import ai_service, fb_service
import database

# Danh sách từ khóa chào hỏi (Xử lý bằng Python cho nhanh)
GREETINGS = ["hi", "hello", "chào", "xin chào", "hi bot", "alo"]

# Danh sách lệnh Menu
CMD_MENU = ["menu", "hướng dẫn", "help", "lệnh"]
CMD_START = ["bắt đầu", "start", "học", "tiếp tục"]
CMD_ADD = ["thêm từ", "thêm", "add"]
CMD_RESET = ["reset", "học lại", "xóa data"]

def process_message(uid, text, cache):
    # 1. KIỂM TRA GIỜ NGỦ (Ưu tiên số 1)
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h). Mai quay lại nhé!")
        return

    # Chuẩn hóa văn bản: Chữ thường + xóa khoảng trắng thừa
    msg = text.lower().strip()
    
    # Lấy trạng thái User từ DB
    state = database.get_user_state(uid, cache)
    current_mode = state.get("mode", "IDLE")

    # ====================================================
    # PHẦN 1: CÁC LỆNH TOÀN CỤC (GLOBAL COMMANDS)
    # Python chặn bắt ngay tại đây, không cho xuống AI
    # ====================================================

    # Lệnh: MENU / HƯỚNG DẪN
    if msg in CMD_MENU:
        menu_text = (
            "📜 **DANH SÁCH LỆNH:**\n"
            "------------------\n"
            "▶️ **Bắt đầu**: Để vào học từ vựng\n"
            "➕ **Thêm từ**: Để thêm từ mới vào kho\n"
            "🔄 **Reset**: Xóa dữ liệu học lại từ đầu\n"
            "❓ **Help/Menu**: Xem bảng này"
        )
        fb_service.send_text(uid, menu_text)
        return

    # Lệnh: THÊM TỪ (Chỉ nhận khi đang rảnh hoặc đang học)
    if msg in CMD_ADD:
        state["mode"] = "ADD_1"
        fb_service.send_text(uid, "📝 Nhập **Hán tự** bạn muốn thêm:")
        database.save_user_state(uid, state, cache)
        return

    # Lệnh: BẮT ĐẦU
    if msg in CMD_START:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    # Lệnh: RESET
    if msg in CMD_RESET:
        # Reset về trắng tinh
        new_state = {
            "user_id": uid, 
            "mode": "IDLE", 
            "learned": [], 
            "session": [], 
            "next_time": 0, 
            "waiting": False, 
            "temp_word": None, 
            "last_greet": "", 
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
        }
        database.save_user_state(uid, new_state, cache)
        fb_service.send_text(uid, "🔄 Đã xóa dữ liệu. Gõ 'Bắt đầu' để học lại.")
        return

    # Xử lý chào hỏi cơ bản (Không cần AI)
    if msg in GREETINGS:
        fb_service.send_text(uid, "👋 Chào bạn! Gõ 'Menu' để xem hướng dẫn nhé.")
        return

    # ====================================================
    # PHẦN 2: XỬ LÝ THEO TRẠNG THÁI (STATE MACHINE)
    # Kiểm tra xem User đang lở dở việc gì không
    # ====================================================

    # Đang trong quy trình Thêm từ
    if current_mode.startswith("ADD_"):
        add_word.handle(uid, text, state, cache)
        return

    # Đang làm bài kiểm tra (Quiz)
    if current_mode == "QUIZ":
        quiz.handle_answer(uid, text, state, cache)
        return

    # Đang học từ (Auto Reply)
    if current_mode == "AUTO":
        # Nếu đang chờ user gõ lại từ hoặc xác nhận "OK"
        if state.get("waiting"):
            learning.handle_auto_reply(uid, text, state, cache)
            return
        # Nếu không waiting thì rơi xuống phần AI bên dưới để chat phiếm

    # ====================================================
    # PHẦN 3: AI CHAT (FALLBACK)
    # Nếu không trúng bất kỳ lệnh nào ở trên -> Mới gọi AI
    # ====================================================
    
    # Gọi AI Service
    ai_reply = ai_service.chat_reply(text)
    fb_service.send_text(uid, ai_reply)
