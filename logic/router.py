from logic import common, add_word, learning, quiz
from services import ai_service, fb_service
import database

def process_message(uid, text, cache):
    # 1. SLEEP MODE 0H-6H
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Hệ thống đang nghỉ (0h-6h). Mai học tiếp nhé!")
        return

    # Lấy trạng thái user
    state = database.get_user_state(uid, cache)
    msg = text.lower().strip()

    # 2. GLOBAL COMMANDS (Lệnh ưu tiên)
    if msg == "thêm từ":
        state["mode"] = "ADD_1"
        fb_service.send_text(uid, "📝 Nhập **Hán tự** muốn thêm:")
        database.save_user_state(uid, state, cache)
        return

    if msg in ["bắt đầu", "start"]:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    if msg in ["reset", "học lại"]:
        # Reset toàn bộ state
        state = {"user_id": uid, "mode": "IDLE", "learned": [], "session": [], "next_time": 0, "waiting": False, "temp_word": None, "last_greet": "", "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}}
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, "🔄 Đã Reset.")
        return

    # 3. ROUTING THEO MODE
    mode = state.get("mode", "IDLE")

    if mode.startswith("ADD_"):
        add_word.handle(uid, text, state, cache)
    elif mode == "QUIZ":
        quiz.handle_answer(uid, text, state, cache)
    elif mode == "AUTO":
        learning.handle_auto_reply(uid, text, state, cache)
    else:
        # IDLE: Chat tự do
        fb_service.send_text(uid, ai_service.chat_reply(text))