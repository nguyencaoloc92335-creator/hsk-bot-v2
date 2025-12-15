import threading
import time
from services import ai_service, fb_service
from logic import common
import database

def send_next_word(uid, state, cache):
    if common.is_sleep_mode(): return
    
    target_fields = state.get("fields", ["HSK1"])
    total_words = database.get_total_words_by_fields(target_fields)
    learned_count = len(state.get("learned", [])) + len(state.get("session", []))
    
    current_session_hanzi = [x['Hán tự'] for x in state['session']]
    exclude_list = state.get("learned", []) + current_session_hanzi
    
    w = database.get_random_words_by_fields(exclude_list, target_fields, 1)
    
    if not w: 
        fb_service.send_text(uid, f"🎉 Chúc mừng! Bạn đã học hết {learned_count}/{total_words} từ vựng trong kho này!", buttons=["Menu", "Reset"])
        return
    
    word = w[0]
    state["session"].append(word)
    state["current_word"] = word['Hán tự']
    
    # --- LOGIC MỚI: Đặt lại bộ đếm số lần nhắc lại ---
    state["repetition_count"] = 0 
    # ------------------------------------------------
    
    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/12)\n"
           f"📈 **Tiến độ: {learned_count + 1}/{total_words}**\n"
           f"──────────────\n"
           f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
           f"🇻🇳 {word['Nghĩa']}\n"
           f"🏷️ {word['Field']}\n"
           f"──────────────\n"
           f"✍️ **YÊU CẦU:** Gõ lại từ **{word['Hán tự']}** 5 lần để nhớ mặt chữ!")
    
    # Không dùng nút bấm để bắt buộc gõ
    fb_service.send_text(uid, msg)
    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()
    
    state["waiting"] = True
    state["mode"] = "AUTO"
    database.save_user_state(uid, state, cache)

def handle_auto_reply(uid, text, state, cache):
    cur = state.get("current_word", "")
    msg = text.lower().strip()
    
    # Kiểm tra đáp án thông minh
    is_match = common.check_answer_smart(msg, cur)
    
    # Lấy số lần đã gõ (mặc định là 0)
    current_count = state.get("repetition_count", 0)

    if is_match:
        # Tăng số lần đã gõ đúng
        current_count += 1
        state["repetition_count"] = current_count
        
        # --- KIỂM TRA ĐÃ ĐỦ 5 LẦN CHƯA ---
        if current_count < 5:
            remain = 5 - current_count
            fb_service.send_text(uid, f"✅ Chính xác! Hãy gõ lại **{remain}** lần nữa cho nhớ hẳn nhé.")
            database.save_user_state(uid, state, cache)
            return # Dừng hàm tại đây, không đi tiếp logic bên dưới
        # ---------------------------------

        # NẾU ĐÃ ĐỦ 5 LẦN -> Chạy tiếp logic cũ (Lưu từ, check mốc...)
        if cur not in state["learned"]:
            state["learned"].append(cur)
        
        count = len(state["session"])
        
        # 1. MỐC 12 TỪ
        if count >= 12:
            state["mode"] = "PRE_QUIZ"
            state["next_time"] = common.get_ts() + 540
            review_words = state["session"]
            review_msg = "\n".join([f"• {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in review_words])
            
            fb_service.send_text(uid, f"🛑 **HOÀN THÀNH 12 TỪ**\nTổng hợp:\n{review_msg}\n\n☕ Nghỉ 9 phút nhé!", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return

        # 2. MỐC 6 TỪ
        if count == 6:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540
            review_words = state["session"][0:6]
            review_msg = "\n".join([f"• {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in review_words])
            
            fb_service.send_text(uid, f"🌟 **CHẶNG 1 (6/12)**\n{review_msg}\n\n⏳ Nghỉ 9 phút.", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return

        # 3. CÁC MỐC CHẴN KHÁC
        if count % 2 == 0:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540
            words_2 = state["session"][-2:]
            review_msg = "\n".join([f"- {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in words_2])
            
            fb_service.send_text(uid, f"☕ **GIẢI LAO 9 PHÚT**\n{review_msg}", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return
            
        # 4. CÁC MỐC LẺ
        fb_service.send_text(uid, "💪 Tuyệt vời! Bạn đã thuộc từ này. Học từ tiếp theo nhé:")
        time.sleep(1)
        send_next_word(uid, state, cache)
        
    else:
        # Nếu gõ sai hoặc gõ lệnh linh tinh khi đang học
        # Cho phép lệnh "skip" hoặc "tiếp" nếu user thực sự muốn bỏ qua (tùy chọn)
        if msg in ["tiếp", "next", "skip"]:
             fb_service.send_text(uid, f"⚠️ Bạn cần gõ đủ 5 lần để nhớ. Đừng bỏ cuộc! Gõ lại **{cur}** nào.")
        else:
             fb_service.send_text(uid, f"⚠️ Chưa đúng. Hãy gõ lại từ **{cur}** nhé.")
