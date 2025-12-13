from logic import common, learning, quiz, pause
from services import ai_service, fb_service
import database

# Danh sách lệnh (Giữ nguyên như cũ)
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    mode = state.get("mode", "IDLE")

    # 1. CÁC LỆNH HỆ THỐNG (Ưu tiên)
    if msg in ["menu", "help", "hướng dẫn"]:
        fb_service.send_text(uid, "📘 **HƯỚNG DẪN MỚI**\nBot sẽ dạy mỗi lần 2 từ, tổng cộng 12 từ.\nSau mỗi 6 từ sẽ ôn tập.\nHết 12 từ sẽ nghỉ 9 phút rồi kiểm tra.")
        return

    # Lệnh Pause/Resume
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    # Lệnh Danh sách / Chọn trường (Code cũ - giữ nguyên hoặc copy từ bài trước)
    if msg in CMD_LIST:
        stats = database.get_all_fields_stats()
        # ... (Phần hiển thị danh sách như bài trước) ...
        reply = "📚 **KHO TỪ:**\n" + "\n".join([f"- {f}: {c}" for f,c in stats])
        fb_service.send_text(uid, reply); return

    if msg.startswith("chọn"):
        # ... (Logic chọn trường như bài trước) ...
        arg = msg.replace("chọn", "").strip().upper().replace(",", " ").split()
        if arg: state["fields"]=arg; state["session"]=[]; state["mode"]="IDLE"; database.save_user_state(uid, state, cache); fb_service.send_text(uid, "✅ Đã chọn kho."); return

    if msg in CMD_START:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    if msg in CMD_RESET:
        # Reset
        s_new = {"user_id": uid, "mode": "IDLE", "learned": [], "session": [], "fields": state.get("fields", ["HSK1"]), "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}}
        database.save_user_state(uid, s_new, cache)
        fb_service.send_text(uid, "🔄 Đã Reset.")
        return

    # 2. XỬ LÝ THEO TRẠNG THÁI (STATE MACHINE)
    
    # Đang học từ (Gõ lại từ)
    if mode == "AUTO" and state.get("waiting"):
        learning.handle_auto_reply(uid, text, state, cache)
        return

    # Đang xem danh sách ôn tập (Review List)
    if mode == "REVIEWING":
        learning.handle_review_confirm(uid, text, state, cache)
        return
        
    # Đang chờ 9 phút (Pre-Quiz) mà user nhắn tin
    if mode == "PRE_QUIZ":
        remaining = state.get("next_time", 0) - common.get_ts()
        if remaining > 0:
            minutes = int(remaining / 60)
            fb_service.send_text(uid, f"⏳ Vẫn đang giờ giải lao.\nCòn khoảng {minutes} phút nữa sẽ bắt đầu kiểm tra nha.")
        else:
            # Nếu lỡ timer trôi qua mà cronjob chưa quét, cho vào thi luôn
            from logic import quiz
            quiz.start_quiz_level(uid, state, cache, 1)
        return

    # Đang thi Quiz
    if mode == "QUIZ":
        quiz.handle_answer(uid, text, state, cache)
        return

    # Chat vui vẻ
    fb_service.send_text(uid, ai_service.chat_reply(text))
