import random
import time
import threading
from services import fb_service
from logic import common, resources # Import kho câu thoại
import database

def start_quiz_level(uid, state, cache, level):
    state["mode"] = "QUIZ"
    
    if level == 1 or level > state["quiz"].get("level", 0):
        state["quiz"]["queue"] = list(range(len(state["session"]))) 
        random.shuffle(state["quiz"]["queue"])
        # Nếu chưa có danh sách failed tổng (cho cả phiên), tạo mới
        if "session_failed" not in state["quiz"]:
            state["quiz"]["session_failed"] = [] # Dùng để lưu vết các từ sai để xóa sau này
        
        state["quiz"]["failed"] = [] # Failed của level hiện tại
    
    state["quiz"]["level"] = level
    state["quiz"]["idx"] = 0
    state["streak"] = 0 # Reset streak khi qua màn mới
    
    titles = {
        1: "CẤP 1: NHÌN HÁN -> ĐOÁN NGHĨA", 
        2: "CẤP 2: NHÌN NGHĨA -> VIẾT HÁN", 
        3: "CẤP 3: NGHE AUDIO -> DỊCH NGHĨA"
    }
    
    fb_service.send_text(uid, f"🛑 **KIỂM TRA {titles.get(level, 'CUỐI')}**\n(Cần đúng {len(state['session'])}/{len(state['session'])} câu)")
    time.sleep(1)
    send_question(uid, state, cache)

def send_question(uid, state, cache):
    q = state["quiz"]
    
    if q["idx"] >= len(q["queue"]): 
        if len(q["failed"]) > 0:
            fb_service.send_text(uid, f"⚠️ Sai {len(q['failed'])} câu. Ôn lại nhé!")
            q["queue"] = q["failed"][:] 
            q["failed"] = []
            q["idx"] = 0
            state["streak"] = 0 # Reset streak khi phải làm lại
            random.shuffle(q["queue"])
            database.save_user_state(uid, state, cache)
            time.sleep(1)
            send_question(uid, state, cache)
        else:
            # Qua màn
            if q["level"] < 3:
                fb_service.send_text(uid, f"🎉 Xuất sắc! Lên Cấp {q['level']+1}...")
                start_quiz_level(uid, state, cache, q["level"] + 1)
            else:
                # ====================================================
                # LOGIC FEATURE 4: XÓA TỪ SAI KHỎI KHO ĐÃ HỌC
                # ====================================================
                failed_indices = state["quiz"].get("session_failed", [])
                removed_words = []
                
                # Chỉ xử lý nếu có từ sai
                if failed_indices:
                    # Lấy danh sách từ sai (unique)
                    unique_failed_idx = set(failed_indices)
                    
                    # Lấy Hanzi của các từ sai
                    failed_hanzis = [state["session"][i]["Hán tự"] for i in unique_failed_idx]
                    
                    # Xóa khỏi state["learned"]
                    original_learned = state.get("learned", [])
                    new_learned = [w for w in original_learned if w not in failed_hanzis]
                    state["learned"] = new_learned
                    removed_words = failed_hanzis
                
                # Reset biến tạm
                state["quiz"]["session_failed"] = [] 

                finish_msg = "🏆 **HOÀN THÀNH 3 CẤP ĐỘ!**\nBạn hãy nghỉ ngơi, 10 phút nữa mình sẽ gọi."
                if removed_words:
                    finish_msg += f"\n\n⚠️ **Lưu ý:** Có {len(removed_words)} từ bạn trả lời sai sẽ được đưa trở lại kho 'Chưa học' để ôn kỹ hơn vào lần sau."

                # Hiện nút bấm cho tiện
                fb_service.send_text(uid, finish_msg, buttons=["Nghỉ 10p", "Danh sách"])
                
                state["mode"] = "SHORT_BREAK" 
                state["session"] = [] 
                state["next_time"] = common.get_ts() + 600 
                state["waiting"] = False
                database.save_user_state(uid, state, cache)
        return

    w_idx = q["queue"][q["idx"]]
    word = state["session"][w_idx]
    lvl = q["level"]
    
    msg = ""
    if lvl == 1:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) **{word['Hán tự']}** nghĩa là gì?"
    elif lvl == 2:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) Viết chữ Hán cho: **{word['Nghĩa']}**"
    elif lvl == 3:
        msg = f"🎧 ({q['idx']+1}/{len(q['queue'])}) Nghe và viết **NGHĨA Tiếng Việt**"
        threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()

    # Không hiện nút bấm ở đây để bắt buộc gõ
    if msg: fb_service.send_text(uid, msg)
    database.save_user_state(uid, state, cache)

def handle_answer(uid, text, state, cache):
    q = state["quiz"]
    if q["idx"] >= len(q["queue"]): return

    w_idx = q["queue"][q["idx"]]
    word = state["session"][w_idx]
    ans = text.lower().strip()
    
    correct = False
    
    # --- FEATURE 2: CHECK THÔNG MINH ---
    if q["level"] in [1, 3]: # Check Nghĩa
        # Logic check nghĩa: Duyệt qua các nghĩa cách nhau bởi dấu phẩy
        meanings = word['Nghĩa'].lower().replace(';', ',').split(',')
        # Dùng smart check cho từng nghĩa
        if any(common.check_answer_smart(ans, m.strip()) for m in meanings if len(m.strip()) > 1):
            correct = True
        # Hoặc gõ đúng Hán tự
        if common.check_answer_smart(ans, word['Hán tự']): correct = True
        
    elif q["level"] == 2: # Check Hán tự
        if common.check_answer_smart(ans, word['Hán tự']): correct = True

    full_info = (f"🇨🇳 **{word['Hán tự']}** ({word['Pinyin']})\n"
                 f"🇻🇳 {word['Nghĩa']}")
    
    if correct:
        # --- FEATURE 1: RANDOM KHEN + STREAK ---
        state["streak"] = state.get("streak", 0) + 1
        praise = resources.get_praise(state["streak"])
        streak_msg = f" (🔥 Chuỗi: {state['streak']})" if state["streak"] > 2 else ""
        
        fb_service.send_text(uid, f"{praise}{streak_msg}\n{full_info}")
    else:
        # --- FEATURE 1 & 4: XỬ LÝ SAI ---
        state["streak"] = 0
        consolation = resources.get_wrong()
        
        fb_service.send_text(uid, f"{consolation} Đáp án là:\n{full_info}")
        
        if w_idx not in q["failed"]: q["failed"].append(w_idx)
        
        # Lưu vào danh sách sai TỔNG để xóa khỏi DB sau này
        if "session_failed" not in state["quiz"]: state["quiz"]["session_failed"] = []
        if w_idx not in state["quiz"]["session_failed"]:
            state["quiz"]["session_failed"].append(w_idx)

    threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()

    q["idx"] += 1
    database.save_user_state(uid, state, cache)
    time.sleep(1)
    send_question(uid, state, cache)
