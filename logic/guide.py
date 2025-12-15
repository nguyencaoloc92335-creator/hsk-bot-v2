def get_full_guide():
    """
    Hàm trả về nội dung hướng dẫn chi tiết.
    Cập nhật nội dung phù hợp với tính năng Tạo kho và logic học mới.
    """
    return (
        "📘 **HƯỚNG DẪN SỬ DỤNG TRỢ LÝ HỌC TẬP** 📘\n"
        "────────────────────────\n\n"
        
        "🛠️ **1. TÙY CHỈNH KHO TỪ (TÍNH NĂNG MỚI)**\n"
        "Bạn có thể tự tạo lộ trình học riêng bằng cách lọc từ vựng:\n"
        "• Bước 1: Gõ lệnh `Tạo kho`.\n"
        "• Bước 2: Chọn nguồn từ vựng muốn duyệt (VD: HSK1, Chuyên_ngành...).\n"
        "• Bước 3: Bot sẽ hiện từng từ. Bấm **[Học]** để chọn hoặc **[Bỏ qua]**.\n"
        "• Bước 4: Sau khi chọn xong, đặt tên cho kho và chọn **Lưu vĩnh viễn** hoặc **Học ngay**.\n\n"

        "📚 **2. CHỌN KHO CÓ SẴN**\n"
        "• Gõ `Danh sách`: Xem thống kê các kho từ hiện có.\n"
        "• Gõ `Chọn [Tên]`: Để học trọn bộ kho đó.\n"
        "   👉 VD: `Chọn HSK1` hoặc `Chọn Chuyên_ngành`.\n"
        "• Gõ `Chọn Tất cả`: Để học trộn lẫn toàn bộ dữ liệu.\n\n"
        
        "🧠 **3. PHƯƠNG PHÁP HỌC TẬP**\n"
        "Bot áp dụng kỹ thuật **Lặp lại ngắt quãng** để tối ưu trí nhớ:\n"
        "🔹 **Học từ mới**: Mỗi phiên gồm **12 từ**. Bạn cần gõ lại đúng mỗi từ **5 lần** để ghi nhớ mặt chữ.\n"
        "🔹 **Giải lao**: Bot sẽ nhắc bạn nghỉ giải lao ngắn sau mỗi 6 từ và nghỉ **9 phút** sau khi xong 12 từ. Hãy tuân thủ để não bộ nạp kiến thức.\n"
        "🔹 **Ôn tập**: Sau giờ nghỉ, Bot sẽ gọi bạn dậy để Kiểm tra.\n\n"
        
        "✍️ **4. HỆ THỐNG KIỂM TRA (QUIZ)**\n"
        "Để hoàn thành bài học, bạn cần vượt qua 3 cấp độ:\n"
        "   1️⃣ Nhìn chữ Hán -> Đoán nghĩa.\n"
        "   2️⃣ Nhìn Nghĩa -> Viết chữ Hán.\n"
        "   3️⃣ Nghe Audio -> Viết nghĩa Tiếng Việt.\n"
        "⚠️ Nếu sai, từ đó sẽ được đánh dấu để ôn kỹ lại sau.\n\n"
        
        "⚙️ **5. CÁC LỆNH TIỆN ÍCH**\n"
        "⏸️ **Tạm dừng**: Gõ `Nghỉ` (hoặc `Nghỉ 30p` để hẹn giờ).\n"
        "▶️ **Tiếp tục**: Gõ `Tiếp` để quay lại bài học.\n"
        "🔄 **Làm mới**: Gõ `Reset` để xóa toàn bộ tiến độ về 0.\n\n"
        
        "────────────────────────\n"
        "💡 **Mẹo:** Hãy bật âm thanh để nghe phát âm chuẩn.\n"
        "👉 Gõ **'Bắt đầu'** hoặc **'Tạo kho'** để vào việc ngay!"
    )
