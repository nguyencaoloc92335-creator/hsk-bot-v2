from logic import common, learning, quiz, pause
from services import ai_service, fb_service
import database

# Danh sách lệnh
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục"]
# Lệnh chọn trường
CMD_SELECT = ["chọn", "học trường", "select"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    mode = state.get("mode", "IDLE")

    # 1. Xử lý Chọn trường (VD: "Chọn HSK1", "Chọn HSK1, HSK2")
    if msg.startswith("chọn") or msg.startswith("select"):
        # Lấy phần sau chữ chọn. VD: "HSK1, HSK2"
        requested_fields = msg.replace("chọn", "").replace("select", "").upper().replace(",", " ").split()
        
        if not requested_fields:
            fb_service.send_text(uid, "⚠️ Hãy ghi tên trường. VD: **Chọn HSK1** hoặc **Chọn HSK1 HSK2**")
            return
            
        # Lưu vào state
        state["fields"] = requested_fields
        state["learned"] = [] # Reset từ đã học khi đổi trường để tránh lỗi
        state["session"] = []
        state["mode"] = "IDLE"
        
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, f"✅ Đã chọn kho: **{', '.join(requested_fields)}**.\nGõ 'Bắt đầu' để học.")
        return

    # 2. Xử lý Pause/Resume
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    # 3. Lệnh cơ bản
    if msg in CMD_START:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    if msg in CMD_RESET:
        # Reset nhưng giữ lại fields đang chọn
        current_fields = state.get("fields", ["HSK2"])
        new_s = {
            "user_id": uid, "mode": "IDLE", 
            "learned": [], "session": [], 
            "next_time": 0, "waiting": False, 
            "fields": current_fields, # Giữ nguyên lựa chọn
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
        }
        database.save_user_state(uid, new_s, cache)
        fb_service.send_text(uid, "🔄 Đã Reset dữ liệu học.")
        return

    if msg == "menu":
        fb_service.send_text(uid, "📜 **MENU**\n- **Chọn HSK1**: Chọn kho học\n- **Bắt đầu**: Vào học\n- **Nghỉ**: Tạm dừng\n- **Reset**: Xóa data cá nhân")
        return

    # 4. State Machine
    if mode == "QUIZ": quiz.handle_answer(uid, text, state, cache); return
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return

    # 5. AI Chat
    fb_service.send_text(uid, ai_service.chat_reply(text))
