"""
TIDUBA STORE - EMAIL & SMTP NOTIFICATION SERVICE
Module gửi email thật (Gmail SMTP) phục vụ:
1. Gửi mã OTP xác minh tài khoản trực tiếp vào hộp thư đến Gmail của khách.
2. Gửi hóa đơn điện tử / xác nhận đơn thuê vào email khách.
3. Cung cấp API cấu hình Gmail SMTP (App Password) trực tiếp trong Bảng Quản Trị.
"""

import smtplib
import sqlite3
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, Tuple


def get_smtp_config(db_conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Lấy cấu hình SMTP Gmail từ bảng smtp_config trong database."""
    should_close = False
    if db_conn is None:
        from main import get_db
        db_conn = get_db()
        should_close = True

    try:
        cur = db_conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS smtp_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smtp_host TEXT NOT NULL DEFAULT 'smtp.gmail.com',
            smtp_port INTEGER NOT NULL DEFAULT 587,
            smtp_user TEXT DEFAULT '',
            smtp_password TEXT DEFAULT '',
            sender_name TEXT DEFAULT 'Tiduba Store',
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        """)
        db_conn.commit()

        cfg = cur.execute("SELECT * FROM smtp_config WHERE id = 1").fetchone()
        if not cfg:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
            INSERT INTO smtp_config (smtp_host, smtp_port, smtp_user, smtp_password, sender_name, is_active, updated_at)
            VALUES ('smtp.gmail.com', 587, '', '', 'Tiduba Store', 1, ?)
            """, (now_str,))
            db_conn.commit()
            cfg = cur.execute("SELECT * FROM smtp_config WHERE id = 1").fetchone()

        return dict(cfg)
    except Exception as e:
        print(f"[SMTP CONFIG ERROR] {e}")
        return {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "sender_name": "Tiduba Store",
            "is_active": 1
        }
    finally:
        if should_close:
            db_conn.close()


def send_otp_email(
    to_email: str,
    otp_code: str,
    customer_name: str = "Quý Khách",
    db_conn: Optional[sqlite3.Connection] = None
) -> Tuple[bool, str]:
    """
    Gửi thư điện tử thật chứa mã OTP 6 số vào hộp thư Gmail của người dùng.
    Sử dụng giao thức SMTP TLS chuẩn quốc tế.
    """
    to_email = (to_email or "").strip().lower()
    if not to_email or "@" not in to_email:
        return False, "Địa chỉ email nhận không hợp lệ!"

    cfg = get_smtp_config(db_conn)
    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    smtp_user = (cfg.get("smtp_user") or "").strip()
    smtp_pass = (cfg.get("smtp_password") or "").strip()
    sender_name = cfg.get("sender_name") or "Tiduba Store"

    # Nếu chưa cấu hình tài khoản Gmail gửi trong Admin
    if not smtp_user or not smtp_pass:
        return False, "Chưa thiết lập tài khoản Gmail gửi thư trong Bảng Quản Trị (Cần Gmail & Mật khẩu ứng dụng)!"

    # Soạn thảo Email HTML sang trọng, đẹp mắt
    subject = f"[{sender_name}] Mã OTP xác minh tài khoản: {otp_code}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6efe6; margin: 0; padding: 20px; color: #1c1917; }}
            .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.06); border: 1px solid #efe8df; }}
            .header {{ background: #1c1917; padding: 24px 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 24px; letter-spacing: 2px; font-family: 'Times New Roman', Georgia, serif; color: #ffffff; }}
            .header p {{ margin: 4px 0 0 0; font-size: 11px; color: #c86d51; text-transform: uppercase; letter-spacing: 1px; }}
            .content {{ padding: 30px 24px; }}
            .otp-box {{ background: #fdfaf6; border: 2px dashed #c86d51; border-radius: 16px; padding: 18px; text-align: center; margin: 24px 0; }}
            .otp-code {{ font-size: 32px; font-weight: 900; letter-spacing: 8px; color: #c86d51; font-family: 'Courier New', monospace; }}
            .warning {{ font-size: 12px; color: #78716c; line-height: 1.6; background: #fff7ed; padding: 12px 16px; border-radius: 12px; border-left: 4px solid #ea580c; }}
            .footer {{ background: #faf7f2; padding: 18px 24px; font-size: 11px; color: #a8a29e; text-align: center; border-top: 1px solid #efe8df; line-height: 1.6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TIDUBA STORE</h1>
                <p>Nền tảng cho thuê máy ảnh & trang phục chuyên nghiệp</p>
            </div>
            <div class="content">
                <p>Xin chào <strong>{customer_name}</strong>,</p>
                <p>Bạn (hoặc ai đó) vừa yêu cầu mã xác thực OTP để kích hoạt tài khoản hoặc xác minh giao dịch tại <strong>Tiduba Store</strong>.</p>
                
                <div class="otp-box">
                    <div style="font-size: 12px; color: #78716c; margin-bottom: 6px; font-weight: bold;">MÃ XÁC THỰC OTP CỦA BẠN:</div>
                    <div class="otp-code">{otp_code}</div>
                    <div style="font-size: 11px; color: #dc2626; margin-top: 6px;">Mã có hiệu lực trong vòng 5 phút</div>
                </div>

                <div class="warning">
                    ⚠️ <strong>LƯU Ý BẢO MẬT:</strong> Tuyệt đối không chia sẻ mã này cho bất kỳ ai. Nhân viên cửa hàng không bao giờ yêu cầu bạn cung cấp mã OTP.
                </div>
            </div>
            <div class="footer">
                <strong>HỆ THỐNG CỬA HÀNG TIDUBA STORE:</strong><br>
                📍 CN1: 183A Huỳnh Thúc Kháng, Pleiku, Gia Lai<br>
                📍 CN2: 801 Lê Duẩn, P. An Phú, TP. Pleiku, Gia Lai<br>
                📞 Hotline / Zalo: 0977.078.981
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{smtp_user}>"
    msg["To"] = to_email

    # Đính kèm nội dung text thuần và HTML
    text_fallback = f"Mã xác thực OTP của bạn tại Tiduba Store là: {otp_code} (Hiệu lực 5 phút). Không chia sẻ mã này cho người khác."
    msg.attach(MIMEText(text_fallback, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        return True, f"Đã gửi mã OTP thành công tới hộp thư Gmail: {to_email}"
    except smtplib.SMTPAuthenticationError as auth_err:
        return False, f"Lỗi xác thực Gmail: Sai tài khoản hoặc Mật khẩu ứng dụng (App Password). Chi tiết: {auth_err}"
    except Exception as e:
        return False, f"Lỗi gửi email qua máy chủ SMTP: {str(e)}"
