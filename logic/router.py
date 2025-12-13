from logic import common, learning, quiz, pause
from services import ai_service, fb_service
import database

# Danh sách lệnh
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục"]
# Lệnh mới
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    mode = state.get("mode", "IDLE")

    # 1. LỆNH XEM DANH SÁCH (MỚI)
    if msg in CMD_LIST:
        stats = database.get_all_fields_stats()
        if not stats:
            fb_service.send_text(uid, "📭 Kho từ vựng đang trống.")
            return
        
        reply = "📚 **KHO TỪ VỰNG HIỆN CÓ:**\n"
        reply += "──────────────────\n"
        total_all = 0
        for field, count in stats:
            reply += f"🔹 **{field}**: {count} từ\n"
            total_all += count
        reply += "──────────────────\n"
        reply += f"∑ **Tổng cộng**: {total_all} từ\n\n"
        reply += "👉 Gõ **'Chọn [Tên]'** để học (VD: Chọn HSK1)\n"
        reply += "👉 Gõ **'Chọn Tất cả'** để học toàn bộ."
        
        fb_service.send_text(uid, reply)
        return

    # 2. Xử lý Chọn trường (Đã nâng cấp cho "Tất cả")
    if msg.startswith("chọn") or msg.startswith("select"):
        # Lấy phần sau lệnh chọn
        arg = msg.replace("chọn", "").replace("select", "").strip().upper()
        
        # Xử lý chọn TẤT CẢ
        if arg in ["ALL", "TẤT CẢ", "HẾT", "TOÀN BỘ"]:
            stats = database.get_all_fields_stats()
            # Lấy danh sách tên tất cả các trường
            all_fields = [row[0] for row in stats]
            
            if not all_fields:
                fb_service.send_text(uid, "⚠️ Kho dữ liệu trống.")
                return

            state["fields"] = all_fields
            state["learned"] = []
            state["session"] = []
            state["mode"] = "IDLE"
            database.save_user_state(uid, state, cache)
            
            fb_service.send_text(uid, f"✅ Đã chọn **TẤT CẢ ({len(all_fields)} kho)**.\nTổng cộng: {sum(r[1] for r in stats)} từ.\n\nGõ 'Bắt đầu' để học ngay!")
            return

        # Xử lý chọn LẺ (VD: HSK1, HSK2)
        requested_fields = arg.replace(",", " ").split()
        if not requested_fields:
            fb_service.send_text(uid, "⚠️ Hãy ghi tên trường. VD: **Chọn HSK1**")
            return
            
        state["fields"] = requested_fields
        state["learned"] = []
        state["session"] = []
        state["mode"] = "IDLE"
        
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, f"✅ Đã chọn: **{', '.join(requested_fields)}**.\nGõ 'Bắt đầu' để học.")
        return

    # 3. Pause/Resume
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    # 4. Lệnh cơ bản
    if msg in CMD_START:
        state["mode"] = "AUTO"
        state["session"] = []
        learning.send_next_word(uid, state, cache)
        return

    if msg in CMD_RESET:
        current_fields = state.get("fields", ["HSK1"])
        new_s = {
            "user_id": uid, "mode": "IDLE", 
            "learned": [], "session": [], 
            "next_time": 0, "waiting": False, 
            "fields": current_fields,
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
        }
        database.save_user_state(uid, new_s, cache)
        fb_service.send_text(uid, "🔄 Đã Reset dữ liệu học.")
        return

    if msg == "menu":
        fb_service.send_text(uid, "📜 **MENU**\n- **Danh sách**: Xem các kho từ\n- **Chọn [Tên]**: Chọn kho\n- **Bắt đầu**: Vào học\n- **Nghỉ**: Tạm dừng\n- **Reset**: Xóa data")
        return

    # 5. State Machine & AI
    if mode == "QUIZ": quiz.handle_answer(uid, text, state, cache); return
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return

    fb_service.send_text(uid, ai_service.chat_reply(text))
