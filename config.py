import os

# Token Facebook (Có thể để đây hoặc đưa lên Env Variable nốt cho an toàn)
PAGE_ACCESS_TOKEN = "EAAbQQNNSmSMBQM5JdL7WYT15Kpz2WUip1Tte40vI75VbtRNm1O1F5mauEtTpzsTvetV9DFjEj4rRsWMUvZB8c2RvwV4FIhX0ky4bjoup8vjJrhyjiUPgUCpR0Gkg1UDxEiorU6C5LORUGwhBrRBIvRL7a8WQmtoafKpaxRkgjeZCfWQZBsqGZBNxEMoUuaFclIqWkwZDZD"
VERIFY_TOKEN = "hsk_mat_khau_bi_mat"

# --- QUAN TRỌNG: LẤY KEY TỪ BIẾN MÔI TRƯỜNG ---
# Code này sẽ tự động lấy Key bạn vừa lưu trên Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

DATABASE_URL = os.environ.get('DATABASE_URL')
