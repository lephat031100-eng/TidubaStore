"""
Unit & Integration Test Suite for Tiduba Store (Complete Core Architecture)
(tests/test_tiduba.py)
Principal AI Architecture - Quality & Reliability Verification
"""

import sys
import os
import time
import datetime
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

TIDUBA_ROOT = Path(__file__).resolve().parent.parent
if str(TIDUBA_ROOT) not in sys.path:
    sys.path.insert(0, str(TIDUBA_ROOT))

from main import (
    app,
    get_db,
    hash_password,
    create_token,
    generate_vietqr_url,
    calculate_rental_metrics,
    BANK_CONFIG
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_items_available():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE items SET availability = 'AVAILABLE'")
    conn.commit()
    conn.close()
    yield


def test_vietqr_url_generation():
    """Kiểm tra sinh link VietQR chuẩn MBBank STK 0123006101998."""
    qr_url = generate_vietqr_url(5000000, "TDB-889900")
    assert "MB" in qr_url
    assert "0123006101998" in qr_url
    assert "amount=5000000" in qr_url
    assert "accountName=KHONG+KY+DUYEN" in qr_url or "accountName=KHONG%20KY%20DUYEN" in qr_url
    assert "TDB-889900" in qr_url


def test_rental_metrics_calculation():
    """Kiểm tra tính toán số ngày thuê theo ca 4h/8h/24h và chiết khấu bậc thang."""
    start_time = "2026-10-01 08:00"
    end_time = "2026-10-03 08:00"
    price_4h = 150000
    price_8h = 250000
    price_24h = 350000

    rtype, hours, days, total_price, dt_s, dt_e = calculate_rental_metrics(
        start_time, end_time, price_4h, price_8h, price_24h
    )
    assert rtype == "24h"
    assert hours == 48.0
    assert days == 2.0
    # Thuê 2 ngày được chiết khấu 15% (350.000 * 2 * 0.85 = 595.000đ)
    assert total_price == 595000

    # Lỗi khi ngày trả trước ngày nhận
    with pytest.raises(ValueError):
        calculate_rental_metrics("2026-10-05 08:00", "2026-10-01 08:00", price_4h, price_8h, price_24h)


def test_get_items_catalog():
    """Kiểm tra API danh mục máy ảnh và trang phục."""
    res = client.get("/api/items")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 10
    
    categories = {i["category"] for i in data["items"]}
    assert "CAMERA_GEAR" in categories
    assert "COSTUME_FASHION" in categories

    names = [i["name"] for i in data["items"]]
    assert any("Sony" in n for n in names)
    assert any("Cổ Phục" in n for n in names)


def test_auth_login_admin_and_customer():
    """Kiểm tra đăng nhập tài khoản Admin và Khách hàng."""
    # 1. Login Admin
    res_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_adm.status_code == 200
    adm_data = res_adm.json()
    assert adm_data["success"] is True
    assert adm_data["user"]["role"] == "admin"
    assert "token" in adm_data

    # 2. Login Khách hàng
    res_cus = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    assert res_cus.status_code == 200
    cus_data = res_cus.json()
    assert cus_data["user"]["role"] == "customer"


def test_ekyc_and_blacklist_detection():
    """Kiểm tra cơ chế eKYC OCR + Liveness và kiểm tra Blacklist nội bộ."""
    # 1. Login khách hàng
    login_res = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test eKYC hợp lệ
    valid_ekyc = {
        "cccd_number": "079200008899",
        "full_name": "Nguyễn Văn Khách",
        "phone": "0987654321",
        "liveness_confirmed": True
    }
    ekyc_res = client.post("/api/ekyc/verify", json=valid_ekyc, headers=headers)
    assert ekyc_res.status_code == 200
    assert ekyc_res.json()["success"] is True
    assert ekyc_res.json()["liveness_passed"] is True

    # 3. Test người nằm trong Blacklist nội bộ (SĐT 0999888777)
    blacklisted_ekyc = {
        "cccd_number": "079200009999",
        "full_name": "Kẻ Gian Lận",
        "phone": "0999888777",
        "liveness_confirmed": True
    }
    bl_res = client.post("/api/ekyc/verify", json=blacklisted_ekyc, headers=headers)
    assert bl_res.status_code == 403
    assert "Blacklist" in bl_res.json()["detail"]


def test_booking_workflow_and_vietqr():
    """Kiểm tra quy trình đặt thuê máy ảnh, giữ kho 15 phút và sinh mã VietQR MBBank 0123006101998."""
    login_res = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    items_res = client.get("/api/items?category=CAMERA_GEAR")
    avail = [i for i in items_res.json()["items"] if i["availability"] == "AVAILABLE"]
    if not avail:
        conn = get_db()
        conn.execute("UPDATE items SET availability = 'AVAILABLE'")
        conn.commit()
        conn.close()
        items_res = client.get("/api/items?category=CAMERA_GEAR")
        avail = items_res.json()["items"]

    item = avail[0]

    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)
    booking_payload = {
        "item_id": item["id"],
        "start_time": now.strftime("%Y-%m-%d %H:%M"),
        "end_time": tomorrow.strftime("%Y-%m-%d %H:%M"),
        "customer_notes": "Test booking camera",
        "deposit_type": "ESCROW_100"
    }

    book_res = client.post("/api/rentals/book", json=booking_payload, headers=headers)
    assert book_res.status_code == 200
    b_data = book_res.json()
    assert b_data["success"] is True
    assert "TDB-" in b_data["rental_code"]
    assert b_data["hold_countdown_seconds"] == 900
    assert "0123006101998" in b_data["qr_image_url"]
    assert "MB" in b_data["qr_image_url"]


def test_contract_otp_signing():
    """Kiểm tra quy trình gửi mã OTP và ký số Hợp Đồng Điện Tử Bồi Thường 100%."""
    login_res = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    conn = get_db()
    rental = conn.execute("SELECT id FROM rentals WHERE user_id = ? LIMIT 1", (login_res.json()["user"]["id"],)).fetchone()
    conn.close()

    # 1. Gửi OTP
    otp_res = client.post(f"/api/rentals/{rental['id']}/send_contract_otp", headers=headers)
    assert otp_res.status_code == 200
    demo_otp = otp_res.json()["demo_otp_code"]

    # 2. Ký OTP
    sign_res = client.post(f"/api/rentals/{rental['id']}/sign_contract_otp", json={"otp": demo_otp}, headers=headers)
    assert sign_res.status_code == 200
    assert sign_res.json()["success"] is True

    # 3. Xem hợp đồng HTML
    contract_res = client.get(f"/api/rentals/{rental['id']}/contract", headers=headers)
    assert contract_res.status_code == 200
    html = contract_res.text
    assert "0123006101998" in html
    assert "MBBank" in html
    assert "ĐÃ KÝ SỐ QUA MÃ OTP CHÍNH CHỦ" in html


def test_payment_webhook_and_auto_print_queue():
    """Kiểm tra webhook ngân hàng SePAY/Casso tự động kích hoạt máy in nhiệt K80."""
    conn = get_db()
    rental = conn.execute("SELECT rental_code, total_price, deposit_paid FROM rentals LIMIT 1").fetchone()
    conn.close()

    webhook_payload = {
        "gateway": "SePAY / Casso / VietQR PRO",
        "account_no": "0123006101998",
        "amount": float(rental["total_price"] + rental["deposit_paid"]),
        "description": f"Thanh toan don hang {rental['rental_code']} qua MBBank",
        "transaction_id": f"TXN-MB-{int(time.time()*1000)}"
    }

    wh_res = client.post("/api/webhook/payment", json=webhook_payload)
    assert wh_res.status_code == 200
    data = wh_res.json()
    assert data["status"] == "PAYMENT_CONFIRMED_AUTO_PRINT_TRIGGERED"

    # Kiểm tra hàng đợi in (Print Queue) đã nhận lệnh in bill K80
    pq_res = client.get("/api/printer/pending_jobs", headers={"X-Printer-Secret": "PRINTER_LOCAL_SECRET_TIDUBA_2026"})
    assert pq_res.status_code == 200
    jobs = pq_res.json()["jobs"]
    assert len(jobs) >= 1
    assert "TIDUBA CAMERA & FASHION" in jobs[0]["bill_text"]
    assert "MBBANK 0123006101998" in jobs[0]["bill_text"]


def test_digital_handover_and_damage_assessment():
    """Kiểm tra Biên bản bàn giao số (chụp camera, chữ ký cảm ứng) & Trừ cọc chuẩn hóa."""
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    conn = get_db()
    cur = conn.cursor()
    rental = cur.execute("SELECT id FROM rentals LIMIT 1").fetchone()
    cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (rental["id"],))
    conn.commit()
    conn.close()

    # 1. Ký biên bản bàn giao Checkout
    handover_payload = {
        "rental_id": rental["id"],
        "phase": "CHECKOUT",
        "sensor_clean": True,
        "lens_scratchless": True,
        "shutter_count": 4200,
        "camera_front_img": "https://example.com/front.jpg",
        "camera_lens_img": "https://example.com/lens.jpg",
        "camera_sensor_img": "https://example.com/sensor.jpg",
        "costume_details_img": "https://example.com/dress.jpg",
        "accessories_included": "Body, Lens, 2 Pin, Sac, The 128GB",
        "staff_signature_svg": "[Sig: Le Nhat Phat]",
        "customer_signature_svg": "[Sig: Nguyen Van Khach]",
        "notes": "Kiểm tra tại quầy sạch 100%"
    }
    ho_res = client.post("/api/handover/submit", json=handover_payload, headers=admin_headers)
    assert ho_res.status_code == 200
    assert ho_res.json()["success"] is True

    # 2. Ghi nhận trừ cọc chuẩn hóa (Ví dụ: khách làm bẩn trang phục cần giặt hấp)
    damage_payload = {
        "rental_id": rental["id"],
        "damage_code": "DIRTY_FABRIC",
        "damage_title": "Bẩn trang phục cần giặt hấp chuyên sâu",
        "penalty_amount": 150000,
        "notes": "Trang phục dính vết bùn ngoại cảnh"
    }
    dmg_res = client.post("/api/qc/add_damage_penalty", json=damage_payload, headers=admin_headers)
    assert dmg_res.status_code == 200

    # 3. Nghiệm thu hoàn tất và kích hoạt hoàn cọc
    refund_res = client.post(f"/api/qc/complete_refund/{rental['id']}", headers=admin_headers)
    assert refund_res.status_code == 200
    assert refund_res.json()["success"] is True
    assert refund_res.json()["damage_deduction"] >= 150000


def test_legal_overdue_dossier():
    """Kiểm tra xuất Hồ Sơ Pháp Lý Vi Phạm 24h kèm CCCD và đối chứng."""
    conn = get_db()
    rental = conn.execute("SELECT id FROM rentals LIMIT 1").fetchone()
    conn.close()

    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {login_res.json()['token']}"}
    res = client.get(f"/api/rentals/{rental['id']}/legal_dossier", headers=admin_headers)
    assert res.status_code == 200
    html = res.text
    assert "ĐƠN TRÌNH BÁO VI PHẠM CHIẾM ĐOẠT TÀI SẢN THUÊ QUÁ HẠN 24 GIỜ" in html
    assert "MBBank 0123006101998 (KHONG KY DUYEN)" in html
    assert "LÊ NHẬT PHÁT" in html


def test_coupon_engine_and_barcode_label():
    """Kiểm tra động cơ áp dụng mã giảm giá Coupon & In tem mã vạch K80."""
    # 1. Test coupon TIDUBA50K
    res_c1 = client.post("/api/coupons/apply", json={"code": "TIDUBA50K", "order_amount": 500000})
    assert res_c1.status_code == 200
    c1_data = res_c1.json()
    assert c1_data["success"] is True
    assert c1_data["discount_amount"] == 50000
    assert c1_data["final_amount"] == 450000

    # 2. Test coupon phần trăm VIP10 (10%)
    res_c2 = client.post("/api/coupons/apply", json={"code": "VIP10", "order_amount": 1000000})
    assert res_c2.status_code == 200
    assert res_c2.json()["discount_amount"] == 100000

    # 3. Test coupon không tồn tại
    res_err = client.post("/api/coupons/apply", json={"code": "INVALID_CODE", "order_amount": 500000})
    assert res_err.status_code == 400

    # 4. Test in tem mã vạch Barcode K80
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}

    conn = get_db()
    rental = conn.execute("SELECT id FROM rentals LIMIT 1").fetchone()
    conn.close()

    res_label = client.get(f"/api/admin/rentals/{rental['id']}/label", headers=admin_headers)
    assert res_label.status_code == 200
    assert "TIDUBA STORE - THIẾT BỊ CHO THUÊ" in res_label.text
    assert "NIÊM PHONG THIẾT BỊ" in res_label.text


def test_custom_deposit_and_admin_confirm_payment_and_zalo():
    """Test các tính năng mới yêu cầu: tự nhập tiền cọc, admin xác nhận thanh toán, Zalo notification."""
    # 1. Đăng nhập khách
    login_cus = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    cus_headers = {"Authorization": f"Bearer {login_cus.json()['token']}"}

    # 2. Đặt đơn với tiền cọc TỰ NHẬP (VD: 1.500.000đ)
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)
    items_res = client.get("/api/items")
    avail = [i for i in items_res.json()["items"] if i["availability"] == "AVAILABLE"]
    item_id = avail[0]["id"]

    booking_payload = {
        "item_id": item_id,
        "start_time": now.strftime("%Y-%m-%d %H:%M"),
        "end_time": tomorrow.strftime("%Y-%m-%d %H:%M"),
        "custom_deposit_amount": 1500000,
        "customer_notes": "Test tự nhập cọc 1.5tr"
    }

    book_res = client.post("/api/rentals/book", json=booking_payload, headers=cus_headers)
    assert book_res.status_code == 200
    b_data = book_res.json()
    assert b_data["deposit_amount"] == 1500000
    rental_id = b_data["rental_id"]

    # 3. Đăng nhập Admin & bấm Xác Nhận Đã Nhận Tiền
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}

    confirm_res = client.post(f"/api/admin/rentals/{rental_id}/confirm_payment", headers=adm_headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["success"] is True

    # 4. Kiểm tra Zalo config API
    zalo_cfg_res = client.get("/api/admin/zalo/config", headers=adm_headers)
    assert zalo_cfg_res.status_code == 200

    zalo_save_res = client.post("/api/admin/zalo/config", json={"admin_phone": "0987654321", "is_active": 1}, headers=adm_headers)
    assert zalo_save_res.status_code == 200

    zalo_logs_res = client.get("/api/admin/zalo/logs", headers=adm_headers)
    assert zalo_logs_res.status_code == 200
    assert len(zalo_logs_res.json()["logs"]) >= 1


def test_anonymous_user_protected_api_deny():
    """Anonymous user -> protected API = DENY"""
    res = client.get("/api/rentals/my")
    assert res.status_code == 401

def test_customer_accessing_admin_api_deny():
    """Customer -> Admin API = DENY"""
    login_cus = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    cus_headers = {"Authorization": f"Bearer {login_cus.json()['token']}"}
    res = client.get("/api/admin/dashboard_stats", headers=cus_headers)
    assert res.status_code == 403

def test_idor_rental_contract_deny():
    """Customer A -> resource của Customer B = DENY"""
    # 1. Login Customer A (khachhang)
    login_a = client.post("/api/auth/login", json={"username": "khachhang", "password": "123456"})
    token_a = login_a.json()['token']
    
    # 2. Tạo User B và Login (không dùng số điện thoại/CCCD trong blacklist)
    uname_b = f"customer_b_{int(time.time()*1000)}"
    client.post("/api/auth/register", json={
        "username": uname_b, "password": "password_b", "email": f"{uname_b}@example.com",
        "full_name": "Customer B", "phone": "0912345678", "cccd_number": "123456789012"
    })
    login_b = client.post("/api/auth/login", json={"username": uname_b, "password": "password_b"})
    token_b = login_b.json()['token']
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 3. User B tạo 1 rental
    book_res = client.post("/api/rentals/book", json={
        "item_id": 1, "start_time": "2026-10-10 10:00", "end_time": "2026-10-11 10:00"
    }, headers=headers_b)
    rental_id = book_res.json()["rental_id"]
    
    # 4. User A cố gắng truy cập hợp đồng của User B
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res = client.get(f"/api/rentals/{rental_id}/contract", headers=headers_a)
    assert res.status_code == 403

def test_admin_accessing_admin_api_allow():
    """Admin -> authorized admin API = ALLOW"""
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}
    res = client.get("/api/admin/dashboard_stats", headers=adm_headers)
    assert res.status_code == 200

def test_webhook_missing_signature_deny():
    """Payment webhook không có/không hợp lệ signature = DENY"""
    res = client.post("/api/webhook/payment", json={"gateway": "SePAY", "amount": 1000}, headers={"X-Webhook-Token": "INVALID_TOKEN"})
    assert res.status_code == 401

def test_duplicate_refund_prevented():
    """Duplicate request không được tạo duplicate transaction hoặc double refund"""
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}
    
    # Get a rental
    conn = get_db()
    cur = conn.cursor()
    r = cur.execute("SELECT id FROM rentals LIMIT 1").fetchone()
    cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (r["id"],))
    conn.commit()
    conn.close()
    
    # Refund 1st time
    res1 = client.post(f"/api/qc/complete_refund/{r['id']}", headers=adm_headers)
    assert res1.status_code == 200
    assert res1.json()["success"] is True
    
    # Refund 2nd time should be stopped
    res2 = client.post(f"/api/qc/complete_refund/{r['id']}", headers=adm_headers)
    assert res2.json()["success"] == False
    assert "nghiệm thu và hoàn tiền trước đó" in res2.json()["message"]


def test_track_order_by_phone():
    """Tra cứu đơn hàng bằng số điện thoại khách hàng (Phone lookup)."""
    res = client.get("/api/rentals/track/0987654321")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["type"] == "PHONE_LOOKUP"
    assert len(data["rentals"]) >= 1


def test_admin_blacklist_crud():
    """Admin quản lý danh sách đen (thêm/xóa đối tượng bị chặn)."""
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}

    # Thêm vào blacklist
    add_res = client.post("/api/admin/blacklist", json={
        "phone": "0988776655", "cccd_number": "079200999888", "reason": "Thử nghiệm blacklist"
    }, headers=adm_headers)
    assert add_res.status_code == 200
    assert add_res.json()["success"] is True

    # Lấy danh sách blacklist
    get_res = client.get("/api/admin/blacklist", headers=adm_headers)
    assert get_res.status_code == 200
    items = [b for b in get_res.json()["blacklist"] if b["phone"] == "0988776655"]
    assert len(items) == 1
    bl_id = items[0]["id"]

    # Xóa khỏi blacklist
    del_res = client.delete(f"/api/admin/blacklist/{bl_id}", headers=adm_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_export_csv_report():
    """Admin xuất file báo cáo doanh thu & đơn thuê dạng CSV chuẩn."""
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_adm.json()["token"]

    # Thử qua query parameter ?token=
    res = client.get(f"/api/admin/reports/export_csv?token={token}")
    assert res.status_code == 200
    assert "Mã Đơn" in res.text
    assert "Tiền Thuê" in res.text


def test_rental_refund_qr():
    """Admin lấy thông tin và mã VietQR hoàn cọc cho khách."""
    login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_headers = {"Authorization": f"Bearer {login_adm.json()['token']}"}

    conn = get_db()
    r = conn.execute("SELECT id FROM rentals LIMIT 1").fetchone()
    conn.close()

    res = client.get(f"/api/admin/rentals/{r['id']}/refund_qr", headers=adm_headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "refund_amount" in res.json()
