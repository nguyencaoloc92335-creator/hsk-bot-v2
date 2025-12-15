from services import fb_service
import database
from logic import common

def handle_show_stats(uid, state, cache):
    """Xử lý lệnh 'Danh sách'"""
    stats = database.get_all_fields_stats()

    if not stats: 
        fb_service.send_text(uid, "📭 Kho từ vựng đang trống.")
        return

    msg_lines = ["📚 **THỐNG KÊ KHO TỪ VỰNG:**"]
    for field, count in stats:
        display_name = field.replace("_", " ")
        msg_lines.append(f"• **{display_name}**: {count} từ")
    
    msg_lines.append("\n👉 Gõ `Chọn [Tên]` để học (VD: Chọn HSK1).")
    msg_lines.append("👉 Gõ `Chọn Tất cả` để học gộp toàn bộ.")
    
    # Gợi ý nút bấm
    buttons = ["Chọn Tất cả"] + [s[0].replace("_", " ") for s in stats][:2]
    
    fb_service.send_text(uid, "\n".join(msg_lines), buttons=buttons)

def handle_select_source(uid, text, state, cache):
    """Xử lý lệnh 'Chọn ...'"""
    # 1. Chuẩn hóa text đầu vào
    arg = text.lower().replace("chọn", "").strip()
    raw_input = arg.replace("_", " ").replace(" ", "")
    
    # 2. Lấy dữ liệu thực tế từ DB
    stats = database.get_all_fields_stats()
    real_fields = {s[0].lower().replace("_", " ").replace(" ", ""): s[0] for s in stats}
    
    reply = ""
    target_fields = []

    # --- LOGIC CHỌN TẤT CẢ (ĐƯỢC ƯU TIÊN) ---
    if raw_input in ["tấtcả", "all", "tatca", "tat ca"]:
        target_fields = [s[0] for s in stats] # Lấy danh sách toàn bộ field
        reply = "✅ Đã chọn **TẤT CẢ** các kho."
    
    # --- LOGIC CHỌN KHO CỤ THỂ ---
    elif raw_input in real_fields:
        correct_field = real_fields[raw_input]
        target_fields = [correct_field]
        reply = f"✅ Đã chọn kho: **{correct_field}**."
        
    # --- LOGIC FALLBACK (Chọn nhiều kho gõ tay) ---
    else:
        # Cố gắng tách chuỗi cũ (VD: HSK1 HSK2)
        parts = text.replace("chọn", "").upper().replace(",", " ").split()
        if parts:
            target_fields = parts 
            reply = f"✅ Đã chọn: {', '.join(parts)}."
        else:
            fb_service.send_text(uid, "⚠️ Tên kho không hợp lệ. Gõ 'Danh sách' để xem lại nhé.")
            return

    # 3. Cập nhật State
    state["fields"] = target_fields
    state["custom_learn"]["active"] = False # Quan trọng: Tắt chế độ Custom Learn
    
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, f"{reply}\nTiến độ học được tính riêng cho lựa chọn này.", buttons=["Bắt đầu", "Menu"])
