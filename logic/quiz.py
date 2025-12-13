import random
import time
import threading
from services import fb_service
import database

def start_quiz_level(uid, state, cache, level):
    state["mode"] = "QUIZ"
    
    # Reset queue nếu là level 1 hoặc chuyển level
    if level == 1 or level > state["quiz"]["level"]:
        state["quiz"]["queue"] = list(range(len(state["session"]))) # [0, 1, 2, 3, 4, 5]
        random.shuffle(state["quiz"]["queue"])
        state["quiz"]["failed"] = []
    
    state["quiz"]["level"] = level
    state["quiz"]["idx"] = 0
    
    titles = {1: "CẤP 1: NHÌN HÁN -> ĐOÁN NGHĨA", 2: "CẤP 2: NHÌN NGHĨA -> VIẾT HÁN", 3: "CẤP 3: NGHE -> VIẾT HÁN"}
    fb_service.send_text(uid, f"🛑 **KIỂM TRA {titles[level]}**\n(Phải đúng 6/6 từ mới qua màn)")
    time.sleep(1)
    send_question(uid, state, cache)

def send_question(uid, state, cache):
    q = state["quiz"]
    
    # Hết câu hỏi trong hàng đợi
    if q["idx"] >= len(q["queue"]): 
        if len(q["failed"]) > 0:
            fb_service.send_text(uid, f"⚠️ Sai {len(q['failed'])} từ. Ôn lại ngay!")
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
                fb_service.send_text(uid, "🏆 **HOÀN THÀNH 3 CẤP ĐỘ!**\nNghỉ ngơi nhé, 10 phút nữa học tiếp!")
                state["mode"] = "AUTO"
                state["session"] = []
                # Tính giờ nghỉ từ bây giờ
                from logic import common
                state["next_time"] = common.get_ts() + 600 
                state["waiting"] = False
                database.save_user_state(uid, state, cache)
        return

    # Lấy câu hỏi
    w_idx = q["queue"][q["idx"]]
    word = state["session"][w_idx]
    lvl = q["level"]
    
    if lvl == 1:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) **{word['Hán tự']}** nghĩa là gì?"
    elif lvl == 2:
        msg = f"❓ ({q['idx']+1}/{len(q['queue'])}) Viết chữ Hán cho: **{word['Nghĩa']}**"
    elif lvl == 3:
        msg = f"🎧 ({q['idx']+1}/{len(q['queue'])}) Nghe và viết lại từ (Audio đang gửi...)"
        threading.Thread(target=fb_service.send_audio, args=(uid, word['Hán tự'])).start()

    fb_service.send_text(uid, msg)
    database.save_user_state(uid, state, cache)

def handle_answer(uid, text, state, cache):
    q = state["quiz"]
    w_idx = q["queue"][q["idx"]]
    word = state["session"][w_idx]
    ans = text.lower().strip()
    
    correct = False
    if q["level"] == 1: # Check nghĩa (tương đối)
        if any(x in ans for x in word['Nghĩa'].lower().split(',')) or len(ans) > 2: correct = True
    elif q["level"] in [2, 3]: # Check Hán tự
        if word['Hán tự'] in text: correct = True

    if correct:
        fb_service.send_text(uid, "✅ Đúng!")
    else:
        fb_service.send_text(uid, f"❌ Sai. Đáp án: {word['Hán tự']} - {word['Nghĩa']}")
        if w_idx not in q["failed"]: q["failed"].append(w_idx)

    q["idx"] += 1
    database.save_user_state(uid, state, cache)
    time.sleep(1)
    send_question(uid, state, cache)