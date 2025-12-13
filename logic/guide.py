def get_full_guide():
    """
    Hàm trả về nội dung hướng dẫn chi tiết.
    Cập nhật nội dung tại đây mỗi khi có tính năng mới.
    """
    return (
        "📘 **CẨM NANG HƯỚNG DẪN SỬ DỤNG BOT** 📘\n"
        "────────────────────────\n\n"
        
        "1️⃣ **QUẢN LÝ KHO TỪ VỰNG**\n"
        "• Gõ `Danh sách`: Xem thống kê các kho từ (HSK1, HSK2...).\n"
        "• Gõ `Chọn [Tên]`: Để chọn kho học cụ thể.\n"
        "   👉 VD: `Chọn HSK1` hoặc `Chọn HSK1 HSK2`.\n"
        "• Gõ `Chọn Tất cả`: Để học trộn lẫn toàn bộ kho.\n\n"
        
        "2️⃣ **QUY TRÌNH HỌC TẬP (CƠ CHẾ MỚI)**\n"
        "Bot sẽ dạy theo **nhóm 12 từ** để tối ưu trí nhớ:\n"
        "🔹 **Giai đoạn 1**: Bot gửi lần lượt từng từ. Bạn gõ lại từ đó (hoặc gõ `OK`) để xác nhận.\n"
        "🔹 **Giai đoạn 2**: Khi đủ **6 từ**, Bot gửi danh sách ôn tập. Gõ `OK` để học tiếp.\n"
        "🔹 **Giai đoạn 3**: Khi đủ **12 từ**, Bot gửi danh sách ôn tập lần 2.\n"
        "🔹 **Giai đoạn 4**: **NGHỈ GIẢI LAO**. Sau khi xác nhận xong 12 từ, Bot sẽ yêu cầu bạn nghỉ **9 phút** để não bộ ghi nhớ.\n"
        "🔹 **Giai đoạn 5**: Hết 9 phút, Bot sẽ gọi bạn dậy để làm bài **Kiểm tra (Quiz)**.\n\n"
        
        "3️⃣ **HỆ THỐNG KIỂM TRA (QUIZ)**\n"
        "• Bài kiểm tra xuất hiện sau khi nghỉ giải lao.\n"
        "• Bạn phải vượt qua 3 cấp độ:\n"
        "   - Cấp 1: Nhìn chữ Hán -> Đoán nghĩa.\n"
        "   - Cấp 2: Nhìn Nghĩa -> Viết chữ Hán.\n"
        "   - Cấp 3: Nghe Audio -> Viết chữ Hán.\n"
        "• Nếu sai câu nào, Bot sẽ bắt làm lại đến khi thuộc mới thôi!\n\n"
        
        "4️⃣ **CÁC LỆNH TIỆN ÍCH**\n"
        "⏸️ **Tạm dừng**: Gõ `Nghỉ`, `Stop`, `Bận`.\n"
        "   👉 Bot sẽ dừng gửi tin nhắn. (Có thể gõ `Nghỉ 30p` để hẹn giờ).\n"
        "▶️ **Tiếp tục**: Gõ `Tiếp`, `Resume` để học lại.\n"
        "🔄 **Làm mới**: Gõ `Reset` để xóa toàn bộ tiến độ và học lại từ con số 0.\n\n"
        
        "────────────────────────\n"
        "💡 **Mẹo:** Hãy bật âm thanh để nghe phát âm chuẩn nhé!\n"
        "👉 Gõ **'Bắt đầu'** để vào bài học ngay!"
    )
