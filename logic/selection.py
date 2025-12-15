import time
from services import fb_service
import database

# Các trạng thái
STATE_ASK_SOURCE = "SELECT_ASK_SOURCE"
STATE_BROWSING = "SELECT_BROWSING"
STATE_NAMING = "SELECT_NAMING"
STATE_CONFIRM_SAVE = "SELECT_CONFIRM"

def start_creation_flow(uid, state, cache):
    """Bước 1: Hỏi người dùng muốn lấy từ nguồn nào"""
    stats = database.get_all_fields_stats()
    # Gợi ý nút bấm: Thêm nút "Tất cả" lên đầu
    buttons = ["Tất cả"] + [s[0].replace("_", " ") for s in stats][:2]
    
    msg = "📂 **TẠO KHO TỪ MỚI**\n\nBạn muốn lọc từ vựng từ nguồn nào?\n(Gõ tên nguồn, ví dụ: HSK1, Chuyên ngành, hoặc Tất cả...)"
    
    state["mode"] = STATE_ASK_SOURCE
    state["selection_data"] = {
        "source": "",
        "candidates": [],
        "idx": 0,
        "picked_ids": []
    }
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg, buttons=buttons)

def handle_source_selection(uid, text, state, cache):
    """Bước 2: Xử lý tên nguồn và tải từ"""
    source_name = text.strip()
    
    stats = database.get_all_fields_stats()
    real_fields = {s[0].lower().replace("_", " ").replace(" ", ""): s[0] for s in stats}
    
    user_input_clean = source_name.lower().replace("_", " ").replace(" ", "")
    
    words = []
    display_name = ""

    # TH1: Chọn Tất cả
    if user_input_clean in ["tấtcả", "all", "tatca", "tat ca"]:
        words = database.get_all_words_raw()
        display_name = "TẤT CẢ CÁC NGUỒN"
    
    # TH2: Chọn nguồn cụ thể
    else:
        selected_field = real_fields.get(user_input_clean)
        if not selected_field:
            fb_service.send_text(uid, f"⚠️ Không tìm thấy nguồn '**{source_name}**'.\nVui lòng chọn lại:", buttons=["Tất cả"] + list(real_fields.values())[:2])
            return
        words = database.get_all_words_by_field_raw(selected_field)
        display_name = selected_field

    if not words:
        fb_service.send_text(uid, "📭 Nguồn này trống rỗng.")
        return

    state["selection_data"]["source"] = display_name
    state["selection_data"]["candidates"] = words
    state["selection_data"]["idx"] = 0
    state["selection_data"]["picked_ids"] = []
    
    state["mode"] = STATE_BROWSING
    database.save_user_state(uid, state, cache)
    
    fb_service.send_text(uid, f"✅ Đã tải **{len(words)}** từ từ {display_name}.\nBắt đầu duyệt nhé! 👇")
    time.sleep(1)
    send_next_candidate(uid, state, cache)

def send_next_candidate(uid, state, cache):
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
    msg = text.lower().strip()
    data = state["selection_data"]
    
    if msg in ["kết thúc", "xong", "stop", "đủ rồi"]:
        finish_selection(uid, state, cache)
        return
    
    current_word = data["candidates"][data["idx"]]
    
    if msg in ["học", "có", "lấy", "ok"]:
        data["picked_ids"].append(current_word["id"])
    elif msg in ["bỏ qua", "không", "next", "skip"]:
        pass
    else:
        fb_service.send_text(uid, "Vui lòng bấm nút: Học, Bỏ qua hoặc Kết thúc.", buttons=["Học", "Bỏ qua", "Kết thúc"])
        return

    data["idx"] += 1
    state["selection_data"] = data
    database.save_user_state(uid, state, cache)
    send_next_candidate(uid, state, cache)

def finish_selection(uid, state, cache):
    count = len(state["selection_data"]["picked_ids"])
    if count == 0:
        fb_service.send_text(uid, "❌ Bạn chưa chọn từ nào cả. Đã hủy.", buttons=["Menu"])
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
    name = text.strip()
    state["selection_data"]["list_name"] = name
    
    msg = (f"📂 Tên kho: **{name}**\n\n"
           f"Bạn muốn **Lưu vĩnh viễn** kho này hay chỉ **Học ngay** (xong rồi xóa)?")
    
    state["mode"] = STATE_CONFIRM_SAVE
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg, buttons=["Lưu vĩnh viễn", "Học ngay"])

def handle_save_confirmation(uid, text, state, cache):
    msg = text.lower()
    picked_ids = state["selection_data"]["picked_ids"]
    name = state["selection_data"]["list_name"]
    
    state["custom_learn"] = {
        "active": True,
        "queue": picked_ids,
        "original_queue": picked_ids[:]
    }
    
    reply = ""
    if "lưu" in msg:
        if database.create_custom_list(uid, name, picked_ids):
            reply = f"💾 Đã lưu kho **{name}** thành công!\n"
        else:
            reply = "⚠️ Lưu thất bại (lỗi DB), nhưng vẫn sẽ cho bạn học ngay.\n"
    else:
        reply = "🗑️ Ok, sẽ học tạm thời (không lưu).\n"

    state["mode"] = "AUTO"
    state["session"] = []
    state["waiting"] = False
    del state["selection_data"]
    
    database.save_user_state(uid, state, cache)
    
    fb_service.send_text(uid, f"{reply}🚀 **BẮT ĐẦU HỌC KHO '{name}' NGAY!**")
    time.sleep(1)
    
    from logic import learning
    learning.send_next_word(uid, state, cache)
