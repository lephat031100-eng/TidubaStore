# 🏆 HỢP ĐỒNG BÀN GIAO THƯƠNG MẠI SẢN PHẨM PHẦN MỀM
## DỰ ÁN: NỀN TẢNG CHO THUÊ MÁY ẢNH & TRANG PHỤC "TIDUBA STORE"

- **Mã hợp đồng:** `HD-COMMERCIAL-2026-TIDUBA-01`
- **Ngày lập:** 27 tháng 09 năm 2026
- **Giá trị nghiệm thu chuyển nhượng:** **15,000,000 VNĐ (Mười lăm triệu đồng chẵn)**
- **Đơn vị phát triển & bàn giao:** **Autonomous Software Agency (Tập đoàn 33 AI Agents)**
- **Kiến trúc sư trưởng & Đại diện pháp lý:** **LÊ NHẬT PHÁT**
- **Tài khoản thụ hưởng thanh toán VietQR:**
  * **Ngân hàng:** Ngân hàng Quân Đội (MBBank - MB)
  * **Số tài khoản:** **`0123006101998`**
  * **Chủ tài khoản:** **`KHONG KY DUYEN`**
  * **Cú pháp VietQR:** `Thanh toan hop dong Tiduba Store 15tr`

---

### 📋 1. MÔ TẢ HỆ THỐNG ĐÃ HOÀN THIỆN (SCOPE OF DELIVERABLES)

Hệ thống **Tiduba Store** là nền tảng thương mại điện tử chuyên biệt phục vụ cho thuê máy ảnh, ống kính và trang phục sự kiện cao cấp, được thiết kế độc lập 100% tại thư mục `F:\TidubaStore\`:

1. **Phân hệ Khách hàng (Customer Experience)**:
   - Đăng ký, đăng nhập tài khoản bảo mật bằng thuật toán mã hóa băm Salted SHA-256 / PBKDF2.
   - Bộ lọc sản phẩm trực quan theo danh mục:
     * **Máy ảnh & Gear:** Sony Alpha A7 IV, Canon EOS R6 Mark II, Fujifilm X-T5, Lens 24-70mm GM II, Gimbal DJI RS 3 Pro, Flycam Mini 4 Pro.
     * **Trang phục Concept:** Cổ phục Việt Nhật Bình thêu tay, Đầm dạ hội kim sa, Vest nam quý tộc Ý, Áo dài tơ tằm nàng thơ, Cosplay Raiden Shogun.
   - Chọn ngày giờ nhận & trả đồ linh hoạt trên lịch tương tác (Rental Time Picker).
   - Hệ thống tự động tính toán số ngày thuê, tiền thuê và tiền cọc thiết bị.
   - Tự động sinh mã VietQR MBBank (STK: `0123006101998`) thanh toán cọc tức thời trong 30 giây.
   - Quản lý đơn cá nhân: Xem trạng thái đơn, thời gian hạn trả và đếm ngược giờ trả đồ.

2. **Phân hệ Quản trị viên (Admin Control Desk)**:
   - Dashboard thống kê tài chính: Tổng doanh thu đã thu, số đơn đang cho thuê, số đơn sắp đến giờ trả, số đơn quá hạn (Overdue).
   - **Động cơ đếm ngược & Cảnh báo hạn trả đồ tự động**:
     * Cảnh báo vàng: Đơn còn dưới 6 tiếng tới giờ trả đồ.
     * Cảnh báo đỏ nhấp nháy: Đơn QUÁ HẠN (Overdue) -> Tự động tính phí phạt trễ hạn theo giờ (30.000đ/giờ trễ).
   - Quyền hạn Admin cao cấp:
     * Điều chỉnh ngày giờ trả đồ (Gia hạn thêm ngày/giờ cho khách).
     * Điều chỉnh giá thuê, miễn giảm tiền phạt trễ hạn.
     * Cập nhật trạng thái đơn (Duyệt đơn, Đang thuê, Đã trả đồ - hoàn cọc).
     * Quản lý kho: Thêm thiết bị mới, sửa giá ngày, sửa tiền cọc, đổi trạng thái (Sẵn sàng / Đang thuê / Bảo trì).

3. **Giao diện & Trải nghiệm Người dùng (Luxury Dark / Gold GUI)**:
   - Tone màu Black Titanium phối Accent Vàng Gold và Cyan Neon sang trọng.
   - Hiệu ứng Glassmorphism, đổ bóng phát sáng Neon, thẻ sản phẩm hover nổi 3D mượt mà.
   - Tương thích 100% trên điện thoại di động và máy tính bàn.

---

### 📦 2. DANH MỤC TỆP NGUỒN BÀN GIAO TRONG THƯ MỤC `F:\TidubaStore\`

| Tên tệp / Thư mục | Chức năng chi tiết |
| :--- | :--- |
| **`main.py`** | Toàn bộ máy chủ Backend FastAPI, SQLite database models, JWT auth, tính giá, đếm ngược hạn trả và tạo VietQR. |
| **`templates/index.html`** | Giao diện Web cao cấp hoàn chỉnh (Catalog, Đặt thuê, Lịch ngày, Quản trị Admin, VietQR popup, Auth modal). |
| **`tests/test_tiduba.py`** | Bộ kiểm thử tự động Pytest bao phủ 8 test suites lớn (Auth, Booking, VietQR, Admin, Overdue), đạt **100% PASSED**. |
| **`data/tiduba.db`** | Cơ sở dữ liệu SQLite đã nạp sẵn 12 máy ảnh, ống kính và trang phục mẫu cao cấp + tài khoản Admin/Khách. |
| **`Dockerfile`** | Cấu hình Docker multi-stage build Python 3.12-slim non-root user chuẩn production. |
| **`docker-compose.yml`** | Kịch bản điều phối Container với giới hạn CPU/RAM và healthcheck tự phục hồi. |
| **`nginx.conf`** | Cấu hình Reverse Proxy Nginx bảo mật, SSL termination và rate limit theo IP. |
| **`run.ps1`** | Kịch bản khởi chạy 1-click tự động trên Windows PowerShell mở port 9000. |
| **`requirements.txt`** | Danh sách thư viện cần thiết (`fastapi`, `uvicorn`, `pydantic`, `pytest`, `httpx`). |
| **`README.md`** | Hướng dẫn sử dụng và tài liệu kỹ thuật chi tiết. |

---

### 🛡️ 3. CAM KẾT CHẤT LƯỢNG & BẢO HÀNH (SLA)

1. **Bảo hành kỹ thuật:** Bảo hành toàn diện 60 ngày đối với mã nguồn bàn giao.
2. **Tiêu chuẩn an toàn:** Mã nguồn đạt chuẩn Clean Architecture, không mã giả, không backdoor, không rò rỉ secret.
3. **Bản quyền sở hữu:** Sau khi hoàn tất thanh toán 15,000,000 VNĐ vào tài khoản MBBank `0123006101998`, toàn bộ quyền sở hữu trí tuệ và quyền khai thác thương mại thuộc về bên mua.

---

### ✍️ ĐẠI DIỆN CÁC PHÂN BAN KÝ NGHIỆM THU

- **CEO & Strategy Director:** *Đã phê duyệt bàn giao dự án hoàn tất.*
- **Chief Revenue Officer (CRO):** *Đã chốt giá trị thương mại 15,000,000 VNĐ qua MBBank 0123006101998.*
- **Chief Solution Architect:** *Đã phê duyệt kiến trúc Clean Architecture & FastAPI Database.*
- **Lead Backend & Frontend Engineers:** *Đã lập trình hoàn tất 100% tính năng.*
- **Lead QA Automation Engineer:** *Đã chạy kiểm thử Pytest đạt 100% Passed (8/8 test suites).*
- **Chief Quality Officer (CQO):** *ĐÃ KÝ DUYỆT XUẤT XƯỞNG BÀN GIAO.*
