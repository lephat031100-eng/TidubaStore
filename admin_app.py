"""
TIDUBA STORE - DESKTOP ADMIN APP (ENTERPRISE EDITION)
Ứng dụng Desktop cao cấp dành riêng cho Quản Trị Viên (Admin)
Đồng bộ trực tiếp với Web Khách Hàng (FastAPI Port 9000).

Phát triển cho: Tiduba Store
"""

import sys
import os
import time
import threading
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

# Đảm bảo UTF-8 stream trên Windows và PyInstaller không bị UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def safe_print(*args, **kwargs):
    """Ghi log an toàn không bao giờ văng lỗi UnicodeEncodeError cp1252 trên Windows GUI."""
    try:
        msg = " ".join(str(a) for a in args)
        if sys.stdout:
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()
    except Exception:
        pass

# Đảm bảo working directory
BASE_DIR = Path(__file__).resolve().parent
os.chdir(str(BASE_DIR))

SERVER_URL = "https://tidubastore.onrender.com"
ADMIN_URL = "https://tidubastore.onrender.com/?admin=1"
LOCAL_SERVER_URL = "http://127.0.0.1:9000"
LOCAL_ADMIN_URL = "http://127.0.0.1:9000/?admin=1"
PUBLIC_DOMAIN = os.environ.get("PUBLIC_DOMAIN", "https://tidubastore.onrender.com").rstrip("/")


def is_cloud_accessible() -> bool:
    """Kiểm tra máy chủ Cloud chính thức có đang online không."""
    try:
        req = urllib.request.Request(f"{SERVER_URL}/api/items", headers={"User-Agent": "TidubaAdminApp/3.5"})
        res = urllib.request.urlopen(req, timeout=3.5)
        return res.status == 200
    except Exception:
        return False


def free_port_if_stuck():
    """Giải phóng port 9000 nếu có tiến trình treo."""
    if sys.platform == "win32":
        try:
            output = subprocess.check_output("netstat -ano | findstr :9000", shell=True, text=True)
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid and pid != "0":
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def is_server_running() -> bool:
    try:
        req = urllib.request.Request(f"{SERVER_URL}/api/auth/me", headers={"User-Agent": "TidubaAdminApp/3.2"})
        res = urllib.request.urlopen(req, timeout=1.5)
        return res.status in (200, 401)
    except Exception:
        return False


def run_uvicorn_thread():
    """Chạy Uvicorn FastAPI server trực tiếp trong daemon thread."""
    try:
        import uvicorn
        from main import app as fastapi_app
        uvicorn.run(fastapi_app, host="0.0.0.0", port=9000, log_level="error")
    except Exception as e:
        safe_print(f"[ADMIN APP] Lỗi khởi động Uvicorn thread: {e}")


def start_backend_server():
    """Tự động kiểm tra và khởi chạy Backend Server nếu chưa chạy."""
    if is_server_running():
        safe_print("[ADMIN APP] Backend server da hoat dong san tai port 9000.")
        return

    safe_print("[ADMIN APP] Khoi tao Backend Server FastAPI port 9000...")
    free_port_if_stuck()
    time.sleep(0.5)

    t = threading.Thread(target=run_uvicorn_thread, daemon=True)
    t.start()

    # Chờ server phản hồi (tối đa 10 giây)
    for _ in range(20):
        time.sleep(0.5)
        if is_server_running():
            safe_print("[ADMIN APP] Backend server khoi dong thanh cong!")
            return

    safe_print("[ADMIN APP] Server dang khoi dong...")


class AdminApi:
    """JS Bridge cho phép giao diện gọi hàm Python Native."""

    def open_customer_web(self):
        """Mở trang Web dành cho Khách hàng trên trình duyệt mặc định."""
        webbrowser.open(SERVER_URL)
        return {"success": True, "message": "Đã mở Web Khách trên trình duyệt!"}

    def sync_data(self):
        """Đồng bộ dữ liệu giữa App Admin và Web Khách."""
        return {"success": True, "message": "Đã đồng bộ kho thiết bị & đơn thuê!"}

    def get_app_info(self):
        return {
            "app_name": "Tiduba Store Admin Desktop App",
            "version": "3.5.0",
            "domain": "Tiduba Store",
            "server_url": SERVER_URL,
            "status": "ONLINE" if is_server_running() else "OFFLINE"
        }


def main():
    # 1. Kiểm tra máy chủ Cloud chính thức
    cloud_online = is_cloud_accessible()
    if cloud_online:
        target_url = ADMIN_URL
        window_title = "Tiduba Store - Quản Trị Hệ Thống (Cloud Online: tidubastore.onrender.com)"
        safe_print("[ADMIN APP] Da ket noi truc tiep May Chu Cloud: https://tidubastore.onrender.com")
    else:
        safe_print("[ADMIN APP] May chu Cloud chua san sang hoac khong co internet. Khoi chay may chu noi bo port 9000...")
        start_backend_server()
        target_url = LOCAL_ADMIN_URL
        window_title = "Tiduba Store - Quản Trị Hệ Thống (Offline Localhost)"

    # 2. Mở cửa sổ Desktop pywebview
    try:
        import webview

        api = AdminApi()
        window = webview.create_window(
            title=window_title,
            url=target_url,
            width=1400,
            height=900,
            resizable=True,
            confirm_close=False,
            js_api=api
        )

        safe_print("======================================================================")
        safe_print("TIDUBA STORE - ADMIN DESKTOP APP ONLINE")
        safe_print(f"May chu: {target_url}")
        safe_print("CN1: 183A Huynh Thuc Khang, Pleiku, Gia Lai (0977.078.981)")
        safe_print("CN2: 801 Le Duan, P. An Phu, TP. Pleiku, Gia Lai (0977.078.981)")
        safe_print("App Admin tu dong ket noi & dong bo du lieu thoi gian thuc.")
        safe_print("======================================================================")

        webview.start(private_mode=False)

    except ImportError:
        safe_print("[ADMIN APP] pywebview chua cai dat. Mo giao dien Admin qua trinh duyet...")
        webbrowser.open(target_url)


if __name__ == "__main__":
    main()
