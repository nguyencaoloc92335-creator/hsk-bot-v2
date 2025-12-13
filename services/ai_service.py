import random
import re

# Dữ liệu trò chuyện được lập trình sẵn
CHAT_DATA = {
    "greetings": {
        "keys": ["hi", "hello", "chào", "halo", "alo", "ê"],
        "reply": [
            "👋 Chào bạn! Sẵn sàng học từ vựng chưa?",
            "Hello! Gõ 'Bắt đầu' để học nhé.",
            "Chào bạn, chúc bạn một ngày tốt lành! ☀️"
        ]
    },
    "thanks": {
        "keys": ["cảm ơn", "thank", "tks", "ok"],
        "reply": ["👌 Không có chi!", "Đừng khách sáo nè.", "🥰"]
    },
    "compliment": {
        "keys": ["giỏi", "thông minh", "hay", "tốt", "good"],
        "reply": ["Cảm ơn bạn quá khen! 😳", "Mình vẫn đang học hỏi thêm ạ.", "Bot mà lị! 😎"]
    },
    "insult": {
        "keys": ["ngu", "dốt", "kém", "chán", "cút"],
        "reply": ["Mình xin lỗi nếu làm bạn phật ý. 😿", "Mình sẽ cố gắng cải thiện hơn.", "Đừng mắng mình tội nghiệp..."]
    },
    "tired": {
        "keys": ["mệt", "chán quá", "buồn ngủ"],
        "reply": ["Mệt thì gõ 'Nghỉ' để thư giãn chút đi bạn.", "Cố lên nào! Học xong rồi nghỉ.", "Uống chút nước rồi học tiếp nhé! ☕"]
    }
}

DEFAULT_REPLIES = [
    "Mình không hiểu lắm. Bạn gõ **Menu** để xem hướng dẫn nhé.",
    "Câu này khó quá, mình chỉ biết dạy tiếng Trung thôi 😅",
    "Gõ **'Bắt đầu'** để học từ vựng đi bạn ơi.",
    "Mình là Bot học tập, không phải ChatGPT đâu nha 🤖"
]

def chat_reply(text):
    """Hàm trả lời tin nhắn dựa trên từ khóa"""
    msg = text.lower().strip()
    
    # Duyệt qua các chủ đề để tìm từ khóa
    for topic, data in CHAT_DATA.items():
        if any(key in msg for key in data["keys"]):
            return random.choice(data["reply"])
    
    # Nếu không khớp từ khóa nào -> Trả lời ngẫu nhiên mặc định
    return random.choice(DEFAULT_REPLIES)

def generate_sentence_with_annotation(word):
    """
    Vì bỏ AI nên hàm này chỉ trả về dữ liệu cơ bản.
    Không tạo ví dụ giả để tránh sai ngữ pháp.
    """
    hanzi = word.get('Hán tự', '') or word.get('hanzi', '')
    meaning = word.get('Nghĩa', '') or word.get('meaning', '')
    
    # Trả về cấu trúc rỗng nhưng an toàn
    return {
        "sentence_han": "", 
        "sentence_pinyin": "", 
        "sentence_viet": "", 
        "new_words": []
    }
