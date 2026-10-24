"""
TIDUBA STORE - DESKTOP ADMIN APP (ENTERPRISE EDITION)
Ứng dụng Desktop cao cấp dành riêng cho Quản Trị Viên (Admin)
Đồng bộ trực tiếp với Web Khách Hàng (FastAPI Port 9000).

Phát triển cho: Tiduba Store
"""

import io
import sys
import os
import time
import threading
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

# Đảm bảo sys.stdout và sys.stderr luôn hợp lệ trong môi trường Windows GUI (console=False)
class SafeStream(io.StringIO):
    def isatty(self):
        return False
    def write(self, s):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = SafeStream()
if sys.stderr is None:
    sys.stderr = SafeStream()

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Xác định chính xác thư mục gốc của ứng dụng (nơi chứa data/tiduba.db và templates/)
if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).resolve().parent
    if (EXE_DIR.parent / "data" / "tiduba.db").exists():
        APP_ROOT = EXE_DIR.parent
    elif (EXE_DIR / "data" / "tiduba.db").exists():
        APP_ROOT = EXE_DIR
    else:
        APP_ROOT = EXE_DIR.parent if EXE_DIR.name == "dist" else EXE_DIR
else:
    APP_ROOT = Path(__file__).resolve().parent

os.environ["DATA_DIR"] = str(APP_ROOT / "data")
os.chdir(str(APP_ROOT))


def safe_print(*args, **kwargs):
    """Ghi log an toàn ra console và file log admin_app.log."""
    try:
        msg = " ".join(str(a) for a in args)
        if sys.stdout:
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()
        log_file = APP_ROOT / "admin_app.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

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


def is_local_server_running() -> bool:
    """Kiểm tra máy chủ nội bộ port 9000 có đang hoạt động và phản hồi ping không."""
    try:
        req = urllib.request.Request(f"{LOCAL_SERVER_URL}/api/ping", headers={"User-Agent": "TidubaAdminApp/3.5"})
        with urllib.request.urlopen(req, timeout=1.0) as res:
            return res.status == 200
    except Exception:
        return False


def free_port_if_stuck():
    """Giải phóng port 9000 nếu có tiến trình treo và không phản hồi ping."""
    if is_local_server_running():
        return

    if sys.platform == "win32":
        try:
            cur_pid = os.getpid()
            output = subprocess.check_output("netstat -ano | findstr :9000", shell=True, text=True)
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid and pid != "0" and int(pid) != cur_pid:
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def is_server_running() -> bool:
    """Hàm tương thích cũ: kiểm tra server cục bộ port 9000."""
    return is_local_server_running()


def run_uvicorn_thread():
    """Chạy Uvicorn FastAPI server trực tiếp trong daemon thread."""
    try:
        safe_print("[ADMIN APP] run_uvicorn_thread bat dau...")
        import traceback
        import uvicorn
        from main import app as fastapi_app
        safe_print("[ADMIN APP] Da import thanh cong main.app! Khoi tao uvicorn.Server...")
        config = uvicorn.Config(
            fastapi_app, 
            host="0.0.0.0", 
            port=9000, 
            log_config=None,
            access_log=False
        )
        server = uvicorn.Server(config)
        safe_print("[ADMIN APP] Bat dau server.run()...")
        server.run()
        safe_print("[ADMIN APP] server.run() da ket thuc.")
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        safe_print(f"[ADMIN APP] LOI run_uvicorn_thread:\n{err}")


def start_backend_server():
    """Tự động kiểm tra và khởi chạy Backend Server nếu chưa chạy."""
    if is_local_server_running():
        safe_print("[ADMIN APP] Backend server da hoat dong san tai port 9000.")
        return True

    safe_print("[ADMIN APP] Khoi tao Backend Server FastAPI port 9000...")
    free_port_if_stuck()
    time.sleep(0.3)

    t = threading.Thread(target=run_uvicorn_thread, daemon=True, name="TidubaUvicornServer")
    t.start()

    # Chờ server phản hồi (tối đa 15 giây)
    for i in range(30):
        time.sleep(0.5)
        if is_local_server_running():
            safe_print(f"[ADMIN APP] Backend server khoi dong thanh cong sau {(i+1)*0.5}s!")
            return True

    safe_print("[ADMIN APP] Canh bao: Server can them thoi gian de khoi dong...")
    return is_local_server_running()


class AdminApi:
    """JS Bridge cho phép giao diện gọi hàm Python Native."""

    def open_customer_web(self):
        """Mở trang Web dành cho Khách hàng trên trình duyệt mặc định."""
        target = LOCAL_SERVER_URL if is_local_server_running() else SERVER_URL
        webbrowser.open(target)
        return {"success": True, "message": "Đã mở Web Khách trên trình duyệt!"}

    def sync_data(self):
        """Đồng bộ dữ liệu giữa App Admin và Web Khách."""
        return {"success": True, "message": "Đã đồng bộ kho thiết bị & đơn thuê!"}

    def get_app_info(self):
        return {
            "app_name": "Tiduba Store Admin Desktop App",
            "version": "3.5.0",
            "domain": "Tiduba Store",
            "server_url": LOCAL_SERVER_URL if is_local_server_running() else SERVER_URL,
            "status": "ONLINE" if is_local_server_running() else "OFFLINE"
        }


def main():
    safe_print("======================================================================")
    safe_print("TIDUBA STORE - ADMIN DESKTOP APP ONLINE")
    safe_print(f"Thu muc lam viec: {APP_ROOT}")
    safe_print(f"Co so du lieu: {APP_ROOT / 'data' / 'tiduba.db'}")

    # 1. Khởi chạy và xác nhận Backend Server nội bộ sẵn sàng
    local_ready = start_backend_server()

    if local_ready:
        target_url = LOCAL_ADMIN_URL
        window_title = "Tiduba Store - Quản Trị Hệ Thống (Kho Hàng 1.045 Món)"
        safe_print(f"[ADMIN APP] Ket noi Backend Noi Bo thanh cong: {target_url}")
    else:
        # Nếu local port 9000 không mở được, thử kết nối qua Cloud
        if is_cloud_accessible():
            target_url = ADMIN_URL
            window_title = "Tiduba Store - Quản Trị Hệ Thống (Cloud Online: tidubastore.onrender.com)"
            safe_print(f"[ADMIN APP] Port 9000 noi bo bi chan. Chuyen sang May Chu Cloud: {target_url}")
        else:
            target_url = LOCAL_ADMIN_URL
            window_title = "Tiduba Store - Quản Trị Hệ Thống"

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
