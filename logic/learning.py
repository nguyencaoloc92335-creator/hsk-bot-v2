import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    # Lấy fields người dùng chọn
    target_fields = state.get("fields", ["HSK1"])
    
    # Lấy 1 từ mới từ DB (trừ những từ đã học trong session này)
    current_session_hanzi = [x['Hán tự'] for x in state['session']]
    exclude_list = state.get("learned", []) + current_session_hanzi
    
    w = database.get_random_words_by_fields(exclude_list, target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Bạn đã học hết từ vựng trong kho này rồi!")
        return
    
    word = w[0]
    state["session"].append(word)
    state["current_word"] = word['Hán tự']
    
    # Tạo tin nhắn thẻ từ
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/12)\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"🏷️ {word['Field']}\n"
           f"──────────────\n"
           f"👉 Gõ lại từ **{word['Hán tự']}** để học.")
    
    fb_service.send_text(uid, msg)
    
    # Gửi Audio
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    
    state["waiting"] = True
    state["mode"] = "AUTO"
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    """Xử lý khi user gõ lại từ để học"""
    cur = state.get("current_word", "")
    msg = text.lower().strip()
    
    # Chấp nhận gõ đúng từ hoặc lệnh xác nhận
    if (cur in text) or (msg in ["hiểu", "ok", "tiếp", "next"]):
        # Lưu từ vào danh sách đã học lâu dài
        if cur not in state["learned"]:
            state["learned"].append(cur)
        
        count = len(state["session"])
        
        # ========================================================
        # LOGIC NGHỈ NGƠI & TỔNG HỢP (Updated)
        # ========================================================
        
        # 1. MỐC 12 TỪ: Tổng hợp + Nghỉ chờ Thi (PRE_QUIZ)
        if count >= 12:
            state["mode"] = "PRE_QUIZ"
            state["next_time"] = common.get_ts() + 540 # 9 phút
            
            # Tổng hợp 6 từ cuối (7-12)
            review_words = state["session"][6:12]
            review_msg = "\n".join([f"• {w['Hán tự']}: {w['Nghĩa']}" for w in review_words])
            
            fb_service.send_text(uid, f"🛑 **ĐỦ 12 TỪ**\nTổng hợp 6 từ cuối:\n{review_msg}\n\n☕ Nghỉ 9 phút rồi làm bài kiểm tra nhé!")
            database.save_user_state(uid, state, cache)
            return

        # 2. MỐC 6 TỪ: Tổng hợp đặc biệt + Nghỉ ngắn (SHORT_BREAK)
        if count == 6:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540 # 9 phút
            
            # Tổng hợp cả 6 từ đầu tiên (1-6)
            review_words = state["session"][0:6]
            review_msg = "\n".join([f"• {w['Hán tự']}: {w['Nghĩa']}" for w in review_words])
            
            fb_service.send_text(uid, f"🌟 **CHẶNG 1 HOÀN THÀNH** (6/12)\nDanh sách ôn tập:\n{review_msg}\n\n⏳ Bot sẽ gọi bạn dậy học tiếp sau 9 phút nữa.")
            database.save_user_state(uid, state, cache)
            return

        # 3. CÁC MỐC CHẴN KHÁC (2, 4, 8, 10): Tổng hợp nhỏ + Nghỉ ngắn (SHORT_BREAK)
        if count % 2 == 0:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540 # 9 phút
            
            # Chỉ nhắc lại 2 từ vừa học
            words_2 = state["session"][-2:]
            review_msg = "\n".join([f"- {w['Hán tự']}: {w['Nghĩa']}" for w in words_2])
            
            fb_service.send_text(uid, f"☕ **GIẢI LAO 9 PHÚT**\nĐã học xong 2 từ:\n{review_msg}\n\n⏳ Hết giờ Bot sẽ tự gọi bạn.")
            database.save_user_state(uid, state, cache)
            return
            
        # 4. CÁC MỐC LẺ (1, 3, 5...): Học tiếp ngay
        fb_service.send_text(uid, "✅ Chính xác! Từ tiếp theo:")
        time.sleep(1)
        send_next_word(uid, state, cache)
        
    else:
        fb_service.send_text(uid, f"⚠️ Gõ lại từ **{cur}** để nhớ mặt chữ nhé.")

# Lưu ý: Hàm send_review_list và handle_review_confirm cũ không còn dùng nữa,
# có thể xóa hoặc để đó cũng không ảnh hưởng.
