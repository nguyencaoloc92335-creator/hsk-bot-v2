import threading
import time
from services import ai_service, fb_service
from logic import common, resources
import database

def send_next_word(uid, state, cache):
    # [ĐÃ SỬA] Xóa dòng kiểm tra is_sleep_mode() để tránh lỗi crash
    # if common.is_sleep_mode(): return 
    
    # --- LOGIC MỚI: KIỂM TRA CHẾ ĐỘ HỌC CUSTOM ---
    custom_cfg = state.get("custom_learn", {"active": False})
    
    word_data = None
    
    # 1. Nếu đang học Custom List (Kho tự tạo)
    if custom_cfg.get("active"):
        queue = custom_cfg.get("queue", [])
        if not queue:
            fb_service.send_text(uid, "🎉 **CHÚC MỪNG!**\nBạn đã học hết kho từ tự chọn này.", buttons=["Menu", "Tạo kho"])
            state["mode"] = "IDLE"
            state["custom_learn"]["active"] = False 
            database.save_user_state(uid, state, cache)
            return
            
        next_id = queue.pop(0) 
        state["custom_learn"]["queue"] = queue
        
        w_list = database.get_words_by_ids([next_id])
        if w_list:
            word_data = w_list[0]
    
    # 2. Nếu học bình thường (Random theo Field đã chọn)
    else:
        target_fields = state.get("fields", ["HSK1"])
        
        # Nếu target_fields rỗng (trường hợp lỗi), gán mặc định
        if not target_fields: target_fields = ["HSK1"]

        exclude_list = state.get("learned", []) + [x['Hán tự'] for x in state.get('session', [])]
        w = database.get_random_words_by_fields(exclude_list, target_fields, 1)
        if w: word_data = w[0]

    # --- XỬ LÝ HIỂN THỊ ---
    if not word_data:
        fb_service.send_text(uid, "🎉 Bạn đã học hết từ vựng trong kho này!", buttons=["Menu", "Reset"])
        return
    
    state["session"].append(word_data)
    state["current_word"] = word_data['Hán tự']
    state["repetition_count"] = 0 
    
    # --- HIỂN THỊ TIẾN ĐỘ ---
    if custom_cfg.get("active"):
        # Với Custom List: Hiển thị số còn lại
        progress_str = f"Còn {len(custom_cfg['queue']) + 1} từ"
    else:
        # Với kho thường: Tính chính xác số đã học TRONG KHO NÀY
        target_fields = state.get("fields", ["HSK1"])
        if not target_fields: target_fields = ["HSK1"]
        
        total_words = database.get_total_words_by_fields(target_fields)
        
        # Đếm số từ đã học thuộc kho này
        learned_in_field = database.get_count_learned_in_fields(state.get("learned", []), target_fields)
        # Cộng thêm số từ đang học trong session hiện tại
        current_session_count = len(state.get("session", []))
        
        progress_str = f"{learned_in_field + current_session_count}/{total_words}"

    msg = (f"🔔 **TỪ MỚI** ({len(state['session'])}/12)\n"
           f"📈 **Tiến độ: {progress_str}**\n"
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

def handle_auto_reply(uid, text, state, cache):
    cur = state.get("current_word", "")
    msg = text.lower().strip()
    
    is_match = common.check_answer_smart(msg, cur)
    current_count = state.get("repetition_count", 0)

    if is_match:
        current_count += 1
        state["repetition_count"] = current_count
        
        if current_count < 5:
            remain = 5 - current_count
            fb_service.send_text(uid, f"✅ Chính xác! Hãy gõ lại **{remain}** lần nữa cho nhớ hẳn nhé.")
            database.save_user_state(uid, state, cache)
            return

        if cur not in state["learned"]:
            state["learned"].append(cur)
        
        count = len(state["session"])
        
        if count >= 12:
            state["mode"] = "PRE_QUIZ"
            state["next_time"] = common.get_ts() + 540
            review_words = state["session"]
            review_msg = "\n".join([f"• {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in review_words])
            fb_service.send_text(uid, f"🛑 **HOÀN THÀNH 12 TỪ**\nTổng hợp:\n{review_msg}\n\n☕ Nghỉ 9 phút nhé!", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return

        if count == 6:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540
            review_words = state["session"][0:6]
            review_msg = "\n".join([f"• {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in review_words])
            fb_service.send_text(uid, f"🌟 **CHẶNG 1 (6/12)**\n{review_msg}\n\n⏳ Nghỉ 9 phút.", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return

        if count % 2 == 0:
            state["mode"] = "SHORT_BREAK"
            state["next_time"] = common.get_ts() + 540
            words_2 = state["session"][-2:]
            review_msg = "\n".join([f"- {w['Hán tự']} ({w['Pinyin']}): {w['Nghĩa']}" for w in words_2])
            fb_service.send_text(uid, f"☕ **GIẢI LAO 9 PHÚT**\n{review_msg}", buttons=["Nghỉ ngay"])
            database.save_user_state(uid, state, cache)
            return
            
        fb_service.send_text(uid, "💪 Tuyệt vời! Bạn đã thuộc từ này. Học từ tiếp theo nhé:")
        time.sleep(1)
        send_next_word(uid, state, cache)
        
    else:
        if msg in ["tiếp", "next", "skip"]:
             fb_service.send_text(uid, f"⚠️ Bạn cần gõ đủ 5 lần để nhớ. Đừng bỏ cuộc! Gõ lại **{cur}** nào.")
        else:
             fb_service.send_text(uid, f"⚠️ Chưa đúng. Hãy gõ lại từ **{cur}** nhé.")
