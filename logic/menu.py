from services import fb_service
import database
from logic import common

def handle_show_stats(uid, state, cache):
    """Xử lý lệnh 'Danh sách' - Hiển thị các kho từ vựng"""
    # 1. Lấy thống kê các kho HSK/Chuyên ngành
    stats = database.get_all_fields_stats()
    
    # 2. (Tùy chọn) Có thể lấy thêm danh sách kho tự tạo (Custom List) nếu muốn
    # custom_lists = database.get_custom_lists_of_user(uid) ... (Chưa làm hàm này, để sau)

    if not stats: 
        fb_service.send_text(uid, "📭 Kho từ vựng đang trống.")
        return

    # Format nội dung
    msg_lines = ["📚 **THỐNG KÊ KHO TỪ VỰNG:**"]
    for field, count in stats:
        # Làm đẹp tên: Chuyên_ngành -> Chuyên ngành
        display_name = field.replace("_", " ")
        msg_lines.append(f"• **{display_name}**: {count} từ")
    
    msg_lines.append("\n👉 Gõ `Chọn [Tên]` để học (VD: Chọn HSK1).")
    
    # Gợi ý nút bấm dựa trên danh sách có sẵn
    buttons = [s[0].replace("_", " ") for s in stats][:3] # Lấy 3 cái đầu
    
    fb_service.send_text(uid, "\n".join(msg_lines), buttons=buttons)

def handle_select_source(uid, text, state, cache):
    """Xử lý lệnh 'Chọn ...' (VD: Chọn HSK1, Chọn Chuyên ngành)"""
    arg = text.lower().replace("chọn", "").strip()
    
    # Lấy danh sách field thực tế trong DB
    stats = database.get_all_fields_stats()
    # Map để chuẩn hóa: "chuyên ngành" -> "Chuyên_ngành"
    # Key là tên viết thường không dấu cách/gạch, Value là tên chuẩn trong DB
    real_fields = {s[0].lower().replace("_", " ").replace(" ", ""): s[0] for s in stats}
    
    # Xử lý input người dùng
    raw_input = arg.replace("_", " ").replace(" ", "")
    
    reply = ""
    target_fields = []

    # 1. Trường hợp chọn TẤT CẢ
    if raw_input in ["tấtcả", "all", "tatca"]:
        target_fields = [s[0] for s in stats]
        reply = "✅ Đã chọn **TẤT CẢ** các kho."
    
    # 2. Trường hợp chọn 1 kho cụ thể (Match thông minh)
    elif raw_input in real_fields:
        correct_field = real_fields[raw_input]
        target_fields = [correct_field]
        reply = f"✅ Đã chọn kho: **{correct_field}**."
        
    # 3. Trường hợp fallback (Chọn nhiều kho gõ tay: HSK1 HSK2)
    else:
        # Cố gắng tách chuỗi cũ
        parts = text.replace("chọn", "").upper().replace(",", " ").split()
        target_fields = parts # Cách này kém chính xác hơn nhưng giữ tương thích cũ
        reply = f"✅ Đã chọn: {', '.join(parts)}."

    # CẬP NHẬT STATE
    state["fields"] = target_fields
    
    # Quan trọng: Tắt chế độ học Custom (nếu đang bật) để quay về học kho thường
    state["custom_learn"]["active"] = False
    
    # Reset phiên học hiện tại để nạp từ mới từ kho mới
    # (Tùy chọn: Nếu muốn giữ 12 từ đang học dở thì bỏ dòng này)
    # state["session"] = [] 
    
    database.save_user_state(uid, state, cache)
    
    fb_service.send_text(uid, f"{reply}\nTiến độ học được tính riêng cho kho này.", buttons=["Bắt đầu", "Menu"])
