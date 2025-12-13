import random
import time
import threading
from services import fb_service
import database

def start_quiz_level(uid, state, cache, level):
    state["mode"] = "QUIZ"
    
    # Nếu là level 1 hoặc chuyển level mới -> Tạo lại hàng đợi
    if level == 1 or level > state["quiz"].get("level", 0):
        # Tạo danh sách index [0, 1, 2, 3, 4, 5] tương ứng với session
        state["quiz"]["queue"] = list(range(len(state["session"]))) 
        random.shuffle(state["quiz"]["queue"])
        state["quiz"]["failed"] = []
    
    state["quiz"]["level"] = level
    state["quiz"]["idx"] = 0
    
    # --- CẬP NHẬT TÊN CẤP ĐỘ ---
    titles = {
        1: "CẤP 1: NHÌN HÁN -> ĐOÁN NGHĨA", 
        2: "CẤP 2: NHÌN NGHĨA -> VIẾT HÁN", 
        3: "CẤP 3: NGHE AUDIO -> DỊCH NGHĨA" # <--- Đã sửa thành Dịch nghĩa
    }
    
    fb_service.send_text(uid, f"🛑 **KIỂM TRA {titles.get(level, 'CUỐI')}**\n(Cần đúng {len(state['session'])}/{len(state['session'])} câu)")
    time.sleep(1)
    send_question(uid, state, cache)

def send_question(uid, state, cache):
    q = state["quiz"]
    
    # Kiểm tra xem đã hết câu hỏi chưa
    if q["idx"] >= len(q["queue"]): 
        if len(q["failed"]) > 0:
            fb_service.send_text(uid, f"⚠️ Sai {len(q['failed'])} câu. Ôn lại những câu sai nhé!")
            # Chỉ hỏi lại câu sai
            q["queue"] = q["failed"][:] 
            q["failed"] = []
            q["idx"] = 0
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
                fb_service.send_text(uid, "🏆 **HOÀN THÀNH 3 CẤP ĐỘ!**\nBạn hãy nghỉ ngơi, 10 phút nữa mình sẽ gọi.")
                state["mode"] = "AUTO"
                state["session"] = [] # Xóa session cũ
                
                # Hẹn giờ học tiếp
                from logic import common
                state["next_time"] = common.get_ts() + 600 # 10 phút
                state["waiting"] = False
                database.save_user_state(uid, state, cache)
        return

    # Lấy câu hỏi
    w_idx = q["queue"][q["idx"]]
    # Đảm bảo index hợp lệ
    if w_idx >= len(state["session"]):
        q["idx"] += 1
        send_question(uid, state, cache)
        return

    word = state["session"][w_idx]
    lvl = q["level"]
    
    msg = ""
    if lvl == 1:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) **{word['Hán tự']}** nghĩa là gì?"
    elif lvl == 2:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) Viết chữ Hán cho: **{word['Nghĩa']}**"
    elif lvl == 3:
        # --- CẬP NHẬT CÂU HỎI LEVEL 3 ---
        msg = f"🎧 ({q['idx']+1}/{len(q['queue'])}) Nghe và viết **NGHĨA Tiếng Việt** (Audio đang gửi...)"
        threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()

    if msg: fb_service.send_text(uid, msg)
    database.save_user_state(uid, state, cache)

def handle_answer(uid, text, state, cache):
    q = state["quiz"]
    
    # Bảo vệ lỗi index
    if q["idx"] >= len(q["queue"]):
        return # Tránh crash

    w_idx = q["queue"][q["idx"]]
    word = state["session"][w_idx]
    ans = text.lower().strip()
    
    correct = False
    
    # --- LOGIC CHECK ĐÁP ÁN MỚI ---
    
    # Nhóm 1: Check Nghĩa (Level 1 và Level 3)
    if q["level"] in [1, 3]: 
        # Logic check nghĩa tương đối (chứa từ khóa)
        meanings = word['Nghĩa'].lower().replace(';', ',').split(',')
        if any(m.strip() in ans for m in meanings if len(m.strip()) > 1):
            correct = True
        # Hoặc user gõ đúng Hán tự cũng châm chước tính là hiểu
        if word['Hán tự'] in text: correct = True
        
    # Nhóm 2: Check Hán tự (Level 2)
    elif q["level"] == 2: 
        if word['Hán tự'] in text: correct = True

    if correct:
        # --- CẬP NHẬT PHẢN HỒI KHI ĐÚNG ---
        # Gửi lại đầy đủ thông tin từ vựng
        reply = (f"✅ **Chính xác!**\n"
                 f"🇨🇳 {word['Hán tự']} ({word['Pinyin']})\n"
                 f"🇻🇳 {word['Nghĩa']}")
        fb_service.send_text(uid, reply)
    else:
        fb_service.send_text(uid, f"❌ Sai rồi. Đáp án: {word['Hán tự']} - {word['Nghĩa']}")
        if w_idx not in q["failed"]: q["failed"].append(w_idx)

    q["idx"] += 1
    database.save_user_state(uid, state, cache)
    time.sleep(1)
    send_question(uid, state, cache)
