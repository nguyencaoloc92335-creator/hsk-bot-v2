import requests
import json
import os
import time
from gtts import gTTS
from config import PAGE_ACCESS_TOKEN

def send_text(uid, txt, buttons=None):
    """
    buttons: List các nhãn nút. VD: ["Học tiếp", "Nghỉ ngơi"]
    """
    payload = {"recipient": {"id": uid}, "message": {"text": txt}}
    
    # Thêm Quick Replies (Nút bấm)
    if buttons:
        quick_replies = []
        for btn_title in buttons:
            quick_replies.append({
                "content_type": "text",
                "title": btn_title,
                "payload": btn_title.upper().replace(" ", "_") # Payload ví dụ: HOC_TIEP
            })
        payload["message"]["quick_replies"] = quick_replies

    try:
        requests.post("https://graph.facebook.com/v16.0/me/messages", 
            params={"access_token": PAGE_ACCESS_TOKEN}, 
            json=payload, timeout=10)
    except Exception as e: print(f"FB Error: {e}")

def send_audio(uid, txt):
    if not txt: return
    fname = f"tts_{uid}_{int(time.time())}.mp3"
    try:
        # --- SỬA LỖI TẠI ĐÂY: Đổi 'zh-cn' thành 'zh-CN' ---
        gTTS(text=txt, lang='zh-CN').save(fname)
        
        requests.post(f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
            data={'recipient': json.dumps({'id': uid}), 'message': json.dumps({'attachment': {'type': 'audio', 'payload': {}}})}, 
            files={'filedata': (fname, open(fname, 'rb'), 'audio/mp3')}, timeout=20)
    except Exception as e: print(f"Audio Error: {e}")
    finally: 
        if os.path.exists(fname): os.remove(fname)
