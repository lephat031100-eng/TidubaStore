# 🌐 HƯỚNG DẪN MỞ WEB CÔNG KHAI TÊN MIỀN CỐ ĐỊNH & MIỄN PHÍ VĨNH VIỄN 100%

Hệ thống **Tiduba Store** đã được tối ưu hóa toàn diện:
- **Đã fix lỗi đăng nhập:** Mở quyền CORS toàn cầu (`*`), bạn và khách hàng truy cập từ bất kỳ tên miền nào hay điện thoại nào đều **đăng nhập, xem đồ, đặt thuê, gửi ảnh biên lai** mượt mà 100%.
- **Không tốn 1 xu mua tên miền.**

Dưới đây là 2 cách chuẩn nhất để bạn chọn:

---

## 🚀 CÁCH 1 (KHUYÊN DÙNG NHẤT): ĐƯA LÊN CLOUD MIỄN PHÍ (RENDER.COM)
> **Ưu điểm lớn nhất:** **TẮT MÁY TÍNH KHÁCH VẪN VÀO ĐƯỢC 24/7!**  
> Tên miền cố định vĩnh viễn dạng: `https://tidubastore.onrender.com` (hoặc tên bạn chọn).  
> Hoàn toàn **MIỄN PHÍ 100%**, không cần thẻ ngân hàng.

### Các bước thực hiện (chỉ làm 1 lần mất 3 phút):
1. **Bước 1:** Đưa code lên GitHub:
   - Tạo tài khoản miễn phí tại [github.com](https://github.com).
   - Tạo 1 repository mới (chọn Private hoặc Public đều được), ví dụ tên: `TidubaStore`.
   - Mở terminal trong thư mục `F:\TidubaStore` và chạy:
     ```bash
     git remote add origin https://github.com/<tên-github-của-bạn>/TidubaStore.git
     git add .
     git commit -m "Tiduba Store online"
     git push -u origin master
     ```
2. **Bước 2:** Đăng ký Render.com:
   - Vào [render.com](https://render.com), bấm **Get Started for Free** (đăng nhập bằng tài khoản GitHub vừa tạo).
3. **Bước 3:** Tạo Web Service:
   - Bấm nút **New +** $\rightarrow$ chọn **Web Service**.
   - Chọn kho code `TidubaStore` trên GitHub của bạn.
   - Điền thông tin:
     - **Name:** `tidubastore` (link web của bạn sẽ là `https://tidubastore.onrender.com`).
     - **Environment:** `Python 3`.
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Instance Type:** Chọn gói **Free ($0/month)**.
   - Bấm **Create Web Service**.
4. **Xong!** Bạn nhận ngay link cố định `https://tidubastore.onrender.com`.  
   👉 Chia sẻ link này cho khách xem đồ và đặt đơn, dù bạn tắt máy tính ngủ web vẫn hoạt động bình thường!

---

## ⚡ CÁCH 2: DÙNG TÊN MIỀN CỐ ĐỊNH MIỄN PHÍ TRÊN MÁY TÍNH (NGROK STATIC DOMAIN)
> **Ưu điểm:** Chạy trực tiếp dữ liệu trên máy tính của bạn, không cần đưa code lên mạng.  
> Ngrok cấp cho mỗi tài khoản **1 Tên miền tĩnh cố định vĩnh viễn miễn phí 100%** (ví dụ: `https://tiduba-store.ngrok-free.app`).  
> Tắt máy tính hoặc tắt web mở lại thì link **KHÔNG BAO GIỜ BỊ ĐỔI!**

### Các bước thực hiện:
1. Đăng ký tài khoản miễn phí tại [ngrok.com](https://ngrok.com).
2. Vào mục **Cloud Edge** $\rightarrow$ **Domains** $\rightarrow$ Bấm **Create Domain** để nhận 1 tên miền cố định miễn phí (ví dụ: `vivid-elk-nicely.ngrok-free.app` hoặc bạn tự đặt tên).
3. Tải `ngrok` về hoặc cài qua terminal:
   ```powershell
   winget install ngrok
   ```
4. Lưu mã token của bạn (lấy tại trang dashboard ngrok):
   ```powershell
   ngrok config add-authtoken <TOKEN_CỦA_BẠN>
   ```
5. Mỗi khi mở web công khai, chạy lệnh:
   ```powershell
   ngrok http 9000 --domain=<ten-mien-tinh-cua-ban>.ngrok-free.app
   ```
   👉 Tên miền này giữ nguyên vĩnh viễn, bạn và khách hàng đăng nhập thoải mái!

---

## 🛠️ CÁCH 3: DÙNG LOCALTUNNEL VỚI SUBDOMAIN CỐ ĐỊNH
> Không cần tạo tài khoản hay đăng ký bất kỳ đâu.

Mở PowerShell tại thư mục `F:\TidubaStore` và chạy:
```powershell
npx localtunnel --port 9000 --subdomain tidubastore
```
- Đường link công khai cố định sẽ là: **`https://tidubastore.loca.lt`**
- Đã fix lỗi CORS: Đăng nhập tài khoản, xem đồ, đặt đơn hoạt động 100%.
- Lần đầu khách truy cập vào trang này sẽ hiện ô hỏi Password IP: Khách chỉ cần nhập địa chỉ IP công khai của máy chủ (lấy tại [ipv4.icanhazip.com](https://ipv4.icanhazip.com)) là vào thẳng web.
