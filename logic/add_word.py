from services import ai_service, fb_service
import database

def handle(uid, text, state, cache):
    msg = text.lower().strip()
    
    # Bước 1: User nhập từ
    if state["mode"] == "ADD_1":
        if msg in ["hủy","không"]: 
            state["mode"]="IDLE"
            fb_service.send_text(uid, "❌ Đã hủy.")
            database.save_user_state(uid, state, cache)
            return

        fb_service.send_text(uid, "⏳ Đang tra cứu...")
        data = ai_service.lookup_word(text)
        if data and data.get('pinyin'):
            state["temp_word"] = data
            state["mode"] = "ADD_2"
            fb_service.send_text(uid, f"📖 {data['hanzi']} - {data['pinyin']}\nNghĩa: {data['meaning']}\n\n❓ Thêm không? (OK/Không)")
        else: 
            fb_service.send_text(uid, "⚠️ Lỗi AI. Nhập lại hoặc Hủy.")
        database.save_user_state(uid, state, cache)
        return

    # Bước 2: Xác nhận
    if state["mode"] == "ADD_2":
        if msg in ["ok","có","lưu"]:
            d = state.get("temp_word")
            if d and database.add_word(d['hanzi'], d['pinyin'], d['meaning']): 
                fb_service.send_text(uid, f"✅ Đã thêm {d['hanzi']}")
            else: 
                fb_service.send_text(uid, "⚠️ Từ đã tồn tại.")
        else: 
            fb_service.send_text(uid, "❌ Đã hủy.")
        
        state["mode"]="IDLE"
        state["temp_word"]=None
        database.save_user_state(uid, state, cache)
        return