import threading
import time
from services import ai_service, fb_service
from logic import common, resources
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    # --- LOGIC MỚI: KIỂM TRA CHẾ ĐỘ HỌC CUSTOM ---
    custom_cfg = state.get("custom_learn", {"active": False})
    
    word_data = None
    
    # 1. Nếu đang học Custom List
    if custom_cfg.get("active"):
        queue = custom_cfg.get("queue", [])
        if not queue:
            fb_service.send_text(uid, "🎉 **CHÚC MỪNG!**\nBạn đã học hết kho từ tự chọn này.", buttons=["Menu", "Tạo kho"])
            state["mode"] = "IDLE"
            state["custom_learn"]["active"] = False # Tắt chế độ
            database.save_user_state(uid, state, cache)
            return
            
        # Lấy ID đầu tiên trong hàng đợi
        next_id = queue.pop(0) 
        # Cập nhật lại queue
        state["custom_learn"]["queue"] = queue
        
        # Fetch thông tin từ
        w_list = database.get_words_by_ids([next_id])
        if w_list:
            word_data = w_list[0]
    
    # 2. Nếu học bình thường (Random theo Field)
    else:
        target_fields = state.get("fields", ["HSK1"])
        exclude_list = state.get("learned", []) + [x['Hán tự'] for x in state.get('session', [])]
        w = database.get_random_words_by_fields(exclude_list, target_fields, 1)
        if w: word_data = w[0]
        else:
             # Hết từ
             pass

    # --- XỬ LÝ HIỂN THỊ ---
    if not word_data:
        fb_service.send_text(uid, "🎉 Bạn đã học hết từ vựng trong kho này!", buttons=["Menu", "Reset"])
        return
    
    state["session"].append(word_data)
    state["current_word"] = word_data['Hán tự']
    state["repetition_count"] = 0 
    
    # (Phần hiển thị giữ nguyên như cũ)
    learned_count = len(state.get("learned", []))
    total_words = "Custom" if custom_cfg.get("active") else database.get_total_words_by_fields(state.get("fields", []))
    
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/12)\n"
           f"📈 **Kho: {total_words}**\n"
           f"──────────────\n"
           f"🇨🇳 **{word_data['Hán tự']}** ({word_data['Pinyin']})\n"
           f"🇻🇳 {word_data['Nghĩa']}\n"
           f"🏷️ {word_data['Field']}\n"
           f"──────────────\n"
           f"✍️ **YÊU CẦU:** Gõ lại từ **{word_data['Hán tự']}** 5 lần để nhớ mặt chữ!")
    
    fb_service.send_text(uid, msg)
    threading.Thread(target=fb_service.send_audio, args=(uid, word_data['Hán tự'])).start()
    
    state["waiting"] = True
    state["mode"] = "AUTO"
    database.save_user_state(uid, state, cache)

# (Hàm handle_auto_reply giữ nguyên)
def handle_auto_reply(uid, text, state, cache):
    # ... (Giữ nguyên code cũ của bạn)
    # Lưu ý: Nhớ copy lại toàn bộ hàm handle_auto_reply vào đây nếu bạn overwrite file
    pass
