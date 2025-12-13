import requests
import json
import os
import time
from gtts import gTTS
from config import PAGE_ACCESS_TOKEN

def send_text(uid, txt):
    try:
        requests.post("https://graph.facebook.com/v16.0/me/messages", 
            params={"access_token": PAGE_ACCESS_TOKEN}, 
            json={"recipient": {"id": uid}, "message": {"text": txt}}, timeout=10)
    except Exception as e: print(f"FB Error: {e}")

def send_audio(uid, txt):
    if not txt: return
    fname = f"tts_{uid}_{int(time.time())}.mp3"
    try:
        gTTS(text=txt, lang='zh-cn').save(fname)
        requests.post(f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
            data={'recipient': json.dumps({'id': uid}), 'message': json.dumps({'attachment': {'type': 'audio', 'payload': {}}})}, 
            files={'filedata': (fname, open(fname, 'rb'), 'audio/mp3')}, timeout=20)
    except Exception as e: print(f"Audio Error: {e}")
    finally: 
        if os.path.exists(fname): os.remove(fname)