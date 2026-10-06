# HƯỚNG DẪN CẤU HÌNH TÊN MIỀN CÔNG KHAI TIDUBASTORE.COM

Hệ thống **TidubaStore.com** đã được cấu hình toàn diện để hoạt động công khai trên Internet với thương hiệu và tên miền **TidubaStore.com**.

---

## 1. TRẠNG THÁI CÔNG KHAI ĐANG HOẠT ĐỘNG (LIVE NGAY BÂY GIỜ)

Hệ thống đang được mở đường truyền công khai bảo mật HTTPS (SSL) ra toàn cầu:

- **Link Trực Tiếp (Cloudflare HTTPS - Khách mở được trên mọi điện thoại/máy tính):**
  👉 **`https://areas-builders-herein-dam.trycloudflare.com`**
- **Link Cố Định Subdomain:**
  👉 **`https://tidubastore.loca.lt`**
- **Trang Quản Trị Admin:**
  👉 Mở file `F:\TidubaStore\dist\TidubaStoreAdmin.exe` (Chỉ dành cho Admin, bảo mật tuyệt đối)

---

## 2. HƯỚNG DẪN TRỎ TÊN MIỀN CHÍNH THỨC `TidubaStore.com`

Khi chủ cửa hàng sở hữu tên miền **`TidubaStore.com`** (mua từ Namecheap, GoDaddy, MatBao, PA Vietnam, v.v.), có 2 cách cực kỳ đơn giản để trỏ về máy:

### CÁCH 1: Dùng Cloudflare Tunnel (KHUYÊN DÙNG - Miễn phí 100%, bảo mật DDoS, không cần mở Port Router)
Công cụ `cloudflared.exe` đã được tải sẵn trong thư mục `F:\TidubaStore`.
1. Đăng ký tài khoản miễn phí tại **https://dash.cloudflare.com** và thêm tên miền `TidubaStore.com`.
2. Vào mục **Zero Trust** -> **Networks** -> **Tunnels** -> Chọn **Create a Tunnel**.
3. Chọn Windows, copy mã Token cài đặt và chạy lệnh:
   ```powershell
   .\cloudflared.exe service install <TOKEN-CUA-BAN>
   ```
4. Trên giao diện Cloudflare, chọn Public Hostname:
   - Subdomain: `@` hoặc `www`
   - Domain: `tidubastore.com`
   - Type: `HTTP`
   - URL: `localhost:9000`
👉 **Ngay lập tức, khách hàng khắp thế giới truy cập `https://tidubastore.com` sẽ vào thẳng cửa hàng của bạn!**

### CÁCH 2: Triển khai lên VPS / Server Riêng (Docker & Nginx có sẵn)
Thư mục dự án đã có sẵn:
- `docker-compose.yml`
- `Dockerfile`
- `nginx.conf` (Đã cấu hình sẵn cho `tidubastore.com`)

Chỉ cần upload thư mục lên VPS Linux và chạy:
```bash
docker-compose up -d --build
```
Và trỏ bản ghi **A Record** của `tidubastore.com` về địa chỉ IP của VPS.

---

## 3. CÁCH BẬT ĐƯỜNG TRUYỀN CÔNG KHAI MỖI KHI MỞ MÁY

Trong thư mục `F:\TidubaStore` có sẵn file:
👉 **`start_public_tunnel.ps1`**

Chỉ cần click chuột phải vào file **`start_public_tunnel.ps1`** -> Chọn **Run with PowerShell**, hệ thống sẽ tự động tạo đường link công khai HTTPS để gửi cho khách hoặc đối tác ngay lập tức!
