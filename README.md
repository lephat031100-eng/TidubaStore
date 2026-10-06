# 📸 TIDUBA STORE - HỆ THỐNG CHO THUÊ MÁY ẢNH & TRANG PHỤC CAO CẤP
*(Tiduba Camera & Fashion Rental Platform)*

Dự án phần mềm thương mại độc lập phát triển bởi **Autonomous Software Agency** dành riêng cho khách hàng.  
Toàn bộ mã nguồn, cơ sở dữ liệu và giao diện web được đặt độc lập 100% tại thư mục `F:\TidubaStore\`.

---

## 🚀 1. Khởi Động Nhanh 1-Click (Quickstart)

### Cách 1: Chạy trực tiếp bằng PowerShell
Mở PowerShell tại thư mục `F:\TidubaStore\` và chạy lệnh:
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```
Hệ thống sẽ tự động khởi động server tại cổng **`http://localhost:9000`** và tự động mở trình duyệt!

### Cách 2: Chạy bằng lệnh Python
```powershell
F:\AI\venv\Scripts\python.exe main.py
```

### Cách 3: Chạy bằng Docker
```bash
docker-compose up -d
```

---

## 👥 2. Tài Khoản Đăng Nhập Mẫu

| Loại tài khoản | Tên đăng nhập | Mật khẩu | Quyền hạn |
| :--- | :--- | :--- | :--- |
| **Quản trị viên (Admin)** | **`admin`** | **`admin123`** | Toàn quyền Admin: xem doanh thu, duyệt đơn, chỉnh ngày giờ trả đồ, chỉnh giá thuê, miễn giảm phí phạt trễ hạn, xem cảnh báo quá hạn, thêm/xóa máy ảnh & trang phục. |
| **Khách hàng mẫu** | **`khachhang`** | **`123456`** | Xem danh mục máy ảnh/trang phục, đặt thuê chọn ngày giờ nhận - trả, lấy mã VietQR thanh toán cọc, xem đếm ngược thời gian trả đồ. |

*(Khách hàng mới có thể tự do bấm tab "Đăng Ký Mới" trên Web để tạo tài khoản cá nhân).*

---

## 🌟 3. Các Tính Năng Cốt Lõi Đã Hoàn Thiện

1. **Danh Mục Sản Phẩm Đa Dạng**:
   - **Máy ảnh chuyên nghiệp**: Sony Alpha A7 IV, Canon EOS R6 Mark II, Fujifilm X-T5, Lens 24-70mm f/2.8 GM II, Gimbal DJI RS 3 Pro, Flycam DJI Mini 4 Pro.
   - **Trang phục Concept**: Cổ phục Việt Nhật Bình thêu tay, Đầm dạ hội kim sa tiệc đêm, Bộ vest nam quý tộc Ý, Áo dài tơ tằm nàng thơ, Cosplay Raiden Shogun.
2. **Quy Trình Đặt Thuê & Lịch Ngày Giờ (Rental Time Picker)**:
   - Khách tự chọn ngày giờ nhận đồ và ngày giờ trả đồ.
   - Hệ thống tự động tính số ngày thuê và thành tiền kèm tiền cọc thiết bị.
3. **Thanh Toán VietQR MBBank Tự Động**:
   - Tự động sinh mã VietQR Napas 247 trỏ về tài khoản **MBBank (Ngân hàng Quân Đội) 0123006101998 (KHONG KY DUYEN)**.
   - Nội dung chuyển khoản mã hóa tự động theo mã đơn thuê (ví dụ: `Thanh toan thue do TDB-123456`).
4. **Cơ Chế Đếm Ngược & Cảnh Báo Giờ Trả Đồ**:
   - Tự động đếm ngược số giờ còn lại đến hạn trả.
   - Cảnh báo vàng: Đơn còn dưới 6 tiếng tới giờ trả.
   - Cảnh báo đỏ nhấp nháy: Đơn **QUÁ HẠN (Overdue)** -> Tự động tính phí phạt trễ hạn theo giờ (30.000đ/giờ trễ).
5. **Quyền Hạn Admin Đặc Biệt**:
   - Gia hạn thêm ngày/giờ trả đồ trực tiếp cho khách.
   - Điều chỉnh lại giá thuê hoặc tiền phạt trễ hạn.
   - Cập nhật trạng thái đơn (Duyệt đơn, Đang thuê, Đã trả đồ xong).
   - Quản lý kho máy ảnh và trang phục (Thêm mới, sửa giá, sửa tiền cọc, đổi trạng thái bảo trì).

---

## 🧪 4. Chạy Kiểm Thử Tự Động (Unit Tests)

Bộ kiểm thử tự động 8 test suites lớn đã được lập trình sẵn tại `tests/test_tiduba.py`:
```powershell
F:\AI\venv\Scripts\python.exe -m pytest tests/test_tiduba.py -v
```
*(Kết quả: **8 passed in 1.27s - 100% Passed**).*

---

## 💳 5. Thông Tin Thanh Toán Hợp Đồng Chuyển Nhượng

- **Giá trị nghiệm thu:** **15,000,000 VNĐ**
- **Ngân hàng:** **MBBank (Ngân hàng Quân Đội - MB)**
- **Số tài khoản:** **`0123006101998`**
- **Chủ tài khoản:** **`KHONG KY DUYEN`**
- **Văn bản pháp lý:** Chi tiết xem tại `HỢP_ĐỒNG_BÀN_GIAO_TIDUBA.md`.
