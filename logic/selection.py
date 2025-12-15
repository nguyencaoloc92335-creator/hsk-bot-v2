import time
from services import fb_service
import database

# Các trạng thái trong quy trình tạo kho
STATE_ASK_SOURCE = "SELECT_ASK_SOURCE"
STATE_BROWSING = "SELECT_BROWSING"
STATE_NAMING = "SELECT_NAMING"
STATE_CONFIRM_SAVE = "SELECT_CONFIRM"

def start_creation_flow(uid, state, cache):
    """Bước 1: Hỏi người dùng muốn lấy từ nguồn nào"""
    # Lấy danh sách các field hiện có để gợi ý
    stats = database.get_all_fields_stats()
    fields = [s[0] for s in stats]
    
    msg = "📂 **TẠO KHO TỪ MỚI**\n\nBạn muốn lọc từ vựng từ nguồn nào?\n(Gõ tên nguồn, ví dụ: HSK1, Chuyên_ngành...)"
    
    # Gợi ý nút bấm
    buttons = fields[:3] # Lấy 3 cái đầu làm nút
    
    state["mode"] = STATE_ASK_SOURCE
    # Reset biến tạm
    state["selection_data"] = {
        "source": "",
        "candidates": [], # Danh sách từ để duyệt
        "idx": 0,         # Vị trí đang duyệt
        "picked_ids": []  # Danh sách ID đã chọn
    }
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg, buttons=buttons)

def handle_source_selection(uid, text, state, cache):
    """Bước 2: Xử lý tên nguồn và tải từ"""
    # Chuẩn hóa tên nguồn (Fix lỗi Chuyên ngành)
    source_name = text.strip()
    # Nếu người dùng gõ "Chuyên ngành" (có dấu cách), ta tự sửa thành "Chuyên_ngành"
    # Hoặc có thể so sánh không phân biệt hoa thường/dấu cách với DB
    
    # Lấy danh sách field thực tế trong DB để so khớp
    stats = database.get_all_fields_stats()
    real_fields = {s[0].lower().replace("_", " ").replace(" ", ""): s[0] for s in stats}
    
    user_input_clean = source_name.lower().replace("_", " ").replace(" ", "")
    
    selected_field = real_fields.get(user_input_clean)
    
    if not selected_field:
        fb_service.send_text(uid, f"⚠️ Không tìm thấy nguồn '**{source_name}**'.\nVui lòng chọn lại:", buttons=list(real_fields.values())[:3])
        return

    # Tải từ từ DB
    words = database.get_all_words_by_field_raw(selected_field)
    if not words:
        fb_service.send_text(uid, "📭 Nguồn này trống rỗng. Chọn nguồn khác nhé.")
        return

    state["selection_data"]["source"] = selected_field
    state["selection_data"]["candidates"] = words
    state["selection_data"]["idx"] = 0
    state["selection_data"]["picked_ids"] = []
    
    state["mode"] = STATE_BROWSING
    database.save_user_state(uid, state, cache)
    
    fb_service.send_text(uid, f"✅ Đã tải **{len(words)}** từ từ {selected_field}.\nBắt đầu duyệt nhé! 👇")
    time.sleep(1)
    send_next_candidate(uid, state, cache)

def send_next_candidate(uid, state, cache):
    """Hiển thị từ tiếp theo để chọn"""
    data = state["selection_data"]
    idx = data["idx"]
    words = data["candidates"]
    
    if idx >= len(words):
        finish_selection(uid, state, cache)
        return

    word = words[idx]
    
    msg = (f"🔍 **DUYỆT TỪ ({idx + 1}/{len(words)})**\n"
           f"──────────────\n"
           f"🇨🇳 **{word['hanzi']}**\n"
           f"🇻🇳 {word['meaning']}\n"
           f"──────────────\n"
           f"👉 Bạn có muốn học từ này không?")
    
    fb_service.send_text(uid, msg, buttons=["Học", "Bỏ qua", "Kết thúc"])

def handle_browsing_decision(uid, text, state, cache):
    """Xử lý nút Học/Bỏ qua"""
    msg = text.lower().strip()
    data = state["selection_data"]
    
    if msg in ["kết thúc", "xong", "stop", "đủ rồi"]:
        finish_selection(uid, state, cache)
        return
    
    # Xử lý lựa chọn hiện tại
    current_word = data["candidates"][data["idx"]]
    
    if msg in ["học", "có", "lấy", "ok"]:
        data["picked_ids"].append(current_word["id"])
        # Feedback nhẹ (tùy chọn, để spam ít thì bỏ qua)
        # fb_service.send_text(uid, f"✅ Đã thêm: {current_word['hanzi']}")
    elif msg in ["bỏ qua", "không", "next", "skip"]:
        pass
    else:
        fb_service.send_text(uid, "Vui lòng bấm nút: Học, Bỏ qua hoặc Kết thúc.", buttons=["Học", "Bỏ qua", "Kết thúc"])
        return

    # Tăng index
    data["idx"] += 1
    state["selection_data"] = data
    database.save_user_state(uid, state, cache)
    
    # Gửi từ tiếp theo
    send_next_candidate(uid, state, cache)

def finish_selection(uid, state, cache):
    """Bước 3: Kết thúc duyệt, hỏi tên"""
    count = len(state["selection_data"]["picked_ids"])
    if count == 0:
        fb_service.send_text(uid, "❌ Bạn chưa chọn từ nào cả. Đã hủy tạo kho.", buttons=["Menu"])
        state["mode"] = "IDLE"
        database.save_user_state(uid, state, cache)
        return

    msg = (f"🎉 **ĐÃ CHỌN XONG!**\n"
           f"Bạn đã chọn được **{count}** từ.\n\n"
           f"✍️ Hãy nhập **Tên** cho kho từ này (VD: Bai_tap_1):")
    
    state["mode"] = STATE_NAMING
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg)

def handle_naming(uid, text, state, cache):
    """Bước 4: Lưu tên và hỏi chế độ lưu"""
    name = text.strip()
    state["selection_data"]["list_name"] = name
    
    msg = (f"📂 Tên kho: **{name}**\n\n"
           f"Bạn muốn **Lưu vĩnh viễn** kho này vào CSDL hay chỉ **Học ngay** (xong rồi xóa)?")
    
    state["mode"] = STATE_CONFIRM_SAVE
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg, buttons=["Lưu vĩnh viễn", "Học ngay"])

def handle_save_confirmation(uid, text, state, cache):
    """Bước 5: Xử lý Lưu/Học và kích hoạt chế độ học"""
    msg = text.lower()
    picked_ids = state["selection_data"]["picked_ids"]
    name = state["selection_data"]["list_name"]
    
    # Cấu hình chế độ học Custom
    state["custom_learn"] = {
        "active": True,
        "queue": picked_ids, # Hàng đợi chứa ID các từ cần học
        "original_queue": picked_ids[:] # Lưu bản gốc để reset nếu cần
    }
    
    reply = ""
    if "lưu" in msg:
        # Lưu vào DB
        if database.create_custom_list(uid, name, picked_ids):
            reply = f"💾 Đã lưu kho **{name}** thành công!\n"
        else:
            reply = "⚠️ Lưu thất bại (lỗi DB), nhưng vẫn sẽ cho bạn học ngay.\n"
            
    else:
        reply = "🗑️ Ok, sẽ học tạm thời (không lưu).\n"

    # Chuyển ngay sang chế độ học
    state["mode"] = "AUTO"
    state["session"] = [] # Clear session cũ
    state["waiting"] = False
    
    # Xóa dữ liệu tạm selection
    del state["selection_data"]
    
    database.save_user_state(uid, state, cache)
    
    fb_service.send_text(uid, f"{reply}🚀 **BẮT ĐẦU HỌC KHO '{name}' NGAY!**")
    time.sleep(1)
    
    # Gọi module learning để bắt đầu
    from logic import learning
    learning.send_next_word(uid, state, cache)
