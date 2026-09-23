# E-Reader Python (Readest Inspired)

Một ứng dụng đọc sách hiện đại, mã nguồn mở được xây dựng bằng Python và PyQt6, tập trung vào hiệu năng, trải nghiệm người dùng và khả năng tùy biến cao.

## ✨ Tính năng chính

- **Hỗ trợ đa định dạng:** EPUB (tối ưu hóa Rust), MOBI, FB2, HTML, TXT.
- **Thư viện thông minh:** Tự động quét sách, quản lý hơn 10.000 đầu sách mượt mà với kỹ thuật nạp dữ liệu theo lô (batch loading).
- **Trình đọc cao cấp:**
  - Chế độ nạp chương nhanh (lazy loading) & Caching.
  - Tùy chỉnh Font chữ, kích thước, giãn dòng.
  - Chế độ giao diện: Sáng (Light), Tối (Dark), Sepia.
- **Tính năng nâng cao:**
  - **TTS (Text-to-Speech):** Đọc sách bằng giọng nói nhân tạo.
  - **Đồng bộ hóa:** Hỗ trợ giao thức KOReader Sync để đồng bộ tiến trình đọc trên nhiều thiết bị.
  - **Ghi chú & Dấu trang:** Quản lý chú thích và các trang yêu thích.
  - **Plugin System:** Dễ dàng mở rộng tính năng qua Python plugins.

## 🚀 Cài đặt & Khởi chạy

### Yêu cầu hệ thống
- Python 3.10 trở lên.
- Windows (Khuyến khích Segoe UI font) hoặc Linux/macOS.

### Các bước cài đặt

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-repo/e-reader-python.git
   cd e-reader-python
   ```

2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Khởi chạy:**
   - Chạy trực tiếp: `python -m ereader`
   - Hoặc sử dụng tệp Windows Batch: `run.bat`

## 🛠 Cấu trúc dự án

- `ereader/`: Gói mã nguồn chính.
  - `ui/`: Các thành phần giao diện (MainWindow, LibraryView, ReaderView, v.v.).
  - `formats/`: Trình xử lý các định dạng sách khác nhau.
  - `features/`: Các tính năng phụ trợ (TTS, Sync, Annotation).
  - `db.py`: Quản lý cơ sở dữ liệu SQLite (WAL mode).
  - `config.py`: Quản lý cấu hình YAML.
- `plugins/`: Thư mục chứa các plugin mở rộng.
- `requirements.txt`: Danh sách các thư viện phụ thuộc.

## ⚙️ Cấu hình

Dữ liệu ứng dụng và tệp `config.yaml` được lưu tại:
- **Windows:** `%APPDATA%/ereader`
- **Linux/macOS:** `~/.config/ereader`

Bạn có thể chỉnh sửa `config.yaml` để thay đổi thư mục chứa sách, theme mặc định hoặc cài đặt đồng bộ hóa.

## 🤝 Đóng góp

Mọi đóng góp về mã nguồn, báo lỗi hoặc đề xuất tính năng mới đều được chào đón! Hãy mở một Issue hoặc tạo Pull Request.

---
*Phát triển bởi đội ngũ đam mê đọc sách.*
