from services import fb_service
from logic import guide
import database

def handle_reset(uid, state, cache):
    """Xử lý lệnh Reset toàn bộ"""
    # Tạo state mới nhưng giữ lại cấu hình field đang chọn để đỡ phải chọn lại
    s_new = {
        "user_id": uid, 
        "mode": "IDLE", 
        "learned": [], 
        "session": [], 
        "fields": state.get("fields", ["HSK1"]), 
        "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0},
        "custom_learn": {"active": False, "queue": []}
    }
    database.save_user_state(uid, s_new, cache)
    fb_service.send_text(uid, "🔄 Đã Reset toàn bộ tiến độ về 0.", buttons=["Bắt đầu"])

def handle_menu_guide(uid, text, state, cache):
    """Xử lý lệnh Menu / Help"""
    guide_content = guide.get_full_guide() 
    fb_service.send_text(uid, guide_content, buttons=["Bắt đầu", "Danh sách", "Tạo kho"])
