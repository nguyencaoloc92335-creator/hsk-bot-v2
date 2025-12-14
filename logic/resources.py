import random

# Kho câu khen thưởng theo cấp độ (Streak)
CORRECT_LV1 = [ # Đúng 1-2 câu
    "✅ Chính xác!", "✅ Đúng rồi.", "✅ Chuẩn!", "✅ Ok, tiếp tục nào.", "✅ Good job!"
]

CORRECT_LV2 = [ # Đúng 3-5 câu
    "🔥 Quá đỉnh!", "🔥 Xuất sắc!", "🔥 Bạn đang vào guồng đấy!", "🔥 Hay lắm!", "🔥 Không trượt phát nào!"
]

CORRECT_LV3 = [ # Đúng > 5 câu
    "🚀 THẦN ĐỒNG TIẾNG TRUNG!", "🚀 Đỉnh của chóp!", "🚀 Không ai cản được bạn!", "🚀 Siêu cấp vip pro!", "🚀 Tuyệt vời ông mặt trời!"
]

# Kho câu an ủi khi sai
WRONG = [
    "❌ Sai mất rồi...", "❌ Tiếc quá, sai một chút thôi.", "❌ Ồ no, chưa đúng.", "❌ Cố lên, thử lại lần sau nhé.", "❌ Đừng nản, sai thì sửa!"
]

def get_praise(streak):
    if streak >= 5: return random.choice(CORRECT_LV3)
    if streak >= 3: return random.choice(CORRECT_LV2)
    return random.choice(CORRECT_LV1)

def get_wrong():
    return random.choice(WRONG)
