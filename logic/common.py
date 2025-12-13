import time
from datetime import datetime, timedelta, timezone

def get_ts(): return int(time.time())

def get_vn_time(): 
    return datetime.now(timezone(timedelta(hours=7)))

def is_sleep_mode():
    return 0 <= get_vn_time().hour < 6

def get_today_str():
    return get_vn_time().strftime("%Y-%m-%d")