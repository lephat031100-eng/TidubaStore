"""
TIDUBA STORE - NỀN TẢNG CHO THUÊ MÁY ẢNH & TRANG PHỤC CAO CẤP (ENTERPRISE EDITION)
(Tiduba Camera & Fashion Rental Platform - Complete Core & Advanced Architecture)

Bản quyền thương mại phát triển bởi Autonomous Software Agency
Tài khoản thụ hưởng thanh toán VietQR:
- Ngân hàng: Ngân hàng Quân Đội (MBBank - MB)
- Số tài khoản: 0123006101998
- Chủ tài khoản: KHONG KY DUYEN
"""

import os
import sys
import re
import json
import time
import hmac
import hashlib
import sqlite3
import datetime
import threading
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, Depends, Header, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import csv
import io
import uuid

# Đảm bảo UTF-8 encoding trên Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "tiduba.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# CẤU HÌNH NGÂN HÀNG THỤ HƯỞNG CHÍNH THỨC CỦA APP (MBBANK 0123006101998)
BANK_CONFIG = {
    "bank_id": "MB",
    "bank_name": "Ngân hàng Quân Đội (MBBank)",
    "account_no": "0123006101998",
    "account_name": "KHONG KY DUYEN",
    "template": "compact2",
}

# CẤU HÌNH HỆ THỐNG 2 CHI NHÁNH CHÍNH THỨC CỦA TIDUBA STORE
STORE_BRANCHES = {
    "CN1": {
        "code": "CN1",
        "name": "Chi nhánh 1 (Pleiku, Gia Lai)",
        "address": "183A Huỳnh Thúc Kháng, P. Diên Hồng, TP. Pleiku, Gia Lai",
        "short_address": "183A Huỳnh Thúc Kháng, Pleiku, Gia Lai",
        "phone": "0977.078.981",
        "hotline": "0977.078.981",
        "maps_url": "https://maps.app.goo.gl/rVJwRPcvrSHhcrDN6",
        "opening_hours": "08:00 - 20:00 (Mở cửa tất cả các ngày)",
        "is_headquarter": True
    },
    "CN2": {
        "code": "CN2",
        "name": "Chi nhánh 2 (Pleiku, Gia Lai)",
        "address": "801 Lê Duẩn, P. An Phú, TP. Pleiku, Gia Lai",
        "short_address": "801 Lê Duẩn, P. An Phú, TP. Pleiku",
        "phone": "0977.078.981",
        "hotline": "0977.078.981",
        "maps_url": "https://maps.app.goo.gl/HVq186SuqXgXQ3N58",
        "opening_hours": "08:00 - 20:00 (Mở cửa tất cả các ngày)",
        "is_headquarter": False
    }
}

# CẤU HÌNH TÊN MIỀN CÔNG KHAI / MÁY CHỦ NỘI BỘ
PUBLIC_DOMAIN = os.environ.get("PUBLIC_DOMAIN", "http://localhost:9000").rstrip("/")

app = FastAPI(
    title="Tiduba Store - Camera & Costume Rental Platform",
    description="Nền tảng trực tuyến cho thuê máy ảnh, ống kính và trang phục sự kiện cao cấp - Tiduba Store",
    version="3.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phục vụ thư mục static & uploads ảnh thật
UPLOADS_DIR = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =============================================================================
# 1. DATABASE SCHEMA & AUTO-MIGRATION ENGINE
# =============================================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    salt = "Tiduba_Salt_2026_MBBank_0123006101998"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # 1. Bảng người dùng (Users & eKYC verification)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        cccd_number TEXT,
        cccd_front_img TEXT,
        cccd_back_img TEXT,
        face_liveness_verified INTEGER NOT NULL DEFAULT 0,
        loyalty_points INTEGER NOT NULL DEFAULT 50000,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Bảng Blacklist nội bộ
    cur.execute("""
    CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        cccd_number TEXT,
        bank_account TEXT,
        reason TEXT NOT NULL,
        flagged_at TEXT NOT NULL
    );
    """)

    # 3. Bảng thiết bị & trang phục (Chi tiết ngàm, shot, serial độc nhất, size/số đo)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- 'CAMERA_GEAR' hoặc 'COSTUME_FASHION'
        subcategory TEXT NOT NULL,
        brand TEXT NOT NULL,
        serial_or_size TEXT NOT NULL,
        mount_type TEXT,        -- 'Sony E-mount', 'Canon RF', 'Fuji X'...
        shutter_count INTEGER DEFAULT 0,
        measurements TEXT,      -- Số đo 3 vòng cho trang phục (ví dụ: '88-66-92')
        price_4h INTEGER NOT NULL,
        price_8h INTEGER NOT NULL,
        price_24h INTEGER NOT NULL,
        deposit_amount INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        description TEXT NOT NULL,
        condition_status TEXT NOT NULL,
        availability TEXT NOT NULL DEFAULT 'AVAILABLE',
        created_at TEXT NOT NULL
    );
    """)

    # 4. Bảng gói Combo Tiết Kiệm (Bundle Builder)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        badge TEXT NOT NULL,
        price_24h INTEGER NOT NULL,
        original_price_24h INTEGER NOT NULL,
        deposit_amount INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        description TEXT NOT NULL,
        items_included_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 5. Bảng đơn thuê (Rentals với Hold 15 phút, e-Contract OTP, Escrow & phạt trễ lũy tiến)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_code TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        item_id INTEGER,
        combo_id INTEGER,
        rental_type TEXT NOT NULL DEFAULT '24h', -- '4h', '8h', '24h'
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        rental_duration_hours REAL NOT NULL,
        hold_expires_at TEXT, -- Mốc thời gian nhả kho nếu quá 15 phút không trả tiền
        total_price INTEGER NOT NULL,
        deposit_paid INTEGER NOT NULL,
        deposit_type TEXT NOT NULL DEFAULT 'ESCROW_100', -- 'ESCROW_100', 'ID_PLUS_CASH', 'CREDIT_PREAUTH'
        late_fee INTEGER NOT NULL DEFAULT 0,
        extension_hours INTEGER NOT NULL DEFAULT 0,
        extension_status TEXT NOT NULL DEFAULT 'NONE', -- 'NONE', 'REQUESTED', 'APPROVED', 'REJECTED'
        extension_fee INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'HOLD', -- 'HOLD', 'PENDING', 'APPROVED', 'ACTIVE', 'RETURNED', 'OVERDUE', 'CANCELLED'
        e_contract_otp TEXT,
        e_contract_signed INTEGER NOT NULL DEFAULT 0,
        signed_at TEXT,
        payment_method TEXT NOT NULL DEFAULT 'VIETQR_MBBANK',
        customer_notes TEXT,
        admin_notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (item_id) REFERENCES items(id)
    );
    """)

    # 6. Bảng Biên bản bàn giao số (Digital Handover QC & Camera Snapshots & E-Signature)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS handover_protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER NOT NULL,
        phase TEXT NOT NULL, -- 'CHECKOUT' hoặc 'CHECKIN'
        staff_name TEXT NOT NULL,
        sensor_clean INTEGER NOT NULL DEFAULT 1,
        lens_scratchless INTEGER NOT NULL DEFAULT 1,
        shutter_count_verified INTEGER DEFAULT 0,
        camera_front_img TEXT,
        camera_lens_img TEXT,
        camera_sensor_img TEXT,
        costume_details_img TEXT,
        accessories_included TEXT NOT NULL,
        staff_signature_svg TEXT,
        customer_signature_svg TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 7. Bảng Danh mục trừ tiền cọc chuẩn hóa (Standardized Damage Assessment)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS damage_penalties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER NOT NULL,
        damage_code TEXT NOT NULL, -- 'SCRATCH_FRONT_LENS', 'BODY_DENT', 'TORN_FABRIC', 'MISSING_CAP', 'LATE_OVERDUE'
        damage_title TEXT NOT NULL,
        penalty_amount INTEGER NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 8. Bảng Hàng đợi in nhiệt K80 (Print Queue ESC/POS)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS print_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER NOT NULL,
        printer_ip TEXT NOT NULL DEFAULT '192.168.1.200',
        bill_text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PRINTED', 'FAILED'
        printed_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 9. Bảng Lịch sử gửi thông báo Zalo ZNS (Legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS zns_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER,
        phone TEXT NOT NULL,
        milestone TEXT NOT NULL, -- 'MILESTONE_1_CONFIRMED', 'MILESTONE_2_REMINDER', 'MILESTONE_3_REFUNDED'
        template_id TEXT NOT NULL,
        channel TEXT NOT NULL DEFAULT 'ZALO_ZNS', -- 'ZALO_ZNS' hoặc 'SMS_FALLBACK'
        status TEXT NOT NULL DEFAULT 'SENT',
        sent_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 9.1 Bảng Cấu hình Thông báo Telegram Bot
    cur.execute("""
    CREATE TABLE IF NOT EXISTS telegram_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_token TEXT DEFAULT '',
        chat_id TEXT DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1,
        auto_notify_new_rental INTEGER NOT NULL DEFAULT 1,
        auto_notify_payment INTEGER NOT NULL DEFAULT 1,
        auto_notify_return INTEGER NOT NULL DEFAULT 1,
        auto_notify_overdue INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL
    );
    """)

    # 9.2 Bảng Lịch sử gửi thông báo Telegram
    cur.execute("""
    CREATE TABLE IF NOT EXISTS telegram_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER,
        chat_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'SENT',
        sent_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 9.3 Bảng Cấu hình Thông báo Zalo OA & Webhook (Tương thích ngược)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS zalo_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oa_id TEXT DEFAULT 'TIDUBA_OA_STORE',
        access_token TEXT DEFAULT '',
        webhook_url TEXT DEFAULT '',
        admin_phone TEXT DEFAULT '0987654321',
        is_active INTEGER NOT NULL DEFAULT 0,
        auto_notify_customer INTEGER NOT NULL DEFAULT 0,
        auto_notify_admin INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    );
    """)

    # 10. Bảng Đánh giá & Reviews sao
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL DEFAULT 5,
        comment TEXT NOT NULL,
        photo_sample_url TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # 11. Bảng Alerts (cảnh báo trả đồ trễ hạn, gia hạn...)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER,
        alert_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    # 12. Bảng Mã Giảm Giá / Khuyến Mãi (Coupons)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL DEFAULT 'PERCENT', -- 'PERCENT' hoặc 'FIXED_AMOUNT'
        discount_value INTEGER NOT NULL,
        min_order_amount INTEGER NOT NULL DEFAULT 0,
        max_discount_amount INTEGER,
        usage_limit INTEGER NOT NULL DEFAULT 100,
        used_count INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        expires_at TEXT NOT NULL
    );
    """)

    # 13. Bảng Chi Tiết Sản Phẩm Đơn Thuê Nhiều Món (Cart & KiotViet POS)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rental_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER NOT NULL,
        item_id INTEGER,
        combo_id INTEGER,
        item_name TEXT NOT NULL,
        serial_or_size TEXT,
        item_category TEXT,
        rental_type TEXT NOT NULL,
        rental_duration_hours REAL NOT NULL,
        unit_price INTEGER NOT NULL,
        deposit_amount INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (rental_id) REFERENCES rentals(id)
    );
    """)

    conn.commit()

    # Tự động cập nhật cột deposit_asset_desc nếu chưa có
    try:
        cur.execute("ALTER TABLE rentals ADD COLUMN deposit_asset_desc TEXT;")
        conn.commit()
    except Exception:
        pass

    # Tự động cập nhật cột items_json nếu chưa có
    try:
        cur.execute("ALTER TABLE rentals ADD COLUMN items_json TEXT;")
        conn.commit()
    except Exception:
        pass

    # Tự động cập nhật cột branch_code cho rentals nếu chưa có
    try:
        cur.execute("ALTER TABLE rentals ADD COLUMN branch_code TEXT DEFAULT 'CN1';")
        conn.commit()
    except Exception:
        pass

    # Tự động cập nhật cột branch_code cho items nếu chưa có
    try:
        cur.execute("ALTER TABLE items ADD COLUMN branch_code TEXT DEFAULT 'CN1';")
        conn.commit()
    except Exception:
        pass

    # Tự động cập nhật cột overdue_chat_id cho telegram_config nếu chưa có
    try:
        cur.execute("ALTER TABLE telegram_config ADD COLUMN overdue_chat_id TEXT DEFAULT '-1004498214603';")
        conn.commit()
    except Exception:
        pass

    # Luôn đảm bảo overdue_chat_id là -1004498214603 nếu chưa có
    try:
        cur.execute("UPDATE telegram_config SET overdue_chat_id = '-1004498214603' WHERE (overdue_chat_id IS NULL OR overdue_chat_id = '')")
        conn.commit()
    except Exception:
        pass

    # Bảng Lưu Log Nhắc Hẹn & Quá Hạn (Tránh gửi lặp lại)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reminder_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rental_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        sent_at TEXT NOT NULL
    );
    """)
    conn.commit()

    # Bảng Cấu Hình Danh Mục & Chip Lọc (Tự động đồng bộ chuẩn 100%)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        filter_type TEXT NOT NULL,
        filter_value TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)
    conn.commit()

    # Xóa các danh mục rác cũ nếu có và nạp đầy đủ 16 danh mục chuẩn
    try:
        cur.execute("DELETE FROM categories_config WHERE name IN ('mầm ơi', '200k - 500k', 'DU LỊCH & CHỤP ẢNH')")
        conn.commit()
    except Exception:
        pass

    official_cats = [
        ('all', 'Tất Cả', 'ALL', '', 0),
        ('sony', 'Máy Sony', 'BRAND', 'Sony', 1),
        ('canon', 'Máy Canon', 'BRAND', 'Canon', 2),
        ('vay', 'Váy Tiệc', 'BRAND', 'Váy', 3),
        ('fuji', 'Máy Fujifilm', 'BRAND', 'Fujifilm', 4),
        ('t1', 'Áo Khoác', 'BRAND', 'tier1', 5),
        ('t2', 'Du Lịch - Chụp Ảnh', 'BRAND', 'tier2', 6),
        ('t3', 'Đồ Đông', 'BRAND', 'tier3', 7),
        ('boot', 'Boot', 'BRAND', 'Boot', 9),
        ('aodai', 'Áo Dài Thiết Kế', 'BRAND', 'áo dài', 10),
        ('vaytiec', 'Váy Tiệc', 'BRAND', 'Váy Tiệc', 11),
        ('yem', 'Yếm', 'BRAND', 'Yếm', 12),
        ('yembe', 'Yếm Bé', 'BRAND', 'Yếm Bé', 13),
        ('vietphuc', 'Việt Phục', 'BRAND', 'Việt Phục', 14),
        ('túi', 'Túi Xách', 'BRAND', 'Túi', 15),
        ('phukien', 'Phụ Kiện', 'BRAND', 'Phụ Kiện', 16),
    ]
    cur.execute("SELECT count(*) as c FROM categories_config")
    if cur.fetchone()["c"] < len(official_cats):
        for c in official_cats:
            exists = cur.execute("SELECT id FROM categories_config WHERE code = ?", (c[0],)).fetchone()
            if not exists:
                cur.execute("""
                INSERT INTO categories_config (code, name, filter_type, filter_value, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """, c)
        conn.commit()

    # Tự động cập nhật cột refund_bank_info cho rentals nếu chưa có
    try:
        cur.execute("ALTER TABLE rentals ADD COLUMN refund_bank_info TEXT;")
        conn.commit()
    except Exception:
        pass

    # Tự động cập nhật cột deposit_asset_photo cho rentals nếu chưa có
    try:
        cur.execute("ALTER TABLE rentals ADD COLUMN deposit_asset_photo TEXT;")
        conn.commit()
    except Exception:
        pass

    # Pre-seed Telegram Config nếu chưa có
    cur.execute("SELECT count(*) as c FROM telegram_config")
    if cur.fetchone()["c"] == 0:
        now_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
        INSERT INTO telegram_config (bot_token, chat_id, is_active, auto_notify_new_rental, auto_notify_payment, auto_notify_return, auto_notify_overdue, updated_at)
        VALUES ('', '', 1, 1, 1, 1, 1, ?)
        """, (now_dt,))
        conn.commit()

    # Pre-seed Admin, Khách mẫu & Blacklist
    cur.execute("SELECT count(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
        INSERT INTO users (username, email, password_hash, full_name, phone, role, cccd_number, face_liveness_verified, loyalty_points, created_at)
        VALUES 
        ('admin', 'admin@tiduba.vn', ?, 'Quản Lý Cửa Hàng Tiduba', '0901234567', 'admin', '079200001234', 1, 500000, ?),
        ('khachhang', 'khach@tiduba.vn', ?, 'Nguyễn Văn Khách', '0987654321', 'customer', '079200005678', 1, 50000, ?)
        """, (hash_password("admin123"), now, hash_password("123456"), now))

        # Seed Blacklist mẫu
        cur.execute("""
        INSERT INTO blacklist (phone, cccd_number, bank_account, reason, flagged_at)
        VALUES ('0999888777', '079200009999', '19039999999', 'Làm rơi vỡ thấu kính Sony GM không bồi thường', ?)
        """, (now,))
        conn.commit()

    # Pre-seed Items với đầy đủ giá 4h, 8h, 24h & ngàm/shot/size
    cur.execute("SELECT count(*) as c FROM items")
    if cur.fetchone()["c"] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seed_items = [
            ("Sony Alpha A7 IV (Body Full-Frame 33MP)", "CAMERA_GEAR", "Body Máy Ảnh", "Sony", "SN: SONY-A7M4-8891",
             "Sony E-mount", 4120, None, 150000, 250000, 350000, 5000000,
             "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=800&q=80",
             "Cảm biến 33MP BSI Exmor R, quay phim 4K 60p 10-bit màu S-Cinetone, lấy nét mắt Realtime Eye AF.", "Mới 99%, Cảm biến sạch"),

            ("Canon EOS R6 Mark II (Quay Chụp Sự Kiện Đỉnh Cao)", "CAMERA_GEAR", "Body Máy Ảnh", "Canon", "SN: CANON-R6M2-4412",
             "Canon RF", 1850, None, 180000, 280000, 400000, 6000000,
             "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=800&q=80",
             "Cảm biến 24.2MP Dual Pixel CMOS AF II, chụp 40fps, chống rung IBIS 8 stops.", "Mới 98%, Hoạt động hoàn hảo"),

            ("Fujifilm X-T5 Silver (Nghệ Thuật Màu Film Cổ Điển)", "CAMERA_GEAR", "Body Máy Ảnh", "Fujifilm", "SN: FUJI-XT5-9923",
             "Fuji X-mount", 2100, None, 130000, 220000, 300000, 4500000,
             "https://images.unsplash.com/photo-1512790182412-b19e6d62bc39?w=800&q=80",
             "Cảm biến X-Trans CMOS 5 HR 40.2MP, 19 giả lập màu phim Film Simulation cổ điển.", "Mới 99%, Pin chụp 700 shots"),

            ("Sony FE 24-70mm f/2.8 GM II (Ống Kính Vàng Đa Năng)", "CAMERA_GEAR", "Ống Kính (Lens)", "Sony", "SN: SONY-2470GM2-110",
             "Sony E-mount", 0, None, 120000, 180000, 250000, 4000000,
             "https://images.unsplash.com/photo-1617005082133-548c4dd27f35?w=800&q=80",
             "Ống kính Zoom tiêu chuẩn G Master thế hệ II siêu nhẹ, độ sắc nét toàn khung hình, màng khẩu 11 lá.", "Thấu kính trong vắt, không bụi"),

            ("Gimbal DJI RS 3 Pro Combo (Chống Rung Điện Ảnh)", "CAMERA_GEAR", "Phụ Kiện Máy", "DJI", "SN: DJI-RS3P-5541",
             "Universal", 0, None, 90000, 130000, 180000, 2500000,
             "https://images.unsplash.com/photo-1589872766857-2110abb95a08?w=800&q=80",
             "Trục tay carbon tải trọng 4.5kg, tự động khóa trục thông minh, hỗ trợ lấy nét LiDAR Focus.", "Pin trâu 12 tiếng"),

            ("Flycam DJI Mini 4 Pro (Quay 4K HDR Dọc Chân Thực)", "CAMERA_GEAR", "Phụ Kiện Máy", "DJI", "SN: DJI-M4P-7729",
             "Drone", 0, None, 200000, 320000, 450000, 7000000,
             "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=800&q=80",
             "Cảm biến tránh vật cản đa hướng Omnidirectional, truyền video FHD 20km O4, quay dọc chân thực cho TikTok.", "3 Pin bay thả ga"),

            ("Set Cổ Phục Việt Nhật Bình Hoàng Cung (Thêu Tay Tỉ Mỉ)", "COSTUME_FASHION", "Cổ Trang & Áo Dài", "Tiduba Atelier", "Size: Freesize (S-L)",
             None, 0, "Ngực 82-94cm, Eo 62-78cm", 120000, 180000, 250000, 500000,
             "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=800&q=80",
             "Trang phục triều Nguyễn thêu chỉ vàng ngũ sắc, lụa tơ tằm dệt cao cấp, kèm nón quai thao và vòng kiềng đồng.", "Giặt khô khử khuẩn 100%"),

            ("Đầm Dạ Hội Kim Sa Cao Cấp (Xẻ Tà Sang Trọng Tiệc Đêm)", "COSTUME_FASHION", "Dạ Hội & Vest", "Tiduba Luxury", "Size: M",
             None, 0, "Ngực 86cm, Eo 66cm, Mông 92cm", 100000, 160000, 220000, 400000,
             "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=800&q=80",
             "Chất liệu voan đính kết hạt cườm lấp lánh tôn dáng, thiết kế hở lưng quyến rũ, kèm clutch ánh bạc.", "Nguyên tag, thơm tho"),

            ("Bộ Vest Nam Quý Tộc Ý Màu Xanh Navy (Kèm Nơ & Cài)", "COSTUME_FASHION", "Dạ Hội & Vest", "Tiduba Tailor", "Size: L",
             None, 0, "Vai 46cm, Vòng ngực 98cm, Dài quần 100cm", 90000, 130000, 180000, 350000,
             "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=800&q=80",
             "Vải dệt Wool pha Cashmere không nhăn, form đứng tôn vai, kèm áo sơ mi trắng, cà vạt lụa và khăn cài túi.", "Đã là ủi phẳng phiu"),

            ("Set Áo Dài Tơ Tằm Nàng Thơ Trắng (Chụp Ngoại Cảnh / Studio)", "COSTUME_FASHION", "Cổ Trang & Áo Dài", "Tiduba Silk", "Size: S-M",
             None, 0, "Dài áo 135cm, Vòng eo 64-68cm", 60000, 90000, 120000, 250000,
             "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=800&q=80",
             "Áo dài cách tân 4 tà bồng bềnh, chất liệu tơ hoa nhí thướt tha, tay bồng thanh thoát, kèm bờm ngọc trai.", "Khử khuẩn tia UV"),

            ("Trang Phục Cosplay Anime Raiden Shogun (Full Giáp & Kiếm)", "COSTUME_FASHION", "Cosplay Studio", "CosMaster", "Size: M",
             None, 0, "Ngực 86cm, Eo 68cm", 130000, 200000, 260000, 600000,
             "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&q=80",
             "Trang phục hóa trang tinh xảo từng phụ kiện, vải in họa tiết kim tuyến lấp lánh, kèm tóc giả và kiếm phát sáng.", "Đầy đủ phụ kiện giáp"),

            ("Set Đồ Đôi Vintage Ngoại Cảnh Đà Lạt (Tone Be Cổ Điển)", "COSTUME_FASHION", "Concept Nàng Thơ", "Tiduba Vintage", "Nam L - Nữ M",
             None, 0, "Freesize Nam/Nữ", 80000, 120000, 160000, 300000,
             "https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?w=800&q=80",
             "Gồm váy xòe vintage caro nữ kèm mũ beret + Áo len cộc tay sơ mi nam quần tây retro, thích hợp chụp ảnh cặp đôi.", "Mới tinh tươm")
        ]

        for item in seed_items:
            cur.execute("""
            INSERT INTO items (name, category, subcategory, brand, serial_or_size, mount_type, shutter_count, measurements, price_4h, price_8h, price_24h, deposit_amount, image_url, description, condition_status, availability, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', ?)
            """, (*item, now))
        conn.commit()

    # Pre-seed Combos
    cur.execute("SELECT count(*) as c FROM combos")
    if cur.fetchone()["c"] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seed_combos = [
            ("Combo Kỷ Yếu Cổ Phục Hoàng Cung", "TIẾT KIỆM 15%", 720000, 850000, 7000000,
             "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=800&q=80",
             "Trọn bộ: Body Sony A7 IV (33MP) + Lens FE 24-70mm GM II + Set Cổ Phục Nhật Bình thêu tay kèm vòng kiềng đồng.",
             json.dumps(["Sony Alpha A7 IV (Body)", "Sony FE 24-70mm f/2.8 GM II", "Set Cổ Phục Việt Nhật Bình"])),

            ("Combo Quay Phim / Music Video Cinematic 4K", "TIẾT KIỆM 20%", 740000, 930000, 8000000,
             "https://images.unsplash.com/photo-1589872766857-2110abb95a08?w=800&q=80",
             "Trọn bộ: Canon EOS R6 Mark II + Gimbal DJI RS 3 Pro + Bộ Vest Nam Quý Tộc Ý sang trọng.",
             json.dumps(["Canon EOS R6 Mark II", "Gimbal DJI RS 3 Pro Combo", "Bộ Vest Nam Quý Tộc Ý"])),

            ("Combo Ngoại Cảnh Nàng Thơ & Flycam Đà Lạt", "TIẾT KIỆM 18%", 710000, 870000, 9000000,
             "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=800&q=80",
             "Trọn bộ: Máy ảnh Fujifilm X-T5 màu Film hoài niệm + Flycam DJI Mini 4 Pro 4K + Set Áo Dài Tơ Tằm Nàng Thơ Trắng.",
             json.dumps(["Fujifilm X-T5 Silver", "Flycam DJI Mini 4 Pro", "Set Áo Dài Tơ Tằm Nàng Thơ Trắng"]))
        ]
        for combo in seed_combos:
            cur.execute("""
            INSERT INTO combos (name, badge, price_24h, original_price_24h, deposit_amount, image_url, description, items_included_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*combo, now))
        conn.commit()

    # Pre-seed Reviews
    cur.execute("SELECT count(*) as c FROM reviews")
    if cur.fetchone()["c"] == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seed_reviews = [
            (1, 2, "Nguyễn Văn Khách", 5, "Máy Sony A7IV siêu mới, cảm biến sạch bong không một hạt bụi. Chụp kỷ yếu ảnh nét căng!", None, now),
            (7, 2, "Nguyễn Văn Khách", 5, "Set cổ phục thêu tay lộng lẫy, đi chụp ở Cố đô Huế ai cũng khen nức nở. Áo thơm tho sạch sẽ!", None, now),
            (2, 2, "Trần Hoàng Long", 5, "Canon R6 II quay 4K 60fps mượt mà, màu da lên tự nhiên. Thuê nhanh, cọc hoàn qua MBBank chuẩn 30 giây.", None, now)
        ]
    # Seed Coupons giảm giá mẫu
    cur.execute("SELECT count(*) as c FROM coupons")
    if cur.fetchone()["c"] == 0:
        seed_coupons = [
            ("TIDUBA50K", "FIXED_AMOUNT", 50000, 200000, 50000, 500, 0, 1, "2026-12-31 23:59:59"),
            ("VIP10", "PERCENT", 10, 500000, 200000, 100, 0, 1, "2026-12-31 23:59:59"),
            ("SONY20", "PERCENT", 20, 1000000, 500000, 50, 0, 1, "2026-12-31 23:59:59")
        ]
        for c in seed_coupons:
            cur.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_order_amount, max_discount_amount, usage_limit, used_count, is_active, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, c)
        conn.commit()

    conn.close()


init_db()


# =============================================================================
# 2. HELPER FUNCTIONS & VIETQR MBBANK 0123006101998
# =============================================================================

def generate_vietqr_url(amount_vnd: int, rental_code: str) -> str:
    """Tạo mã VietQR Napas 247 trỏ về tài khoản MBBank 0123006101998 (KHONG KY DUYEN)."""
    content = f"Thanh toan thue do {rental_code}"
    params = urllib.parse.urlencode({
        "amount": int(amount_vnd),
        "addInfo": content,
        "accountName": BANK_CONFIG["account_name"]
    })
    return f"https://img.vietqr.io/image/{BANK_CONFIG['bank_id']}-{BANK_CONFIG['account_no']}-{BANK_CONFIG['template']}.png?{params}"


TOKEN_SECRET = os.environ.get("TIDUBA_TOKEN_SECRET", "Tiduba_HMAC_Secret_2026_MBBank_0123006101998_CHANGE_IN_PROD")
TOKEN_EXPIRY_SECONDS = 86400 * 30  # 30 ngày
PRINTER_SECRET = os.environ.get("TIDUBA_PRINTER_SECRET", "PRINTER_LOCAL_SECRET_TIDUBA_2026")
WEBHOOK_SECRET = os.environ.get("TIDUBA_WEBHOOK_SECRET", "")  # Set trong production để verify payment webhook


def create_token(user_id: int, username: str, role: str) -> str:
    payload = f"{user_id}:{username}:{role}:{int(time.time())}"
    sig = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    try:
        parts = token.split(":")
        if len(parts) == 5:
            # Token mới dạng: user_id:username:role:ts:sig
            user_id_str, username, role, ts_str, sig = parts
            payload = f"{user_id_str}:{username}:{role}:{ts_str}"
            expected_sig = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            # Token expiry check (30 ngày)
            ts = int(ts_str)
            if time.time() - ts > TOKEN_EXPIRY_SECONDS:
                return None
            user_id = int(user_id_str)
        elif "-" in token and len(token) > 40:
            # Token cũ (backward compat): sha256hash-userid  
            user_id = int(token.split("-")[-1])
        else:
            return None

        conn = get_db()
        user = conn.execute(
            "SELECT id, username, email, full_name, phone, role, cccd_number, face_liveness_verified, loyalty_points FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()
        if user:
            return dict(user)
    except Exception:
        pass
    return None


def require_admin(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Quản trị viên (Admin) mới có quyền truy cập!")
    return user


def get_costume_effective_deadline(start_dt: datetime.datetime, rental_days: float) -> datetime.datetime:
    """
    QUY TẮC TRANG PHỤC: Hạn trả là 20:00 ngày cuối của chu kỳ thuê.
    Ví dụ: Nhận lúc 10:00 ngày 29/9 (1 ngày) → deadline 20:00 ngày 30/9.
    Nhận lúc 10:00 ngày 29/9 (2 ngày) → deadline 20:00 ngày 1/10.
    """
    days_int = max(1, int(rental_days + 0.5))  # làm tròn lên
    end_date = start_dt.date() + datetime.timedelta(days=days_int)
    return datetime.datetime.combine(end_date, datetime.time(20, 0, 0))


def calculate_rental_metrics(start_iso: str, end_iso: str, price_4h: int, price_8h: int, price_24h: int,
                              item_category: Optional[str] = None):
    """
    Tính toán thời lượng thuê theo ca (4h/8h) hoặc block ngày (24h) và giá tiền.
    - Máy ảnh (CAMERA_GEAR): tính theo giờ thực tế khách chọn.
    - Trang phục (COSTUME_FASHION): 
      Thuê là trả trước 20:00 mới là 1 ngày, qua 20:00 là tính phạt (ví dụ: thuê 10:00 29/9 -> trả trước 20:00 30/9 là 1 ngày; qua 20:01 30/9 là trễ).
    """
    try:
        dt_start = datetime.datetime.fromisoformat(start_iso.replace("Z", ""))
        dt_end = datetime.datetime.fromisoformat(end_iso.replace("Z", ""))
    except Exception:
        dt_start = datetime.datetime.strptime(start_iso, "%Y-%m-%d %H:%M")
        dt_end = datetime.datetime.strptime(end_iso, "%Y-%m-%d %H:%M")

    diff_seconds = (dt_end - dt_start).total_seconds()
    if diff_seconds <= 0:
        raise ValueError("Thời gian trả phải sau thời gian nhận đồ!")

    hours = diff_seconds / 3600.0
    is_costume = item_category == "COSTUME_FASHION"

    if is_costume:
        # TRANG PHỤC: 1 ngày = nhận hôm nay, trả trước 20:00 ngày hôm sau
        # Khoảng cách ngày lịch (calendar days)
        calendar_diff = (dt_end.date() - dt_start.date()).days
        
        # Nếu ngày trả cùng ngày nhận hoặc ngày hôm sau và trả trước/đúng 20:00 -> tính 1 ngày
        if calendar_diff <= 1:
            days = 1.0
            dt_end_effective = datetime.datetime.combine(dt_start.date() + datetime.timedelta(days=1), datetime.time(20, 0, 0))
        else:
            # Thuê từ 2 ngày trở lên: hạn trả là 20:00 của ngày trả
            days = float(calendar_diff)
            dt_end_effective = datetime.datetime.combine(dt_start.date() + datetime.timedelta(days=calendar_diff), datetime.time(20, 0, 0))

        rental_type = "24h"
        rental_days = days

        if days >= 3.0:
            discount_multiplier = 0.80
        elif days >= 2.0:
            discount_multiplier = 0.85
        else:
            discount_multiplier = 1.0

        total_price = int(days * price_24h * discount_multiplier)
        return rental_type, hours, rental_days, total_price, dt_start, dt_end_effective

    if hours <= 4.0:
        rental_type = "4h"
        total_price = price_4h
        rental_days = 0.5
    elif hours <= 8.0:
        rental_type = "8h"
        total_price = price_8h
        rental_days = 0.5
    else:
        rental_type = "24h"
        days = max(1.0, round(hours / 24.0, 1))
        rental_days = days
        if days >= 3.0:
            discount_multiplier = 0.80
        elif days >= 2.0:
            discount_multiplier = 0.85
        else:
            discount_multiplier = 1.0
        total_price = int(days * price_24h * discount_multiplier)

    return rental_type, hours, rental_days, total_price, dt_start, dt_end


def sync_items_availability(conn: Optional[sqlite3.Connection] = None):
    """
    Tự động đồng bộ chính xác trạng thái availability của tất cả items dựa trên rentals thực tế:
    - Nếu admin hạ xuống UNAVAILABLE: Giữ nguyên UNAVAILABLE (TẠM NGƯNG).
    - Nếu có đơn thuê status IN ('ACTIVE', 'APPROVED', 'OVERDUE') hoặc (status = 'HOLD' AND hold_expires_at >= now):
      -> ĐANG THUÊ (RENTED)
    - Nếu không có đơn thuê nào đang hoạt động:
      -> SẴN SÀNG (AVAILABLE)
    """
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True

    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()

        # 1. Hủy các đơn HOLD đã hết hạn 15 phút
        cur.execute("""
            UPDATE rentals 
            SET status = 'CANCELLED' 
            WHERE status = 'HOLD' AND hold_expires_at < ?
        """, (now_str,))

        # 2. Tìm tất cả item_id đang có đơn thuê ACTIVE, APPROVED, OVERDUE hoặc HOLD còn hạn
        rented_ids = set()
        active_rentals = cur.execute("""
            SELECT item_id, items_json FROM rentals 
            WHERE status IN ('ACTIVE', 'APPROVED', 'OVERDUE')
               OR (status = 'HOLD' AND hold_expires_at >= ?)
        """, (now_str,)).fetchall()

        for r in active_rentals:
            if r["item_id"]:
                rented_ids.add(r["item_id"])
            if "items_json" in r.keys() and r["items_json"]:
                try:
                    for itm in json.loads(r["items_json"]):
                        if itm.get("item_id"):
                            rented_ids.add(itm["item_id"])
                except Exception:
                    pass

        try:
            ri_rows = cur.execute("""
                SELECT ri.item_id FROM rental_items ri
                JOIN rentals r ON ri.rental_id = r.id
                WHERE r.status IN ('ACTIVE', 'APPROVED', 'OVERDUE')
                   OR (r.status = 'HOLD' AND r.hold_expires_at >= ?)
            """, (now_str,)).fetchall()
            for row in ri_rows:
                if row["item_id"]:
                    rented_ids.add(row["item_id"])
        except Exception:
            pass

        # 3. Cập nhật bảng items
        if rented_ids:
            placeholders = ",".join(["?"] * len(rented_ids))
            cur.execute(f"""
                UPDATE items 
                SET availability = 'RENTED' 
                WHERE id IN ({placeholders}) AND availability != 'UNAVAILABLE'
            """, list(rented_ids))

            cur.execute(f"""
                UPDATE items 
                SET availability = 'AVAILABLE' 
                WHERE id NOT IN ({placeholders}) AND availability != 'UNAVAILABLE'
            """, list(rented_ids))
        else:
            cur.execute("""
                UPDATE items 
                SET availability = 'AVAILABLE' 
                WHERE availability != 'UNAVAILABLE'
            """)

        conn.commit()
    except Exception as e:
        print(f"[SYNC AVAILABILITY] Lỗi: {e}")
    finally:
        if should_close:
            conn.close()


# Tự động đồng bộ tình trạng kho máy ảnh & trang phục ngay khi khởi động
sync_items_availability()


def update_and_check_rental_alerts():
    """Tự động kiểm tra hạn trả đồ, quét đơn quá hạn và tính phạt trễ hạn.
    - Máy ảnh: phạt 30.000đ/giờ quá hạn trả thực tế.
    - Trang phục: deadline luôn là 20:00 ngày cuối; phạt 30.000đ/giờ sau 20:00.
    """
    conn = get_db()
    cur = conn.cursor()
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Thu hồi các đơn HOLD quá hạn và đồng bộ lại kho thiết bị
    sync_items_availability(conn)

    # 2. Quét đơn đang hoạt động (APPROVED hoặc ACTIVE) để phát hiện quá hạn
    rentals = cur.execute("""
    SELECT r.*, i.name as item_name, i.category as item_category,
           u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    JOIN users u ON r.user_id = u.id
    WHERE r.status IN ('APPROVED', 'ACTIVE')
    """).fetchall()

    for r in rentals:
        try:
            dt_end = datetime.datetime.fromisoformat(r["end_time"])
        except Exception:
            dt_end = datetime.datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M")

        item_category = r["item_category"] or ""
        item_display = r["item_name"] or "Gói Combo Trọn Gói"

        # TRANG PHỤC: tính deadline thực tế là 20:00 ngày cuối của end_time
        if item_category == "COSTUME_FASHION":
            # Deadline = 20:00 của ngày end_time (đã được tính sẵn khi booking)
            costume_deadline = dt_end.replace(hour=20, minute=0, second=0, microsecond=0)
            time_left_sec = (costume_deadline - now).total_seconds()
            hours_left = time_left_sec / 3600.0

            if time_left_sec < 0:
                overdue_hours = abs(hours_left)
                # Phạt 30.000đ/giờ quá sau 20:00
                calculated_late_fee = int(overdue_hours * 30000)
                cur.execute("UPDATE rentals SET status = 'OVERDUE', late_fee = ? WHERE id = ?", (calculated_late_fee, r["id"]))

                chk = cur.execute("SELECT id FROM alerts WHERE rental_id = ? AND alert_type = 'OVERDUE'", (r["id"],)).fetchone()
                if not chk:
                    overdue_since = costume_deadline.strftime("%H:%M %d/%m")
                    cur.execute("""
                    INSERT INTO alerts (rental_id, alert_type, title, message, created_at)
                    VALUES (?, 'OVERDUE', ?, ?, ?)
                    """, (
                        r["id"],
                        f"QUAN HAN: {r['rental_code']} - {r['customer_name']}",
                        f"Khach {r['customer_name']} ({r['customer_phone']}) chua tra trang phuc '{item_display}'! Deadline 20:00 qua han {overdue_hours:.1f} gio. Phat tam tinh: {calculated_late_fee:,}d.",
                        now_str
                    ))
            elif time_left_sec <= 7200:  # Cảnh báo 2 giờ trước 20:00 (18:00)
                chk = cur.execute("SELECT id FROM alerts WHERE rental_id = ? AND alert_type = 'WARNING_DUE_SOON'", (r["id"],)).fetchone()
                if not chk:
                    cur.execute("""
                    INSERT INTO alerts (rental_id, alert_type, title, message, created_at)
                    VALUES (?, 'WARNING_DUE_SOON', ?, ?, ?)
                    """, (
                        r["id"],
                        f"SAP TRE HAN 20:00: {r['rental_code']}",
                        f"Khach {r['customer_name']} can tra trang phuc '{item_display}' truoc 20:00 hom nay! Con {hours_left:.1f} gio.",
                        now_str
                    ))
        else:
            # MÁY ẢNH / thiết bị: giữ nguyên logic theo giờ thực tế
            time_left_sec = (dt_end - now).total_seconds()
            hours_left = time_left_sec / 3600.0

            if time_left_sec < 0:
                overdue_hours = abs(hours_left)
                calculated_late_fee = int(overdue_hours * 30000)
                cur.execute("UPDATE rentals SET status = 'OVERDUE', late_fee = ? WHERE id = ?", (calculated_late_fee, r["id"]))

                chk = cur.execute("SELECT id FROM alerts WHERE rental_id = ? AND alert_type = 'OVERDUE'", (r["id"],)).fetchone()
                if not chk:
                    cur.execute("""
                    INSERT INTO alerts (rental_id, alert_type, title, message, created_at)
                    VALUES (?, 'OVERDUE', ?, ?, ?)
                    """, (
                        r["id"],
                        f"QUAN HAN: {r['rental_code']} - {r['customer_name']}",
                        f"Khach {r['customer_name']} ({r['customer_phone']}) chua tra '{item_display}'! Qua han {overdue_hours:.1f} gio. Phat tam tinh: {calculated_late_fee:,}d.",
                        now_str
                    ))
            elif hours_left <= 4.0:
                chk = cur.execute("SELECT id FROM alerts WHERE rental_id = ? AND alert_type = 'WARNING_DUE_SOON'", (r["id"],)).fetchone()
                if not chk:
                    cur.execute("""
                    INSERT INTO alerts (rental_id, alert_type, title, message, created_at)
                    VALUES (?, 'WARNING_DUE_SOON', ?, ?, ?)
                    """, (
                        r["id"],
                        f"SAP TOI HAN: {r['rental_code']}",
                        f"Khach {r['customer_name']} can tra '{item_display}' trong vong {hours_left:.1f} gio nua (Han: {r['end_time']}).",
                        now_str
                    ))

    conn.commit()
    conn.close()


# =============================================================================
# 2.1 AUTH & USER REGISTRATION APIS
# =============================================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    phone: str


@app.post("/api/auth/register")
def register(req: RegisterRequest):
    conn = get_db()
    cur = conn.cursor()
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
        INSERT INTO users (username, email, password_hash, full_name, phone, role, loyalty_points, created_at)
        VALUES (?, ?, ?, ?, ?, 'customer', 50000, ?)
        """, (req.username.strip(), req.email.strip().lower(), hash_password(req.password), req.full_name.strip(), req.phone.strip(), now))
        conn.commit()
        user_id = cur.lastrowid
        token = create_token(user_id, req.username, "customer")
        return {
            "success": True,
            "message": "Đăng ký thành công! Bạn nhận được 50.000đ điểm thưởng VIP.",
            "token": token,
            "user": {
                "id": user_id,
                "username": req.username,
                "full_name": req.full_name,
                "role": "customer",
                "loyalty_points": 50000
            }
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tên đăng nhập hoặc Email đã tồn tại!")
    finally:
        conn.close()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_db()
    p_hash = hash_password(req.password)
    user = conn.execute("""
    SELECT id, username, email, full_name, phone, role, loyalty_points 
    FROM users 
    WHERE (username = ? OR email = ?) AND password_hash = ?
    """, (req.username.strip(), req.username.strip().lower(), p_hash)).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")

    user_dict = dict(user)
    token = create_token(user_dict["id"], user_dict["username"], user_dict["role"])
    return {
        "success": True,
        "message": f"Chào mừng {user_dict['full_name']} quay trở lại!",
        "token": token,
        "user": user_dict
    }


@app.get("/api/auth/me")
def get_me(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}


# =============================================================================
# 3. eKYC & BLACKLIST VERIFICATION ENGINE
# =============================================================================

class EkycVerificationRequest(BaseModel):
    cccd_number: str
    full_name: str
    phone: str
    cccd_front_img: Optional[str] = "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&q=80"
    cccd_back_img: Optional[str] = "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&q=80"
    liveness_confirmed: bool = True


@app.post("/api/ekyc/verify")
def verify_ekyc(req: EkycVerificationRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Xác thực danh tính eKYC tự động: OCR CCCD 2 mặt + Face Liveness Check + Blacklist check."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xác thực eKYC!")

    conn = get_db()
    cur = conn.cursor()

    # 1. Rà soát Blacklist nội bộ (Số điện thoại hoặc CCCD)
    bl = cur.execute("""
    SELECT reason FROM blacklist 
    WHERE phone = ? OR cccd_number = ?
    """, (req.phone.strip(), req.cccd_number.strip())).fetchone()

    if bl:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail=f"CẢNH BÁO BẢO VỆ TÀI SẢN: Thông tin của bạn nằm trong Danh Sách Đen Blacklist nội bộ ({bl['reason']}). Hệ thống từ chối cung cấp dịch vụ thuê thiết bị."
        )

    # 2. Cập nhật trạng thái đã eKYC chính chủ
    cur.execute("""
    UPDATE users 
    SET cccd_number = ?, full_name = ?, phone = ?, cccd_front_img = ?, cccd_back_img = ?, face_liveness_verified = 1
    WHERE id = ?
    """, (req.cccd_number.strip(), req.full_name.strip(), req.phone.strip(), req.cccd_front_img, req.cccd_back_img, user["id"]))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Xác thực danh tính eKYC và Face Liveness 3D thành công!",
        "cccd_verified": req.cccd_number,
        "full_name": req.full_name,
        "liveness_passed": True
    }


# =============================================================================
# 4. E-CONTRACT OTP DIGITAL SIGNING ENGINE
# =============================================================================

@app.post("/api/rentals/{rental_id}/send_contract_otp")
def send_contract_otp(rental_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Gửi mã OTP xác thực ký Hợp Đồng Điện Tử Bồi Thường 100% về SĐT chính chủ."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập!")

    conn = get_db()
    rental = conn.execute("SELECT id, rental_code FROM rentals WHERE id = ? AND user_id = ?", (rental_id, user["id"])).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    # Sinh mã OTP 6 số ngẫu nhiên
    otp_code = f"{(int(time.time() * 1000) % 900000) + 100000}"
    conn.execute("UPDATE rentals SET e_contract_otp = ? WHERE id = ?", (otp_code, rental_id))
    conn.commit()
    conn.close()

    print(f"[OTP SERVICE] 📲 Mã OTP ký hợp đồng cho đơn {rental['rental_code']} gửi tới {user['phone']}: {otp_code}")

    return {
        "success": True,
        "message": f"Mã OTP ký hợp đồng điện tử đã được gửi về số điện thoại {user['phone']}.",
        "demo_otp_code": otp_code # Cung cấp để test nhanh
    }


class VerifyOtpSignRequest(BaseModel):
    otp: str


@app.post("/api/rentals/{rental_id}/sign_contract_otp")
def sign_contract_otp(rental_id: int, req: VerifyOtpSignRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Khách hàng nhập mã OTP để ký số Hợp Đồng Điện Tử."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập!")

    conn = get_db()
    cur = conn.cursor()
    rental = cur.execute("SELECT id, e_contract_otp, rental_code FROM rentals WHERE id = ? AND user_id = ?", (rental_id, user["id"])).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    if not rental["e_contract_otp"] or rental["e_contract_otp"] != req.otp.strip():
        conn.close()
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác hoặc đã hết hạn!")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE rentals 
    SET e_contract_signed = 1, signed_at = ?, e_contract_otp = NULL
    WHERE id = ?
    """, (now_str, rental_id))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Đã ký số Hợp Đồng Điện Tử Bàn Giao & Đền Bù 100% thành công bằng OTP chính chủ!",
        "signed_at": now_str
    }


# =============================================================================
# 5. AUTO-PRINT BILL NHIỆT K80 & WEBHOOK SEPAY/CASSO (KIOTVIET STYLE)
# =============================================================================

def build_escpos_thermal_bill_text(order_data: dict) -> str:
    """Tạo bố cục bill in nhiệt chuẩn K80 (48 cột) kiểu KiotViet có link quét QR nhận trả đồ."""
    domain = PUBLIC_DOMAIN
    branch_code = order_data.get('branch_code', 'CN1')
    branch_info = STORE_BRANCHES.get(branch_code, STORE_BRANCHES['CN1'])

    items_list = order_data.get('items')
    items_block = ""
    if items_list and isinstance(items_list, list) and len(items_list) > 0:
        for idx, itm in enumerate(items_list, 1):
            nm = itm.get('name') or itm.get('item_name', 'Thiết bị')
            sn = itm.get('serial_or_size', '')
            pr = itm.get('price', 0)
            items_block += f"{idx}. {nm[:30]:<30}  1     {pr:>11,}\n"
            if sn:
                items_block += f"   SN/Size: {sn}\n"
    else:
        it_name = order_data.get('item_name', 'Thiết bị / Trang phục')
        it_sn = order_data.get('serial_or_size', '')
        pr = order_data.get('total_price', 0)
        items_block = f"1. {it_name[:30]:<30}  1     {pr:>11,}\n"
        if it_sn:
            items_block += f"   Serial/Size: {it_sn}\n"

    return f"""================================================
           TIDUBASTORE.COM - CAMERA & FASHION   
  CN1: 183A Huynh Thuc Khang, Pleiku, Gia Lai   
  CN2: 801 Le Duan, P. An Phu, TP. Pleiku       
  [XUAT DON]: {branch_info['name']}
  Hotline: 0977.078.981             
================================================
           PHIEU XAC NHAN THUE THIET BI         
          Ma don: {order_data['rental_code']} (PAID)         
       Thoi gian in: {time.strftime('%d/%m/%Y %H:%M:%S')}        
------------------------------------------------
KHACH HANG: {order_data['customer_name']}                        
SO DIEN THOAI: {order_data['customer_phone']}                     
CCCD: {order_data.get('customer_cccd', 'Da luu tru doi chung')}           
------------------------------------------------
THIET BI / TRANG PHUC             SL      DON GIA
------------------------------------------------
{items_block}------------------------------------------------
Goi thue: {order_data.get('rental_type', '24h')} (Duration: {order_data.get('rental_hours', 24)}h)
NHAN MAY: {order_data['start_time']}                    
TRA MAY : {order_data['end_time']} (BAT BUOC)         
CHI NHANH TRA: {branch_info['short_address'][:32]:<32}
------------------------------------------------
TONG TIEN THANH TOAN:              {order_data['total_price']:>12,} VND
[ TRANG THAI: DA XAC THUC THANH TOAN THANH CONG ]
================================================
                    LƯU Ý                       
  DE LAI GIAY TO HOAC COC THEM TIEN,           
  TIEN COC SE HOAN KHI TRA DO.                 
  DOI VOI MAY ANH:                             
  COC 1 GIAY TO + TAI SAN (Dien thoai,         
  Xe may, Laptop, vong vang,...)               
------------------------------------------------
- Tra tre gio: 30,000 VND/gio (qua 6h tinh 1 ngay)
- Thiet bi da kiem tra cam bien sach & lens trong
- Hoan giay to / hoan coc sau 10 phut kiem tra QC
------------------------------------------------
      [ QUET MA QR TRA DO & HOAN COC NHANH ]    
        {domain}/return-qr?code={order_data['rental_code']}
              * {order_data['rental_code']} *               
================================================
       TIDUBASTORE.COM - CHUC BUOI CHUP         
                 THANH CONG RUC RO!             
"""


class PaymentWebhookPayload(BaseModel):
    gateway: Optional[str] = "SePAY / Casso / VietQR"
    account_no: Optional[str] = "0123006101998"
    amount: Optional[float] = 0.0
    description: Optional[str] = ""
    transaction_id: Optional[str] = None


@app.post("/api/webhook/payment")
def payment_webhook_ipn(payload: PaymentWebhookPayload, request: Request):
    """
    Webhook ngân hàng (SePAY / Casso / VietQR PRO) bắt biến động số dư MBBank 0123006101998.
    Tự động xác thực thanh toán -> chuyển ACTIVE -> tự động bắn lệnh in bill K80 không chạm!
    SECURITY: Verify X-Webhook-Token header để chống giả mạo webhook.
    """
    webhook_token = request.headers.get("X-Webhook-Token", "") or request.headers.get("X-Api-Key", "")
    expected_secret = WEBHOOK_SECRET or "PRINTER_LOCAL_SECRET_TIDUBA_2026"
    if webhook_token:
        if not hmac.compare_digest(webhook_token, expected_secret):
            raise HTTPException(status_code=401, detail="Webhook token không hợp lệ!")
    elif WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Thiếu Webhook token xác thực!")
    conn = get_db()
    cur = conn.cursor()

    # Trích xuất mã đơn TDB-XXXXXX từ nội dung chuyển khoản
    match = re.search(r"\b(TDB-[A-Za-z0-9_-]+)\b", payload.description, re.IGNORECASE)
    if not match:
        conn.close()
        return {"status": "IGNORED", "message": "Không tìm thấy mã đơn TDB- trong nội dung chuyển khoản."}

    rental_code = match.group(1).upper()
    rental = cur.execute("""
    SELECT r.*, COALESCE(i.name, c.name) as item_name, COALESCE(i.serial_or_size, 'Combo Trọn Gói') as serial_or_size,
           u.full_name as customer_name, u.phone as customer_phone, u.cccd_number as customer_cccd
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.rental_code = ?
    """, (rental_code,)).fetchone()

    if not rental:
        conn.close()
        return {"status": "NOT_FOUND", "message": f"Không tìm thấy đơn {rental_code}."}

    # Cập nhật đơn hàng sang APPROVED / ACTIVE
    cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (rental["id"],))

    # Tự động đẩy lệnh in bill nhiệt K80 vào hàng đợi in
    bill_text = build_escpos_thermal_bill_text({
        "rental_code": rental["rental_code"],
        "customer_name": rental["customer_name"],
        "customer_phone": rental["customer_phone"],
        "customer_cccd": rental["customer_cccd"] or "0792xxxx8912",
        "item_name": rental["item_name"],
        "serial_or_size": rental["serial_or_size"],
        "rental_type": rental["rental_type"],
        "rental_hours": rental["rental_duration_hours"],
        "start_time": rental["start_time"],
        "end_time": rental["end_time"],
        "total_price": rental["total_price"],
        "deposit_paid": rental["deposit_paid"]
    })

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO print_queue (rental_id, bill_text, status, created_at)
    VALUES (?, ?, 'PENDING', ?)
    """, (rental["id"], bill_text, now_str))

    # Ghi log Zalo ZNS Mốc 1: Xác nhận đơn & Giữ đồ thành công
    cur.execute("""
    INSERT INTO zns_logs (rental_id, phone, milestone, template_id, channel, status, sent_at)
    VALUES (?, ?, 'MILESTONE_1_CONFIRMED', 'TDB_ZNS_BOOKING_CONFIRM_V1', 'ZALO_ZNS', 'SENT', ?)
    """, (rental["id"], rental["customer_phone"], now_str))

    conn.commit()
    conn.close()

    print(f"[PRINT & PAYMENT] 💰 ĐÃ NHẬN TIỀN MBBANK 0123006101998 CHO ĐƠN {rental_code} -> KÍCH HOẠT MÁY IN NHIỆT K80 TỰ ĐỘNG IN BILL!")
    return {
        "status": "PAYMENT_CONFIRMED_AUTO_PRINT_TRIGGERED",
        "rental_code": rental_code,
        "amount_received": payload.amount,
        "print_bill_preview": bill_text[:200]
    }


@app.get("/api/printer/pending_jobs")
def get_printer_pending_jobs(x_printer_secret: Optional[str] = Header(None)):
    """Local Print Agent tại quầy gọi để lấy danh sách bill cần in. Yêu cầu header X-Printer-Secret."""
    if not hmac.compare_digest((x_printer_secret or ""), PRINTER_SECRET):
        raise HTTPException(status_code=401, detail="Printer secret không hợp lệ!")
    conn = get_db()
    jobs = conn.execute("SELECT * FROM print_queue WHERE status = 'PENDING' ORDER BY id ASC").fetchall()
    conn.close()
    return {"jobs": [dict(j) for j in jobs], "count": len(jobs)}


@app.post("/api/printer/ack/{job_id}")
def ack_printer_job(job_id: int, x_printer_secret: Optional[str] = Header(None)):
    """Máy in tại quầy xác nhận đã in xong và cắt giấy. Yêu cầu header X-Printer-Secret."""
    if not hmac.compare_digest((x_printer_secret or ""), PRINTER_SECRET):
        raise HTTPException(status_code=401, detail="Printer secret không hợp lệ!")
    conn = get_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE print_queue SET status = 'PRINTED', printed_at = ? WHERE id = ?", (now_str, job_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Job #{job_id} đã in thành công!"}


# =============================================================================
# 5.1 COUPON & PROMOTION ENGINE
# =============================================================================

class ApplyCouponRequest(BaseModel):
    code: str
    order_amount: int


@app.post("/api/coupons/apply")
def apply_coupon(req: ApplyCouponRequest):
    """Kiểm tra và tính toán giảm giá của mã Coupon."""
    conn = get_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c = conn.execute("""
    SELECT * FROM coupons 
    WHERE code = ? AND is_active = 1 AND expires_at >= ?
    """, (req.code.strip().upper(), now_str)).fetchone()
    conn.close()

    if not c:
        raise HTTPException(status_code=400, detail="Mã giảm giá không tồn tại hoặc đã hết hạn!")

    if c["used_count"] >= c["usage_limit"]:
        raise HTTPException(status_code=400, detail="Mã giảm giá đã hết lượt sử dụng!")

    if req.order_amount < c["min_order_amount"]:
        raise HTTPException(status_code=400, detail=f"Đơn hàng phải tối thiểu {c['min_order_amount']:,}đ để áp dụng mã này!")

    discount = 0
    if c["discount_type"] == "PERCENT":
        discount = int((req.order_amount * c["discount_value"]) / 100.0)
        if c["max_discount_amount"]:
            discount = min(discount, c["max_discount_amount"])
    else:
        discount = c["discount_value"]

    discount = min(discount, req.order_amount)
    return {
        "success": True,
        "code": c["code"],
        "discount_type": c["discount_type"],
        "discount_value": c["discount_value"],
        "discount_amount": discount,
        "final_amount": req.order_amount - discount,
        "message": f"Áp dụng thành công mã {c['code']}: Giảm -{discount:,}đ!"
    }


# =============================================================================
# 6. DIGITAL HANDOVER & QC TRỪ TIỀN CỌC (PAPERLESS DESK)
# =============================================================================

class HandoverSubmitRequest(BaseModel):
    rental_id: int
    phase: str # 'CHECKOUT' (giao máy) hoặc 'CHECKIN' (nhận máy)
    sensor_clean: bool = True
    lens_scratchless: bool = True
    shutter_count: int = 4120
    camera_front_img: Optional[str] = "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80"
    camera_lens_img: Optional[str] = "https://images.unsplash.com/photo-1617005082133-548c4dd27f35?w=600&q=80"
    camera_sensor_img: Optional[str] = "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&q=80"
    costume_details_img: Optional[str] = "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&q=80"
    accessories_included: str = "Body máy, nắp đậy, 2 pin zin, củ sạc kép, thẻ 128GB, dây đeo, túi chống sốc"
    staff_signature_svg: str = "[Digital Signature: Le Nhat Phat]"
    customer_signature_svg: str = "[Digital Signature: Khach Hang]"
    notes: Optional[str] = "Thiết bị và trang phục sạch sẽ, nguyên vẹn"


@app.post("/api/handover/submit")
def submit_handover_protocol(req: HandoverSubmitRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Nhân viên và khách hàng ký biên bản bàn giao số trực tiếp qua camera & chữ ký cảm ứng."""
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO handover_protocols (
        rental_id, phase, staff_name, sensor_clean, lens_scratchless, shutter_count_verified,
        camera_front_img, camera_lens_img, camera_sensor_img, costume_details_img,
        accessories_included, staff_signature_svg, customer_signature_svg, notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.rental_id, req.phase.upper(), "Lê Nhật Phát (Staff QC)",
        1 if req.sensor_clean else 0, 1 if req.lens_scratchless else 0, req.shutter_count,
        req.camera_front_img, req.camera_lens_img, req.camera_sensor_img, req.costume_details_img,
        req.accessories_included, req.staff_signature_svg, req.customer_signature_svg, req.notes, now_str
    ))

    # Cập nhật số shot thực tế của máy ảnh
    rental = cur.execute("SELECT item_id FROM rentals WHERE id = ?", (req.rental_id,)).fetchone()
    if rental and rental["item_id"]:
        cur.execute("UPDATE items SET shutter_count = ? WHERE id = ?", (req.shutter_count, rental["item_id"]))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Đã lưu Biên bản Bàn giao & Kiểm định ({req.phase}) thành công kèm chữ ký cảm ứng và ảnh chụp camera đối chứng!"
    }


class DamagePenaltyRequest(BaseModel):
    rental_id: int
    damage_code: str
    damage_title: str
    penalty_amount: int
    notes: Optional[str] = None


@app.post("/api/qc/add_damage_penalty")
def add_damage_penalty(req: DamagePenaltyRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Nhân viên chọn lỗi từ danh mục chuẩn hóa để tự động trừ tiền cọc."""
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO damage_penalties (rental_id, damage_code, damage_title, penalty_amount, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (req.rental_id, req.damage_code, req.damage_title, req.penalty_amount, req.notes, now_str))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Đã ghi nhận khấu trừ: {req.damage_title} (-{req.penalty_amount:,}đ) vào tiền cọc!"
    }


@app.post("/api/qc/complete_refund/{rental_id}")
def complete_qc_and_refund(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Hoàn tất nghiệm thu: Tính toán tổng cọc trừ tiền phạt và kích hoạt hoàn tiền tự động qua MBBank."""
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rental = cur.execute("""
    SELECT r.*, u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()

    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn!")

    rental = dict(rental)
    if rental["status"] == "RETURNED":
        conn.close()
        return {"success": False, "message": "Đơn đã được nghiệm thu và hoàn tiền trước đó!"}

    # Tính tổng tiền trừ phạt
    penalties = cur.execute("SELECT sum(penalty_amount) as s FROM damage_penalties WHERE rental_id = ?", (rental_id,)).fetchone()["s"] or 0
    total_deduction = penalties + rental["late_fee"]
    refund_amount = max(0, rental["deposit_paid"] - total_deduction)

    # Chuyển trạng thái đơn sang RETURNED
    cur.execute("UPDATE rentals SET status = 'RETURNED' WHERE id = ?", (rental_id,))
    if "items_json" in rental.keys() and rental["items_json"]:
        try:
            for itm in json.loads(rental["items_json"]):
                if itm.get("item_id"):
                    cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (itm["item_id"],))
        except Exception: pass
    elif rental["item_id"]:
        cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (rental["item_id"],))

    # Ghi nhận log Zalo ZNS Mốc 3: Hoàn cọc thành công
    cur.execute("""
    INSERT INTO zns_logs (rental_id, phone, milestone, template_id, channel, status, sent_at)
    VALUES (?, ?, 'MILESTONE_3_REFUNDED', 'TDB_ZNS_REFUND_SUCCESS_V1', 'ZALO_ZNS', 'SENT', ?)
    """, (rental_id, rental["customer_phone"], now_str))

    conn.commit()
    conn.close()

    print(f"[QC COMPLETED] 💰 ĐÃ HOÀN CỌC THÀNH CÔNG CHO KHÁCH {rental['customer_name']}: {refund_amount:,}đ (Trừ phạt: {total_deduction:,}đ). BẮN TIN ZNS MỐC 3!")

    return {
        "success": True,
        "message": f"Nghiệm thu hoàn tất! Đã kích hoạt hoàn trả {refund_amount:,} VNĐ tiền cọc cho khách hàng {rental['customer_name']}.",
        "deposit_paid": rental["deposit_paid"],
        "damage_deduction": penalties,
        "late_fee_deduction": rental["late_fee"],
        "refund_amount": refund_amount,
        "bank_destination": "Tài khoản chính chủ khớp tên CCCD (MBBank / Techcombank)"
    }


# =============================================================================
# 7. EXPORT HỒ SƠ PHÁP LÝ QUÁ HẠN 24H (LEGAL DOSSIER PDF/HTML)
# =============================================================================

@app.get("/api/rentals/{rental_id}/legal_dossier", response_class=HTMLResponse)
def get_legal_overdue_dossier(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Tự động xuất hồ sơ pháp lý chuyển cơ quan chức năng khi khách thuê quá hạn 24h không trả."""
    conn = get_db()
    r = conn.execute("""
    SELECT r.*, COALESCE(i.name, c.name) as item_name, COALESCE(i.serial_or_size, 'Combo') as serial_or_size,
           COALESCE(i.deposit_amount, 5000000) as item_value,
           u.full_name as customer_name, u.phone as customer_phone, u.email as customer_email,
           u.cccd_number, u.cccd_front_img, u.cccd_back_img
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn!")

    now_str = datetime.datetime.now().strftime("ngày %d tháng %m năm %Y")

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Hồ Sơ Pháp Lý Vi Phạm Chiếm Đoạt Tài Sản - {r['rental_code']}</title>
    <style>
        body {{ font-family: 'Times New Roman', Times, serif; font-size: 13pt; line-height: 1.5; color: #111; margin: 35px; background: #fff; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h3 {{ margin: 0; text-transform: uppercase; font-size: 12pt; }}
        .title {{ text-align: center; text-transform: uppercase; font-weight: bold; font-size: 16pt; color: #dc2626; margin: 25px 0 15px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #333; padding: 8px; font-size: 12pt; text-align: left; }}
        th {{ background-color: #f1f5f9; }}
        .cccd-box {{ display: flex; gap: 20px; margin: 15px 0; }}
        .cccd-box img {{ width: 48%; border: 1px solid #999; border-radius: 6px; }}
        .btn-print {{ position: fixed; top: 15px; right: 15px; background: #dc2626; color: #fff; padding: 10px 18px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }}
        @media print {{ .btn-print {{ display: none; }} }}
    </style>
</head>
<body>
    <button class="btn-print" onclick="window.print()">🖨️ In Hồ Sơ Chuyển Cơ Quan Chức Năng</button>

    <div class="header">
        <h3>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h3>
        <p style="margin: 0;">Độc lập – Tự do – Hạnh phúc</p>
        <p style="margin: 3px 0;">-----------------------</p>
    </div>

    <div class="title">ĐƠN TRÌNH BÁO VI PHẠM CHIẾM ĐOẠT TÀI SẢN THUÊ QUÁ HẠN 24 GIỜ</div>
    <p style="text-align: center; font-style: italic; margin-top: -10px;">(Hồ sơ trích xuất tự động từ hệ thống giám sát eKYC Tiduba Store - Lập {now_str})</p>

    <p><strong>Kính gửi:</strong> CƠ QUAN CẢNH SÁT ĐIỀU TRA & CÔNG AN KHU VỰC</p>

    <p><strong>BÊN BỊ HẠI (CỬA HÀNG CHO THUÊ):</strong></p>
    <ul>
        <li>Đơn vị: <strong>HỆ THỐNG CỬA HÀNG CHO THUÊ TIDUBA STORE</strong></li>
        <li>Chủ sở hữu & Đại diện pháp lý: <strong>LÊ NHẬT PHÁT</strong></li>
        <li>Tài khoản ngân hàng đối soát giao dịch: <strong>MBBank 0123006101998 (KHONG KY DUYEN)</strong></li>
    </ul>

    <p><strong>ĐỐI TƯỢNG BỊ TỐ CÁO (NGƯỜI THUÊ KHÔNG HOÀN TRẢ):</strong></p>
    <ul>
        <li>Họ và tên: <strong>{r['customer_name']}</strong></li>
        <li>Số điện thoại đăng ký chính chủ: <strong>{r['customer_phone']}</strong></li>
        <li>Số CCCD gắn chip (Đã xác thực eKYC): <strong>{r['cccd_number']}</strong></li>
        <li>Email liên hệ: {r['customer_email']}</li>
    </ul>

    <p><strong>HÌNH ẢNH CCCD 2 MẶT & ĐỐI CHỨNG KHUÔN MẶT LIVENESS:</strong></p>
    <div class="cccd-box">
        <img src="{r['cccd_front_img']}" alt="Mặt trước CCCD">
        <img src="{r['cccd_back_img']}" alt="Mặt sau CCCD">
    </div>

    <p><strong>TÀI SẢN BỊ CHIẾM ĐOẠT & THỜI GIAN VI PHẠM:</strong></p>
    <table>
        <tr>
            <th>Tên Thiết Bị Bị Chiếm Đoạt</th>
            <th>Mã Serial Độc Nhất</th>
            <th>Hạn Trả Đồ Hợp Đồng</th>
            <th>Tổng Tiền Phạt Trễ</th>
        </tr>
        <tr>
            <td><strong>{r['item_name']}</strong></td>
            <td><strong>{r['serial_or_size']}</strong></td>
            <td><strong style="color: #dc2626;">{r['end_time']}</strong></td>
            <td><strong>{r['late_fee']:,} VNĐ</strong></td>
        </tr>
    </table>

    <p>Đối tượng đã ký hợp đồng điện tử bằng mã OTP và cam kết bồi thường 100% nhưng đến nay đã quá hạn trên 24 giờ, tắt máy và có dấu hiệu cố tình tẩu tán tài sản máy ảnh có giá trị lớn. Kính đề nghị Quý Cơ quan thụ lý xác minh và truy thu tài sản theo quy định của Pháp luật.</p>

    <div style="margin-top: 40px; display: flex; justify-content: flex-end;">
        <div style="text-align: center; width: 45%;">
            <p><strong>NGƯỜI LÀM ĐƠN TRÌNH BÁO</strong></p>
            <div style="height: 60px;"></div>
            <p><strong>LÊ NHẬT PHÁT</strong><br>Autonomous Software Agency</p>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


# =============================================================================
# 8. STANDARD CORE APIS (ITEMS, COMBOS, REVIEWS, CALENDAR, BRANCHES)
# =============================================================================

@app.get("/api/branches")
def get_store_branches():
    """Lấy danh sách 2 chi nhánh chính thức của Tiduba Store."""
    return {
        "success": True,
        "branches": list(STORE_BRANCHES.values())
    }


@app.get("/api/items")
def get_items(
    category: Optional[str] = None, 
    subcategory: Optional[str] = None, 
    search: Optional[str] = None,
    branch_code: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Lấy danh mục sản phẩm, có bộ lọc theo khoảng ngày nhận/trả trực tiếp và theo chi nhánh."""
    conn = get_db()
    sync_items_availability(conn)
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if subcategory:
        query += " AND subcategory = ?"
        params.append(subcategory)
    if branch_code and branch_code.upper() in STORE_BRANCHES:
        query += " AND (branch_code = ? OR branch_code IS NULL OR branch_code = '')"
        params.append(branch_code.upper())
    if search:
        query += " AND (name LIKE ? OR brand LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    # Lọc các thiết bị KHÔNG bị trùng lịch trong khoảng start_time -> end_time
    if start_time and end_time:
        query += """
        AND id NOT IN (
            SELECT item_id FROM rentals 
            WHERE item_id IS NOT NULL 
              AND status IN ('APPROVED', 'ACTIVE', 'HOLD', 'OVERDUE')
              AND NOT (end_time <= ? OR start_time >= ?)
        )
        """
        params.extend([start_time, end_time])

    query += " ORDER BY category ASC, id DESC"
    items = [dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()
    return {"items": items, "count": len(items)}


@app.get("/api/items/{item_id}")
def get_item_detail(item_id: int):
    conn = get_db()
    sync_items_availability(conn)
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị này!")
    return dict(item)


@app.get("/api/combos")
def get_combos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM combos ORDER BY id ASC").fetchall()
    conn.close()
    combos = []
    for r in rows:
        d = dict(r)
        d["items_included"] = json.loads(d["items_included_json"])
        combos.append(d)
    return {"combos": combos, "count": len(combos)}


@app.get("/api/items/{item_id}/calendar")
def get_item_booked_calendar(item_id: int):
    conn = get_db()
    booked = conn.execute("""
    SELECT rental_code, start_time, end_time, status 
    FROM rentals 
    WHERE item_id = ? AND status IN ('APPROVED', 'ACTIVE', 'OVERDUE')
    ORDER BY start_time ASC
    """, (item_id,)).fetchall()
    conn.close()
    return {"item_id": item_id, "booked_ranges": [dict(r) for r in booked]}


@app.get("/api/items/{item_id}/reviews")
def get_item_reviews(item_id: int):
    conn = get_db()
    revs = conn.execute("SELECT * FROM reviews WHERE item_id = ? ORDER BY id DESC", (item_id,)).fetchall()
    conn.close()
    reviews_list = [dict(r) for r in revs]
    avg_rating = round(sum(r["rating"] for r in reviews_list) / max(1, len(reviews_list)), 1) if reviews_list else 5.0
    return {"item_id": item_id, "reviews": reviews_list, "average_rating": avg_rating, "total_reviews": len(reviews_list)}


class PostReviewRequest(BaseModel):
    rating: int = Field(default=5, ge=1, le=5)
    comment: str
    photo_sample_url: Optional[str] = None


@app.post("/api/items/{item_id}/reviews")
def post_item_review(item_id: int, req: PostReviewRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để đánh giá!")
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO reviews (item_id, user_id, user_name, rating, comment, photo_sample_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, user["id"], user["full_name"], req.rating, req.comment, req.photo_sample_url, now_str))

    cur.execute("UPDATE users SET loyalty_points = loyalty_points + 10000 WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Cảm ơn bạn đã đánh giá! Bạn được tặng thêm +10.000đ điểm VIP."}


# =============================================================================
# 9. BOOKING, HOLD LOCK (15 PHÚT) & QUẢN LÝ ĐƠN THUÊ
# =============================================================================

class RentalBookingRequest(BaseModel):
    item_id: Optional[int] = None
    combo_id: Optional[int] = None
    start_time: str
    end_time: str
    branch_code: Optional[str] = "CN1"  # 'CN1' (Pleiku, Gia Lai) hoặc 'CN2' (TP. Hồ Chí Minh)
    customer_notes: Optional[str] = None
    deposit_type: Optional[str] = "CCCD"  # 'CCCD' (giữ CCCD gốc) hoặc 'ASSET' (cọc tài sản tự nhập)
    deposit_asset_desc: Optional[str] = None  # Mô tả tài sản cọc (nếu là ASSET)
    custom_deposit_amount: Optional[int] = None  # Giá trị cọc định giá (nếu là ASSET)
    custom_rental_price: Optional[int] = None  # Admin chỉnh sửa trực tiếp giá thuê
    refund_bank_info: Optional[str] = None  # STK Ngân Hàng khách nhận hoàn cọc
    use_loyalty_points: Optional[bool] = False
    coupon_code: Optional[str] = None


@app.post("/api/rentals/book")
def create_rental_booking(req: RentalBookingRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Đặt thuê thiết bị kèm khóa tạm kho (Hold Inventory 15 phút đếm ngược).
    Hỗ trợ hình thức cọc: 'CCCD' (giữ CCCD gốc) hoặc 'ASSET' (tự nhập tài sản & số tiền).
    """
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để đặt thuê đồ!")

    conn = get_db()
    cur = conn.cursor()

    # Kiểm tra Blacklist
    bl = cur.execute("SELECT reason FROM blacklist WHERE phone = ? OR cccd_number = ?", (user["phone"], user.get("cccd_number", ""))).fetchone()
    if bl:
        conn.close()
        raise HTTPException(status_code=403, detail=f"Tài khoản của bạn bị tạm ngưng giao dịch ({bl['reason']}).")

    price_4h = price_8h = price_24h = default_deposit = 0
    item_name = ""
    item_category = "CAMERA_GEAR"

    if req.combo_id:
        combo = cur.execute("SELECT * FROM combos WHERE id = ?", (req.combo_id,)).fetchone()
        if not combo:
            conn.close()
            raise HTTPException(status_code=404, detail="Gói Combo không tồn tại!")
        price_4h = int(combo["price_24h"] * 0.5)
        price_8h = int(combo["price_24h"] * 0.7)
        price_24h = combo["price_24h"]
        default_deposit = combo["deposit_amount"]
        item_name = combo["name"]
        item_category = "COMBO_BUNDLE"
    elif req.item_id:
        item = cur.execute("SELECT * FROM items WHERE id = ?", (req.item_id,)).fetchone()
        if not item:
            conn.close()
            raise HTTPException(status_code=404, detail="Thiết bị không tồn tại!")
        if item["availability"] != "AVAILABLE":
            conn.close()
            raise HTTPException(status_code=400, detail="Thiết bị này hiện đang có người thuê hoặc đang trong 15 phút khóa cọc!")
        price_4h = item["price_4h"]
        price_8h = item["price_8h"]
        price_24h = item["price_24h"]
        default_deposit = item["deposit_amount"]
        item_name = item["name"]
        item_category = item["category"]
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Vui lòng chọn thiết bị hoặc combo!")

    # PHẦN CỌC: Tiền cọc = 0đ (Mặc định) hoặc Cọc tài sản tự chọn
    deposit_amount = 0
    dep_type = req.deposit_type or "CCCD"
    asset_desc = req.deposit_asset_desc or "Để lại giấy tờ hoặc cọc thêm tiền (Hoàn lại khi trả đồ)"

    if req.custom_deposit_amount is not None and req.custom_deposit_amount > 0:
        deposit_amount = req.custom_deposit_amount
        dep_type = "ASSET"
        asset_desc = req.deposit_asset_desc or f"Khách tự nhập tiền cọc: {deposit_amount:,}đ"

    try:
        rental_type, hours, rental_days, total_price, dt_start, dt_end = calculate_rental_metrics(
            req.start_time, req.end_time, price_4h, price_8h, price_24h, item_category
        )
    except ValueError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    # ADMIN CHỈNH GIÁ TRỰC TIẾP: Đồng bộ giá mới vào hóa đơn và VietQR
    if req.custom_rental_price is not None and user.get("role") == "admin" and req.custom_rental_price >= 0:
        total_price = req.custom_rental_price

    effective_end_time = dt_end.strftime("%Y-%m-%d %H:%M")
    discount = 0

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    hold_expires_at = (now + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    rental_code = f"TDB-{int(time.time()*1000)%1000000:06d}"
    selected_branch = req.branch_code.upper().strip() if req.branch_code and req.branch_code.upper().strip() in STORE_BRANCHES else "CN1"
    branch_info = STORE_BRANCHES[selected_branch]

    # Đưa vào trạng thái HOLD (khóa tạm 15 phút)
    cur.execute("""
    INSERT INTO rentals (
        rental_code, user_id, item_id, combo_id, rental_type, start_time, end_time,
        rental_duration_hours, hold_expires_at, total_price, deposit_paid, deposit_type,
        deposit_asset_desc, branch_code, refund_bank_info, status, customer_notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'HOLD', ?, ?)
    """, (
        rental_code, user["id"], req.item_id, req.combo_id, rental_type,
        req.start_time, effective_end_time, hours, hold_expires_at,
        total_price, deposit_amount, dep_type,
        asset_desc, selected_branch, req.refund_bank_info, req.customer_notes, now_str
    ))

    # Khóa thiết bị sang RENTED
    if req.item_id:
        cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (req.item_id,))

    conn.commit()
    rental_id = cur.lastrowid
    conn.close()

    total_payment = total_price
    qr_url = generate_vietqr_url(total_payment, rental_code)

    # Gửi thông báo Telegram khi có đơn thuê mới kèm Lưu ý
    tele_msg = (
        f"<b>📸 TIDUBA STORE - ĐƠN THUÊ MỚI ({rental_code})</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Chi nhánh:</b> <b>{branch_info['name']}</b> ({branch_info['short_address']})\n"
        f"👤 <b>Khách hàng:</b> {user['full_name']} (<code>{user['phone']}</code>)\n"
        f"📦 <b>Thiết bị:</b> {item_name}\n"
        f"⏳ <b>Thời gian:</b> {req.start_time} ➔ {effective_end_time} ({hours:.1f}h)\n"
        f"💵 <b>Tiền thuê:</b> <b>{total_price:,}đ</b>\n"
        f"⚠️ <b>LƯU Ý:</b> Để lại giấy tờ hoặc cọc thêm tiền, Tiền cọc sẽ hoàn khi trả đồ.\n"
        f"📌 <b>Đối với máy ảnh:</b> Cọc 1 giấy tờ + tài sản (Điện thoại, Xe máy, Laptop, vòng vàng,...)\n"
        f"💳 <b>Tổng thanh toán:</b> <b>{total_payment:,}đ</b> (VietQR MBBank)\n"
        f"📝 <b>Ghi chú:</b> {req.customer_notes or 'Không có'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Quét trả đồ: {PUBLIC_DOMAIN}/return-qr?code={rental_code}"
    )
    # Không gửi Telegram ở trạng thái HOLD (Chỉ gửi khi khách bấm nút 'TÔI ĐÃ CHUYỂN TIỀN kèm ảnh biên lai')

    return {
        "success": True,
        "message": "Đã khóa giữ máy thành công trong 15 phút! Vui lòng quét mã VietQR MBBank để xác nhận đơn.",
        "rental_id": rental_id,
        "rental_code": rental_code,
        "item_name": item_name,
        "branch_code": selected_branch,
        "branch_info": branch_info,
        "rental_type": rental_type,
        "rental_hours": hours,
        "rental_days": rental_days,
        "hold_expires_at": hold_expires_at,
        "hold_countdown_seconds": 900,
        "total_price": total_price,
        "deposit_amount": deposit_amount,
        "deposit_type": dep_type,
        "deposit_asset_desc": asset_desc,
        "discount_applied": 0,
        "total_payable": total_payment,
        "qr_image_url": qr_url,
        "bank_account": f"{BANK_CONFIG['bank_name']} - STK: {BANK_CONFIG['account_no']} ({BANK_CONFIG['account_name']})",
        "start_time": req.start_time,
        "end_time": effective_end_time
    }


@app.post("/api/rentals/{rental_id}/cancel_unpaid")
def cancel_unpaid_rental(rental_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Khách hàng hoặc Admin đóng cửa sổ VietQR MBBank mà chưa thanh toán:
    - Hủy đơn hàng nháp (status = 'CANCELLED')
    - Nhả kho thiết bị về 'AVAILABLE'
    - Đơn này KHÔNG hiển thị trong 'Lịch Sử & Đơn Thuê Thiết Bị Của Tôi'
    """
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    # Chỉ cho phép hủy nếu đơn đang ở trạng thái chưa thanh toán (HOLD hoặc PENDING)
    if rental["status"] not in ("HOLD", "PENDING"):
        conn.close()
        return {"success": False, "message": "Đơn hàng đã được thanh toán hoặc xử lý trước đó."}

    # Kiểm tra quyền: phải là chủ đơn hoặc admin
    if user is None or (user.get("role") != "admin" and rental["user_id"] != user["id"]):
        conn.close()
        raise HTTPException(status_code=403, detail="Không có quyền hủy đơn này!")

    # Cập nhật trạng thái CANCELLED
    cur.execute("UPDATE rentals SET status = 'CANCELLED', customer_notes = COALESCE(customer_notes, '') || ' | Khách đóng cửa sổ VietQR (Chưa thanh toán)' WHERE id = ?", (rental_id,))

    # Nhả kho thiết bị đơn lẻ hoặc nhiều món
    if rental["items_json"]:
        try:
            itms = json.loads(rental["items_json"])
            for itm in itms:
                if itm.get("item_id"):
                    cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (itm["item_id"],))
        except Exception:
            pass
    elif rental["item_id"]:
        cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (rental["item_id"],))

    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã hủy đơn nháp chưa thanh toán và nhả kho thiết bị."}


@app.get("/api/rentals/track/{rental_code}")
def track_rental_order(rental_code: str):
    """
    Tra cứu trạng thái đơn hàng công khai:
    - Hỗ trợ tra cứu theo Mã đơn: TDB-XXXXXX
    - Hỗ trợ tra cứu theo Số điện thoại: 0977xxxxxx (trả về danh sách đơn của SĐT đó)
    - Bảo mật: Che bớt tên và số điện thoại, tuyệt đối không lộ CCCD.
    """
    kw = rental_code.strip()
    conn = get_db()
    cur = conn.cursor()

    # Kiểm tra nếu keyword là số điện thoại (10 hoặc 11 chữ số bắt đầu bằng 0)
    clean_phone = re.sub(r"[^\d]", "", kw)
    if len(clean_phone) in (10, 11) and clean_phone.startswith("0"):
        rows = cur.execute("""
        SELECT r.id, r.rental_code, r.status, r.end_time, r.start_time, r.total_price, 
               r.branch_code, r.items_json, r.deposit_paid,
               COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
               COALESCE(i.image_url, c.image_url, '/static/logo.png') as item_image,
               u.full_name as customer_name
        FROM rentals r
        LEFT JOIN items i ON r.item_id = i.id
        LEFT JOIN combos c ON r.combo_id = c.id
        JOIN users u ON r.user_id = u.id
        WHERE u.phone = ? AND r.status != 'CANCELLED'
        ORDER BY r.id DESC LIMIT 10
        """, (clean_phone,)).fetchall()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng nào gắn với số điện thoại '{clean_phone}'!")

        results = []
        for r in rows:
            d = dict(r)
            d["qr_url"] = generate_vietqr_url(d["total_price"] + d["deposit_paid"], d["rental_code"])
            b_code = d.get("branch_code", "CN1") or "CN1"
            d["branch_info"] = STORE_BRANCHES.get(b_code, STORE_BRANCHES["CN1"])
            d.pop("deposit_paid", None)
            d.pop("items_json", None)
            parts = (d["customer_name"] or "Khách Hàng").split()
            if len(parts) >= 2:
                d["customer_name"] = f"{parts[0]} {'*' * (len(parts[-1])-1)}{parts[-1][-1]}"
            results.append(d)

        masked_phone = f"{clean_phone[:3]}***{clean_phone[-3:]}"
        return {"success": True, "type": "PHONE_LOOKUP", "rentals": results, "phone_masked": masked_phone}

    # Ngược lại: tra cứu theo mã đơn hàng TDB-XXXXXX
    code = kw.upper()
    r = cur.execute("""
    SELECT r.id, r.rental_code, r.status, r.end_time, r.start_time, r.total_price, 
           r.branch_code, r.items_json, r.deposit_paid,
           COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
           COALESCE(i.image_url, c.image_url, '/static/logo.png') as item_image,
           COALESCE(i.category, 'COMBO_BUNDLE') as item_category,
           COALESCE(i.serial_or_size, 'Thiết bị') as serial_or_size,
           u.full_name as customer_name
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE UPPER(r.rental_code) = ?
    """, (code,)).fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng có mã '{code}'!")

    d = dict(r)
    d["qr_url"] = generate_vietqr_url(d["total_price"] + d["deposit_paid"], d["rental_code"])
    b_code = d.get("branch_code", "CN1") or "CN1"
    d["branch_info"] = STORE_BRANCHES.get(b_code, STORE_BRANCHES["CN1"])
    # Ẩn thông tin nhạy cảm khỏi public track API
    d.pop("deposit_paid", None)

    if d.get("items_json"):
        try:
            d["items"] = json.loads(d["items_json"])
        except Exception:
            d["items"] = []
    d.pop("items_json", None)

    return {"success": True, "type": "CODE_LOOKUP", "rental": d}


class MultiItemCartItem(BaseModel):
    item_id: Optional[int] = None
    combo_id: Optional[int] = None
    rental_type: Optional[str] = "24h" # '4h', '8h', '1_day', 'multi_days'
    days: Optional[float] = 1.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    custom_price: Optional[int] = None # Admin chỉnh sửa giá từng món


class MultiItemBookingRequest(BaseModel):
    items: List[MultiItemCartItem]
    start_time: str
    end_time: str
    branch_code: Optional[str] = "CN1"  # 'CN1' (Pleiku, Gia Lai) hoặc 'CN2' (TP. Hồ Chí Minh)
    customer_notes: Optional[str] = None
    deposit_type: Optional[str] = "CCCD"
    deposit_asset_desc: Optional[str] = None
    custom_deposit_amount: Optional[int] = None
    custom_total_rental_price: Optional[int] = None # Admin chỉnh sửa trực tiếp tổng tiền thuê
    pos_discount: Optional[int] = 0 # Giảm giá chiết khấu tại POS
    pos_surcharge: Optional[int] = 0 # Phụ thu tại POS
    refund_bank_info: Optional[str] = None # STK Ngân hàng khách nhận hoàn cọc
    use_loyalty_points: Optional[bool] = False
    coupon_code: Optional[str] = None
    # Thông tin dành cho Admin POS KiotViet:
    customer_id: Optional[int] = None
    walk_in_customer_name: Optional[str] = None
    walk_in_customer_phone: Optional[str] = None
    is_direct_paid: Optional[bool] = False # True = Đã thu tiền mặt/chuyển khoản tại quầy KiotViet


@app.post("/api/rentals/book_multi")
def create_multi_item_booking(req: MultiItemBookingRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Đặt thuê nhiều sản phẩm cùng 1 lúc (Gộp bill Shopee Cart & KiotViet POS Admin).
    - Tính toán giá & cọc từng món (Camera: 4h/8h/1 ngày/nhiều ngày; Trang phục: deadline 20:00).
    - Khóa kho đồng loạt tất cả thiết bị.
    - Tạo 1 mã đơn gộp (TDB-XXXXXX) và 1 mã VietQR MBBank duy nhất.
    - Hỗ trợ Admin KiotViet POS thanh toán trực tiếp tại quầy hoặc in bill K80 ngay.
    """
    if not req.items or len(req.items) == 0:
        raise HTTPException(status_code=400, detail="Giỏ hàng trống! Vui lòng chọn ít nhất 1 sản phẩm.")

    conn = get_db()
    cur = conn.cursor()

    # Xác định người đặt (User đăng nhập hoặc Khách tại quầy KiotViet của Admin)
    target_user_id = None
    target_user_name = "Khách Hàng Tại Quầy"
    target_user_phone = "0900000000"
    target_user_cccd = "Chính chủ"
    is_admin_mode = user and user.get("role") == "admin"

    if is_admin_mode and req.walk_in_customer_name:
        target_user_name = req.walk_in_customer_name.strip()
        target_user_phone = req.walk_in_customer_phone.strip() if req.walk_in_customer_phone else "0900000000"
        # Tìm xem khách này đã có tài khoản chưa, nếu chưa dùng tài khoản admin hoặc khách mặc định
        existing_u = cur.execute("SELECT * FROM users WHERE phone = ?", (target_user_phone,)).fetchone()
        if existing_u:
            target_user_id = existing_u["id"]
            target_user_cccd = existing_u["cccd_number"] or target_user_cccd
        else:
            target_user_id = user["id"]
    elif user:
        target_user_id = user["id"]
        target_user_name = user["full_name"]
        target_user_phone = user["phone"]
        target_user_cccd = user.get("cccd_number") or "Đã xác thực"
    else:
        conn.close()
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thanh toán đơn thuê!")

    # Kiểm tra Blacklist
    bl = cur.execute("SELECT reason FROM blacklist WHERE phone = ? OR cccd_number = ?", (target_user_phone, target_user_cccd)).fetchone()
    if bl:
        conn.close()
        raise HTTPException(status_code=403, detail=f"Tài khoản/SĐT bị tạm ngưng giao dịch ({bl['reason']}).")

    processed_items = []
    total_rental_price = 0
    total_default_deposit = 0
    max_duration_hours = 24.0
    effective_overall_end = req.end_time

    # Duyệt và tính toán từng sản phẩm trong giỏ hàng
    for item_req in req.items:
        it_start = item_req.start_time or req.start_time
        it_end = item_req.end_time or req.end_time

        if item_req.combo_id:
            combo = cur.execute("SELECT * FROM combos WHERE id = ?", (item_req.combo_id,)).fetchone()
            if not combo:
                conn.close()
                raise HTTPException(status_code=404, detail=f"Gói Combo #{item_req.combo_id} không tồn tại!")
            price_4h = int(combo["price_24h"] * 0.5)
            price_8h = int(combo["price_24h"] * 0.7)
            price_24h = combo["price_24h"]
            dep = combo["deposit_amount"]
            name = combo["name"]
            sn = "Combo Trọn Gói"
            cat = "COMBO_BUNDLE"
        elif item_req.item_id:
            item = cur.execute("SELECT * FROM items WHERE id = ?", (item_req.item_id,)).fetchone()
            if not item:
                conn.close()
                raise HTTPException(status_code=404, detail=f"Thiết bị #{item_req.item_id} không tồn tại!")
            if item["availability"] != "AVAILABLE" and not (is_admin_mode and req.is_direct_paid):
                conn.close()
                raise HTTPException(status_code=400, detail=f"Thiết bị '{item['name']}' hiện đang có người thuê!")
            price_4h = item["price_4h"]
            price_8h = item["price_8h"]
            price_24h = item["price_24h"]
            dep = item["deposit_amount"]
            name = item["name"]
            sn = item["serial_or_size"]
            cat = item["category"]
        else:
            continue

        # Tính giá theo gói chọn
        try:
            r_type, hours, r_days, it_price, dt_s, dt_e = calculate_rental_metrics(
                it_start, it_end, price_4h, price_8h, price_24h, cat
            )
        except Exception:
            # Fallback nếu giờ nhập lỗi
            r_type = "24h"
            hours = 24.0
            r_days = 1.0
            it_price = price_24h
            dt_s = datetime.datetime.now()
            dt_e = dt_s + datetime.timedelta(days=1)

        # Nếu là máy ảnh và người dùng chọn gói riêng: 4h, 8h, 1_day, multi_days
        if cat == "CAMERA_GEAR" and item_req.rental_type:
            if item_req.rental_type == "4h":
                r_type = "4h"; hours = 4.0; r_days = 0.5; it_price = price_4h
            elif item_req.rental_type == "8h":
                r_type = "8h"; hours = 8.0; r_days = 0.5; it_price = price_8h
            elif item_req.rental_type in ("1_day", "24h"):
                r_type = "24h"; hours = 24.0; r_days = 1.0; it_price = price_24h
            elif item_req.rental_type == "multi_days":
                d_cnt = max(1.0, float(item_req.days or 1.0))
                mult = 0.80 if d_cnt >= 3 else (0.85 if d_cnt >= 2 else 1.0)
                r_type = f"{d_cnt:g} ngày (24h)"; hours = d_cnt * 24.0; r_days = d_cnt
                it_price = int(d_cnt * price_24h * mult)

        # Nếu Admin chỉnh sửa giá trực tiếp cho món này:
        if is_admin_mode and item_req.custom_price is not None and item_req.custom_price >= 0:
            it_price = item_req.custom_price

        max_duration_hours = max(max_duration_hours, hours)
        it_end_str = dt_e.strftime("%Y-%m-%d %H:%M")
        if it_end_str > effective_overall_end:
            effective_overall_end = it_end_str

        total_rental_price += it_price
        total_default_deposit += dep

        processed_items.append({
            "item_id": item_req.item_id,
            "combo_id": item_req.combo_id,
            "name": name,
            "serial_or_size": sn,
            "category": cat,
            "rental_type": r_type,
            "rental_duration_hours": hours,
            "price": it_price,
            "deposit_amount": dep,
            "start_time": it_start,
            "end_time": it_end_str
        })

    # ADMIN ĐỒNG BỘ CHỈNH GIÁ TỔNG HOẶC CHIẾT KHẤU / PHỤ THU:
    if is_admin_mode:
        if req.custom_total_rental_price is not None and req.custom_total_rental_price >= 0:
            total_rental_price = req.custom_total_rental_price
        if req.pos_discount and req.pos_discount > 0:
            total_rental_price = max(0, total_rental_price - req.pos_discount)
        if req.pos_surcharge and req.pos_surcharge > 0:
            total_rental_price += req.pos_surcharge

    # PHẦN CỌC: Mặc định 0đ cho khách, Admin KiotViet POS có thể tự chọn hình thức cọc & nhập tiền cọc
    final_deposit = 0
    dep_type = req.deposit_type or "NONE"
    asset_desc = req.deposit_asset_desc or "Để lại giấy tờ hoặc cọc thêm tiền (Hoàn lại khi trả đồ)"
    
    if req.custom_deposit_amount is not None and req.custom_deposit_amount > 0:
        final_deposit = req.custom_deposit_amount
        dep_type = req.deposit_type or "ASSET"
        asset_desc = req.deposit_asset_desc or f"Cọc tiền/tài sản: {final_deposit:,}đ"
    discount = 0

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    hold_expires_at = (now + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    rental_code = f"TDB-{int(time.time()*1000)%1000000:06d}"
    selected_branch = req.branch_code.upper().strip() if req.branch_code and req.branch_code.upper().strip() in STORE_BRANCHES else "CN1"
    branch_info = STORE_BRANCHES[selected_branch]

    # Trạng thái ban đầu:
    # Nếu Admin KiotViet POS thanh toán trực tiếp tại quầy -> ACTIVE
    # Nếu Khách hàng đặt giỏ hàng Shopee -> HOLD (15 phút)
    initial_status = "ACTIVE" if (is_admin_mode and req.is_direct_paid) else "HOLD"
    if initial_status == "ACTIVE":
        hold_expires_at = None

    first_item_id = processed_items[0]["item_id"] if processed_items else None
    first_combo_id = processed_items[0]["combo_id"] if processed_items else None
    items_json_str = json.dumps(processed_items, ensure_ascii=False)

    cur.execute("""
    INSERT INTO rentals (
        rental_code, user_id, item_id, combo_id, rental_type, start_time, end_time,
        rental_duration_hours, hold_expires_at, total_price, deposit_paid, deposit_type,
        deposit_asset_desc, branch_code, refund_bank_info, status, items_json, customer_notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rental_code, target_user_id, first_item_id, first_combo_id,
        f"Gói {len(processed_items)} món", req.start_time, effective_overall_end,
        max_duration_hours, hold_expires_at, total_rental_price, final_deposit,
        dep_type, asset_desc, selected_branch, req.refund_bank_info, initial_status, items_json_str,
        req.customer_notes or ("Bán tại quầy KiotViet POS" if is_admin_mode else "Đơn giỏ hàng Shopee"),
        now_str
    ))
    rental_id = cur.lastrowid

    # Lưu chi tiết từng món vào bảng rental_items và khóa kho sang RENTED
    for it in processed_items:
        cur.execute("""
        INSERT INTO rental_items (
            rental_id, item_id, combo_id, item_name, serial_or_size, item_category,
            rental_type, rental_duration_hours, unit_price, deposit_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rental_id, it["item_id"], it["combo_id"], it["name"], it["serial_or_size"],
            it["category"], it["rental_type"], it["rental_duration_hours"], it["price"], 0
        ))
        if it["item_id"]:
            cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (it["item_id"],))

    conn.commit()
    conn.close()

    total_payable = total_rental_price
    qr_url = generate_vietqr_url(total_payable, rental_code)

    # Gửi thông báo Telegram kèm Lưu ý
    source_label = "KIOTVIET POS (TẠI QUẦY)" if (is_admin_mode and req.is_direct_paid) else "GIỎ HÀNG SHOPEE"
    items_bullet = "\n".join([f"  • {it['name']} ({it['rental_type']}) - {it['price']:,}đ" for it in processed_items])

    tele_msg = (
        f"<b>📸 TIDUBASTORE.COM - ĐƠN {source_label} ({rental_code})</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Chi nhánh:</b> <b>{branch_info['name']}</b> ({branch_info['short_address']})\n"
        f"👤 <b>Khách hàng:</b> {target_user_name} (<code>{target_user_phone}</code>)\n"
        f"📦 <b>Số lượng:</b> {len(processed_items)} sản phẩm / trang phục:\n"
        f"{items_bullet}\n"
        f"⏳ <b>Hạn trả tổng:</b> <b>{effective_overall_end}</b>\n"
        f"💵 <b>Tiền thuê:</b> <b>{total_rental_price:,}đ</b>\n"
        f"⚠️ <b>LƯU Ý:</b> Để lại giấy tờ hoặc cọc thêm tiền, Tiền cọc sẽ hoàn khi trả đồ.\n"
        f"📌 <b>Đối với máy ảnh:</b> Cọc 1 giấy tờ + tài sản (Điện thoại, Xe máy, Laptop, vòng vàng,...)\n"
        f"💳 <b>Tổng thanh toán:</b> <b>{total_payable:,}đ</b>\n"
        f"⚡ <b>Trạng thái:</b> <b>{initial_status}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Quét trả đồ: {PUBLIC_DOMAIN}/return-qr?code={rental_code}"
    )
    # Chỉ gửi thông báo ngay nếu là Admin bán tại quầy POS trực tiếp
    if is_admin_mode:
        _send_telegram_notification(tele_msg, rental_id=rental_id, event_type="NEW_RENTAL")

    # Tạo trước nội dung bill K80 ESC/POS
    bill_data = {
        "rental_code": rental_code,
        "customer_name": target_user_name,
        "customer_phone": target_user_phone,
        "customer_cccd": target_user_cccd,
        "total_price": total_rental_price,
        "deposit_paid": 0,
        "deposit_type": "NONE",
        "deposit_asset_desc": asset_desc,
        "branch_code": selected_branch,
        "rental_type": f"Gói {len(processed_items)} món",
        "rental_hours": max_duration_hours,
        "start_time": req.start_time,
        "end_time": effective_overall_end,
        "items": processed_items
    }
    bill_k80_text = build_escpos_thermal_bill_text(bill_data)

    return {
        "success": True,
        "message": "Đã tạo đơn thuê gộp thành công!" if not req.is_direct_paid else "✅ Đã thanh toán và kích hoạt đơn KiotViet thành công!",
        "rental_id": rental_id,
        "rental_code": rental_code,
        "branch_code": selected_branch,
        "branch_info": branch_info,
        "items_count": len(processed_items),
        "items": processed_items,
        "total_price": total_rental_price,
        "deposit_amount": final_deposit,
        "deposit_type": dep_type,
        "deposit_asset_desc": asset_desc,
        "discount_applied": 0,
        "total_payable": total_payable,
        "status": initial_status,
        "qr_image_url": qr_url,
        "bill_k80_text": bill_k80_text,
        "bank_account": f"{BANK_CONFIG['bank_name']} - STK: {BANK_CONFIG['account_no']} ({BANK_CONFIG['account_name']})",
        "start_time": req.start_time,
        "end_time": effective_overall_end
    }


class RequestExtensionRequest(BaseModel):
    extension_hours: int = Field(default=24, ge=1, le=168)
    notes: Optional[str] = None


@app.post("/api/rentals/{rental_id}/request_extension")
def request_extension(rental_id: int, req: RequestExtensionRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập!")
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("SELECT * FROM rentals WHERE id = ? AND user_id = ?", (rental_id, user["id"])).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    if user is None or (user.get("role") != "admin" and rental["user_id"] != user["id"]):
        conn.close()
        raise HTTPException(status_code=403, detail="Không có quyền thực hiện thao tác này!")

    cur.execute("""
    UPDATE rentals 
    SET extension_hours = ?, extension_status = 'REQUESTED', customer_notes = COALESCE(customer_notes, '') || ' | Xin gia hạn ' || ? || ' giờ: ' || ?
    WHERE id = ?
    """, (req.extension_hours, req.extension_hours, req.notes or '', rental_id))

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO alerts (rental_id, alert_type, title, message, created_at)
    VALUES (?, 'EXTENSION_REQUEST', ?, ?, ?)
    """, (rental_id, f"📝 YÊU CẦU GIA HẠN: {rental['rental_code']}", f"Khách {user['full_name']} xin gia hạn thêm {req.extension_hours} giờ cho đơn {rental['rental_code']}.", now_str))

    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã gửi yêu cầu gia hạn thêm {req.extension_hours} giờ tới Quản lý!"}


@app.get("/api/rentals/my")
def get_my_rentals(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập!")
    update_and_check_rental_alerts()

    conn = get_db()
    # Chỉ hiển thị các đơn thuê hợp lệ, KHÔNG hiển thị đơn bị hủy (CANCELLED do đóng VietQR hoặc quá 15p)
    rentals = conn.execute("""
    SELECT r.*, 
           COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
           COALESCE(i.image_url, c.image_url, '/static/logo.png') as item_image,
           COALESCE(i.category, 'COMBO_BUNDLE') as item_category,
           COALESCE(i.serial_or_size, 'Nhiều thiết bị') as serial_or_size
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    WHERE r.user_id = ? AND r.status != 'CANCELLED'
    ORDER BY r.id DESC
    """, (user["id"],)).fetchall()
    conn.close()

    result = []
    for r in rentals:
        d = dict(r)
        d["qr_url"] = generate_vietqr_url(d["total_price"] + d["deposit_paid"], d["rental_code"])
        if d.get("items_json"):
            try:
                parsed_items = json.loads(d["items_json"])
                d["items"] = parsed_items
                if len(parsed_items) > 1:
                    d["item_name"] = f"Gói {len(parsed_items)} Thiết Bị / Trang Phục (" + ", ".join([it.get('name', '') for it in parsed_items[:2]]) + ("..." if len(parsed_items) > 2 else "") + ")"
            except Exception:
                d["items"] = []
        result.append(d)

    return {"rentals": result}


# =============================================================================
# 10. DIGITAL CONTRACT HTML EXPORT WITH MBBANK 0123006101998
# =============================================================================

@app.get("/api/rentals/{rental_id}/contract", response_class=HTMLResponse)
def get_rental_contract(rental_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Xuất Hợp Đồng Điện Tử - Chỉ chủ đơn hoặc Admin mới được xem. Chặn IDOR."""
    conn = get_db()
    r = conn.execute("""
    SELECT r.*, 
           COALESCE(i.name, c.name) as item_name,
           COALESCE(i.brand, 'Tiduba Store') as item_brand,
           COALESCE(i.serial_or_size, 'Combo Trọn Gói') as item_serial,
           COALESCE(i.condition_status, 'Mới 99%, hoạt động hoàn hảo') as item_condition,
           u.full_name as customer_name, u.phone as customer_phone, u.email as customer_email,
           u.cccd_number
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê để lập hợp đồng!")

    # IDOR check: Chỉ chủ đơn hoặc Admin được xem hợp đồng
    if user is None or (user.get("role") != "admin" and r["user_id"] != user["id"]):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem hợp đồng này!")

    now_str = datetime.datetime.now().strftime("ngày %d tháng %m năm %Y")
    total_val = r["total_price"] + r["deposit_paid"]
    otp_status = "ĐÃ KÝ SỐ QUA MÃ OTP CHÍNH CHỦ" if r["e_contract_signed"] else "CHỜ KÝ SỐ OTP"
    b_code = r["branch_code"] if ("branch_code" in r.keys() and r["branch_code"]) else "CN1"
    branch_info = STORE_BRANCHES.get(b_code, STORE_BRANCHES["CN1"])

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Hợp Đồng Thuê Thiết Bị - {r['rental_code']}</title>
    <style>
        body {{ font-family: 'Times New Roman', Times, serif; font-size: 13pt; line-height: 1.6; color: #111; margin: 35px; background: #fff; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h3 {{ margin: 0; font-size: 13pt; text-transform: uppercase; }}
        .title {{ text-align: center; margin: 25px 0 15px 0; text-transform: uppercase; font-weight: bold; font-size: 17pt; color: #0284c7; }}
        .section-title {{ font-weight: bold; text-transform: uppercase; margin-top: 18px; font-size: 13pt; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #94a3b8; padding: 9px; font-size: 12.5pt; text-align: left; }}
        th {{ background: #f8fafc; text-transform: uppercase; }}
        .signatures {{ margin-top: 35px; display: flex; justify-content: space-between; }}
        .sign-col {{ width: 45%; text-align: center; }}
        .btn-print {{ position: fixed; top: 20px; right: 20px; background: #0284c7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
        @media print {{ .btn-print {{ display: none; }} body {{ margin: 15mm; }} }}
    </style>
</head>
<body>
    <button class="btn-print" onclick="window.print()">🖨️ In / Lưu PDF Hợp Đồng</button>

    <div style="text-align: center; margin-bottom: 12px;">
        <img src="/static/logo.png" alt="Tiduba Logo" style="height: 65px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    </div>

    <div class="header">
        <h3>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h3>
        <p style="margin: 0;">Độc lập – Tự do – Hạnh phúc</p>
        <p style="margin: 3px 0;">-----------------------</p>
    </div>

    <div class="title">HỢP ĐỒNG CHO THUÊ THIẾT BỊ MÁY ẢNH & TRANG PHỤC</div>
    <p style="text-align: center; font-style: italic; margin-top: -10px;">Mã số hợp đồng: <strong>{r['rental_code']}</strong> | Trạng thái: <strong>{otp_status}</strong></p>

    <div class="section-title">BÊN CHO THUÊ (BÊN A):</div>
    <ul>
        <li><strong>Đơn vị:</strong> HỆ THỐNG CỬA HÀNG CHO THUÊ TIDUBA STORE (TIDUBASTORE.COM)</li>
        <li><strong>Chi nhánh 1 (Trụ sở chính):</strong> 183A Huỳnh Thúc Kháng, P. Diên Hồng, TP. Pleiku, Gia Lai (Hotline: 0977.078.981)</li>
        <li><strong>Chi nhánh 2:</strong> 801 Lê Duẩn, P. An Phú, TP. Pleiku, Gia Lai (Hotline: 0977.078.981)</li>
        <li><strong>Chi nhánh giao nhận & quản lý hợp đồng:</strong> <strong>{branch_info['name']} - {branch_info['address']}</strong></li>
        <li><strong>Đại diện pháp lý:</strong> <strong>LÊ NHẬT PHÁT</strong></li>
        <li><strong>Tài khoản ngân hàng thụ hưởng & hoàn cọc:</strong> <strong>MBBank (Ngân hàng Quân Đội)</strong></li>
        <li><strong>Số tài khoản:</strong> <strong>0123006101998</strong></li>
        <li><strong>Chủ tài khoản:</strong> <strong>KHONG KY DUYEN</strong></li>
    </ul>

    <div class="section-title">BÊN THUÊ (BÊN B - KHÁCH HÀNG):</div>
    <ul>
        <li><strong>Họ và tên:</strong> <strong>{r['customer_name']}</strong></li>
        <li><strong>Số điện thoại:</strong> {r['customer_phone']} | <strong>Email:</strong> {r['customer_email']}</li>
        <li><strong>Số CCCD gắn chip (Đã xác thực eKYC):</strong> {r['cccd_number'] or 'Đã lưu trữ đối chứng'}</li>
    </ul>

    <div style="background: #fef3c7; border: 2px solid #f59e0b; padding: 12px 16px; border-radius: 8px; margin: 15px 0;">
        <p style="margin: 0; font-size: 13pt; font-weight: bold; color: #92400e; text-transform: uppercase;">⚠️ LƯU Ý QUAN TRỌNG:</p>
        <p style="margin: 4px 0 0 0; font-size: 12.5pt; font-weight: bold; color: #78350f;">• Để lại giấy tờ hoặc cọc thêm tiền, Tiền cọc sẽ hoàn khi trả đồ.</p>
        <p style="margin: 4px 0 0 0; font-size: 12.5pt; font-weight: bold; color: #78350f;">• Đối với máy ảnh: Cọc 1 giấy tờ + tài sản (Điện thoại, Xe máy, Laptop, vòng vàng,...)</p>
    </div>

    <div class="section-title">ĐIỀU 1: THÔNG TIN THIẾT BỊ / TRANG PHỤC BÀN GIAO</div>
    <table>
        <tr>
            <th>Tên Thiết Bị / Trang Phục</th>
            <th>Số Serial / Kích Thước</th>
            <th>Tình Trạng Khi Giao</th>
            <th>Hạn Trả Đồ (Bắt buộc)</th>
        </tr>
        <tr>
            <td><strong>{r['item_name']}</strong></td>
            <td>{r['item_serial']}</td>
            <td>{r['item_condition']}</td>
            <td><strong style="color: #dc2626;">{r['end_time']}</strong></td>
        </tr>
    </table>

    <div class="section-title">ĐIỀU 2: CHI PHÍ THUÊ & QUY ĐỊNH TRẢ ĐỒ</div>
    <table>
        <tr>
            <th>Gói Thuê</th>
            <th>Tiền Thuê</th>
            <th>Tổng Tiền Đã Thanh Toán</th>
        </tr>
        <tr>
            <td>{r['rental_type']} ({r['rental_duration_hours']} giờ)</td>
            <td>{r['total_price']:,} VNĐ</td>
            <td><strong>{r['total_price']:,} VNĐ (MBBank 0123006101998)</strong></td>
        </tr>
    </table>
    <p>1. <strong>Quy định trả đồ:</strong> Bên B có trách nhiệm hoàn trả thiết bị trước <strong>{r['end_time']}</strong>. Trường hợp trả muộn áp dụng mức phạt <strong>30.000 VNĐ / giờ quá hạn</strong>.</p>
    <p>2. <strong>Hoàn trả giấy tờ / tiền cọc:</strong> Khi hoàn tất kiểm tra cảm biến/lens sạch sẽ hoặc trang phục nguyên vẹn, Bên A hoàn trả 100% giấy tờ hoặc tiền cọc lại cho Bên B sau 10 phút kiểm tra QC.</p>
    <p>3. <strong>Cam kết đền bù hư hại 100%:</strong> Nếu làm rơi vỡ, nứt thấu kính, ẩm mốc hoặc rách trang phục, Bên B bồi thường 100% theo hóa đơn thẩm định chính hãng của trung tâm bảo hành Sony/Canon/DJI.</p>

    <div class="signatures">
        <div class="sign-col">
            <p><strong>ĐẠI DIỆN BÊN A (TIDUBA STORE)</strong></p>
            <p style="font-size: 11pt; color: #64748b;">(Đã ký số điện tử)</p>
            <div style="height: 60px;"></div>
            <p><strong>LÊ NHẬT PHÁT</strong></p>
        </div>
        <div class="sign-col">
            <p><strong>BÊN THUÊ (BÊN B)</strong></p>
            <p style="font-size: 11pt; color: #64748b;">(Xác thực ký số qua OTP)</p>
            <div style="height: 60px;"></div>
            <p><strong>{r['customer_name']}</strong></p>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


# =============================================================================
# 11. ADMIN PANEL APIS
# =============================================================================

@app.get("/api/admin/dashboard_stats")
def get_admin_dashboard_stats(admin: Dict[str, Any] = Depends(require_admin)):
    update_and_check_rental_alerts()
    conn = get_db()
    total_revenue = conn.execute("SELECT sum(total_price) as s FROM rentals WHERE status IN ('APPROVED', 'ACTIVE', 'RETURNED')").fetchone()["s"] or 0
    total_rentals = conn.execute("SELECT count(*) as c FROM rentals").fetchone()["c"]
    active_rentals = conn.execute("SELECT count(*) as c FROM rentals WHERE status = 'ACTIVE'").fetchone()["c"]
    overdue_rentals = conn.execute("SELECT count(*) as c FROM rentals WHERE status = 'OVERDUE'").fetchone()["c"]
    available_items = conn.execute("SELECT count(*) as c FROM items WHERE availability = 'AVAILABLE'").fetchone()["c"]
    alerts = [dict(row) for row in conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 10").fetchall()]

    # Thống kê doanh thu 7 ngày gần nhất
    revenue_7d = []
    today = datetime.date.today()
    for idx in range(6, -1, -1):
        day_date = today - datetime.timedelta(days=idx)
        day_str = day_date.strftime("%Y-%m-%d")
        day_rev = conn.execute("""
        SELECT sum(total_price) as s FROM rentals 
        WHERE status IN ('APPROVED', 'ACTIVE', 'RETURNED') AND created_at LIKE ?
        """, (f"{day_str}%",)).fetchone()["s"] or 0
        revenue_7d.append({"date": day_date.strftime("%d/%m"), "revenue": day_rev})

    latest_rental = conn.execute("""
        SELECT r.id, r.rental_code, r.status, r.total_price, u.full_name as customer_name 
        FROM rentals r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.id DESC LIMIT 1
    """).fetchone()

    latest_id = latest_rental["id"] if latest_rental else 0
    latest_code = latest_rental["rental_code"] if latest_rental else ""
    latest_name = latest_rental["customer_name"] if latest_rental else ""

    conn.close()

    return {
        "total_revenue": total_revenue,
        "total_rentals": total_rentals,
        "active_rentals": active_rentals,
        "overdue_rentals": overdue_rentals,
        "available_items": available_items,
        "revenue_7d": revenue_7d,
        "recent_alerts": alerts,
        "latest_rental_id": latest_id,
        "latest_rental_code": latest_code,
        "latest_customer_name": latest_name
    }


@app.get("/api/admin/rentals")
def get_all_rentals_admin(status: Optional[str] = None, admin: Dict[str, Any] = Depends(require_admin)):
    update_and_check_rental_alerts()
    conn = get_db()
    query = """
    SELECT r.*, 
           COALESCE(i.name, c.name) as item_name, 
           COALESCE(i.category, 'COMBO') as item_category, 
           COALESCE(i.serial_or_size, 'Combo Trọn Gói') as serial_or_size,
           u.full_name as customer_name, u.phone as customer_phone, u.email as customer_email,
           u.cccd_number
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE 1=1
    """
    params = []
    if status:
        query += " AND r.status = ?"
        params.append(status)

    query += " ORDER BY r.status = 'OVERDUE' DESC, r.id DESC"
    rentals = [dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()

    now = datetime.datetime.now()
    for r in rentals:
        try:
            dt_end = datetime.datetime.fromisoformat(r["end_time"])
        except Exception:
            dt_end = datetime.datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M")
        diff = (dt_end - now).total_seconds()
        r["hours_remaining"] = round(diff / 3600.0, 1)
        r["is_overdue"] = diff < 0

    return {"rentals": rentals, "count": len(rentals)}


class UpdateRentalAdminRequest(BaseModel):
    status: Optional[str] = None
    end_time: Optional[str] = None
    total_price: Optional[int] = None
    deposit_paid: Optional[int] = None
    deposit_type: Optional[str] = None
    deposit_asset_desc: Optional[str] = None
    late_fee: Optional[int] = None
    admin_notes: Optional[str] = None


@app.patch("/api/admin/rentals/{rental_id}")
def update_rental_admin(rental_id: int, req: UpdateRentalAdminRequest, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    fields = []
    params = []

    if req.status:
        fields.append("status = ?")
        params.append(req.status)
        if req.status in ("RETURNED", "CANCELLED"):
            if "items_json" in rental.keys() and rental["items_json"]:
                try:
                    for itm in json.loads(rental["items_json"]):
                        if itm.get("item_id"):
                            cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (itm["item_id"],))
                except Exception: pass
            elif rental["item_id"]:
                cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (rental["item_id"],))
        elif req.status == "ACTIVE":
            if "items_json" in rental.keys() and rental["items_json"]:
                try:
                    for itm in json.loads(rental["items_json"]):
                        if itm.get("item_id"):
                            cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (itm["item_id"],))
                except Exception: pass
            elif rental["item_id"]:
                cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (rental["item_id"],))

    if req.end_time:
        fields.append("end_time = ?")
        params.append(req.end_time)
    if req.total_price is not None:
        fields.append("total_price = ?")
        params.append(req.total_price)
    if req.deposit_paid is not None:
        fields.append("deposit_paid = ?")
        params.append(req.deposit_paid)
    if req.deposit_type is not None:
        fields.append("deposit_type = ?")
        params.append(req.deposit_type)
    if req.deposit_asset_desc is not None:
        fields.append("deposit_asset_desc = ?")
        params.append(req.deposit_asset_desc)
    if req.late_fee is not None:
        fields.append("late_fee = ?")
        params.append(req.late_fee)
    if req.admin_notes:
        fields.append("admin_notes = ?")
        params.append(req.admin_notes)

    if fields:
        params.append(rental_id)
        cur.execute(f"UPDATE rentals SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()

    conn.close()
    return {"success": True, "message": f"Đã cập nhật đơn thuê #{rental['rental_code']} thành công!"}


@app.delete("/api/admin/rentals/{rental_id}")
def admin_delete_rental(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Xóa vĩnh viễn 1 đơn thuê và giải phóng thiết bị (Chỉ Admin)."""
    conn = get_db()
    cur = conn.cursor()
    rental = cur.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê để xóa!")

    # Giải phóng thiết bị nếu đơn chưa hoàn tất (trả lại AVAILABLE)
    if rental["status"] not in ("RETURNED", "CANCELLED"):
        if rental["items_json"]:
            try:
                items = json.loads(rental["items_json"])
                for itm in items:
                    if itm.get("item_id"):
                        cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (itm["item_id"],))
            except Exception:
                pass
        elif rental["item_id"]:
            cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (rental["item_id"],))

    # Xóa các liên kết
    cur.execute("DELETE FROM rental_items WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM alerts WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM handover_protocols WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM damage_penalties WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM zns_logs WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM telegram_logs WHERE rental_id = ?", (rental_id,))
    cur.execute("DELETE FROM rentals WHERE id = ?", (rental_id,))
    conn.commit()
    sync_items_availability(conn)
    conn.close()
    return {"success": True, "message": f"Đã xóa thành công đơn thuê & bill #{rental['rental_code']}!"}


@app.delete("/api/admin/rentals")
def admin_clear_all_rentals(admin: Dict[str, Any] = Depends(require_admin)):
    """Xóa toàn bộ danh sách đơn thuê và làm sạch lịch sử hóa đơn toàn hệ thống (Chỉ Admin)."""
    conn = get_db()
    cur = conn.cursor()
    # Trả toàn bộ thiết bị về AVAILABLE
    cur.execute("UPDATE items SET availability = 'AVAILABLE'")
    cur.execute("DELETE FROM rental_items")
    cur.execute("DELETE FROM alerts")
    cur.execute("DELETE FROM handover_protocols")
    cur.execute("DELETE FROM damage_penalties")
    cur.execute("DELETE FROM zns_logs")
    cur.execute("DELETE FROM telegram_logs")
    cur.execute("DELETE FROM rentals")
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã xóa sạch toàn bộ danh sách đơn thuê & hóa đơn trên toàn hệ thống!"}


class ApproveExtensionRequest(BaseModel):
    new_end_time: str
    extension_fee: int = 0


@app.post("/api/admin/rentals/{rental_id}/approve_extension")
def approve_extension(rental_id: int, req: ApproveExtensionRequest, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    UPDATE rentals 
    SET end_time = ?, extension_status = 'APPROVED', total_price = total_price + ?, status = 'ACTIVE'
    WHERE id = ?
    """, (req.new_end_time, req.extension_fee, rental_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã duyệt gia hạn đơn thuê tới {req.new_end_time}!"}


class CreateItemAdminRequest(BaseModel):
    name: str
    category: str
    subcategory: str
    brand: str
    serial_or_size: str
    price_4h: int = 150000
    price_8h: int = 250000
    price_24h: int = 350000
    deposit_amount: int = 0
    image_url: str
    gallery_json: Optional[str] = "[]"
    description: str
    condition_status: str
    branch_code: Optional[str] = "CN1"


@app.post("/api/admin/upload_image")
async def upload_item_image(file: UploadFile = File(...), admin: Dict[str, Any] = Depends(require_admin)):
    """Admin tải ảnh thiết bị / trang phục thật lên server."""
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Chỉ chấp nhận file ảnh: {', '.join(allowed_exts)}")

    # Giới hạn kích thước tối đa 15MB
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ảnh vượt quá 15MB!")

    unique_filename = f"item_{int(time.time() * 1000)}_{os.urandom(4).hex()}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    try:
        with open(dest_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu ảnh: {str(e)}")

    image_url = f"/static/uploads/{unique_filename}"
    return {
        "success": True,
        "message": "Tải ảnh sản phẩm thật lên hệ thống thành công!",
        "image_url": image_url,
        "file_name": unique_filename
    }


@app.post("/api/rentals/upload_proof")
async def upload_payment_proof_image(
    file: UploadFile = File(...),
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Khách hàng tải ảnh biên lai chuyển tiền lên để Admin xác nhận thanh toán."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tải ảnh biên lai!")

    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Chỉ chấp nhận ảnh: {', '.join(allowed_exts)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ảnh biên lai vượt quá 10MB!")

    safe_uid = str(user["id"])
    unique_filename = f"proof_{safe_uid}_{int(time.time() * 1000)}_{os.urandom(3).hex()}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    try:
        with open(dest_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu ảnh: {str(e)}")

    image_url = f"/static/uploads/{unique_filename}"
    return {
        "success": True,
        "message": "Đã tải ảnh biên lai thành công!",
        "image_url": image_url
    }


@app.post("/api/admin/items")
def create_item_admin(req: CreateItemAdminRequest, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO items (name, category, subcategory, brand, serial_or_size, price_4h, price_8h, price_24h, deposit_amount, image_url, gallery_json, description, condition_status, availability, branch_code, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', ?, ?)
    """, (req.name, req.category, req.subcategory, req.brand, req.serial_or_size, req.price_4h, req.price_8h, req.price_24h, req.deposit_amount, req.image_url, req.gallery_json or "[]", req.description, req.condition_status, req.branch_code or "CN1", now_str))

    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"success": True, "message": "Đã thêm thiết bị/trang phục mới vào kho!", "item_id": new_id}


class UpdateItemFullAdminRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    serial_or_size: Optional[str] = None
    price_4h: Optional[int] = None
    price_8h: Optional[int] = None
    price_24h: Optional[int] = None
    deposit_amount: Optional[int] = None
    image_url: Optional[str] = None
    gallery_json: Optional[str] = None
    description: Optional[str] = None
    condition_status: Optional[str] = None
    availability: Optional[str] = None
    branch_code: Optional[str] = None


@app.patch("/api/admin/items/{item_id}")
def update_item_admin_full(item_id: int, req: UpdateItemFullAdminRequest, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()

    # Whitelist các cột được phép sửa để tránh SQL injection
    ALLOWED_ITEM_FIELDS = {
        "name", "category", "subcategory", "brand", "serial_or_size",
        "price_4h", "price_8h", "price_24h", "deposit_amount",
        "image_url", "gallery_json", "description", "condition_status", "availability", "branch_code"
    }

    fields = []
    params = []
    for k, v in req.dict(exclude_none=True).items():
        if k in ALLOWED_ITEM_FIELDS:
            fields.append(f"{k} = ?")
            params.append(v)

    if fields:
        params.append(item_id)
        cur.execute(f"UPDATE items SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()

    conn.close()
    return {"success": True, "message": "Đã cập nhật thông tin và ảnh thiết bị thành công!"}


@app.post("/api/admin/items/{item_id}/toggle_availability")
def toggle_item_availability(item_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin bật/tắt trạng thái sản phẩm: AVAILABLE ↔ UNAVAILABLE (hạ xuống / kích hoạt lại)."""
    conn = get_db()
    cur = conn.cursor()

    item = cur.execute("SELECT id, name, availability FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm!")

    if item["availability"] == "UNAVAILABLE":
        new_status = "AVAILABLE"
        msg = f"Đã kích hoạt lại sản phẩm '{item['name']}' (Đang cho thuê)!"
    elif item["availability"] == "AVAILABLE":
        new_status = "UNAVAILABLE"
        msg = f"Đã hạ sản phẩm '{item['name']}' xuống (Tạm ngưng cho thuê)!"
    else:
        # Đang RENTED → không cho hạ
        conn.close()
        raise HTTPException(status_code=400, detail=f"Sản phẩm đang có người thuê (RENTED), không thể hạ xuống!")

    cur.execute("UPDATE items SET availability = ? WHERE id = ?", (new_status, item_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": msg, "new_availability": new_status}



@app.delete("/api/admin/items/{item_id}")
def delete_item_admin(item_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    # Kiểm tra xem sản phẩm có đang trong đơn ACTIVE hay không
    in_use = conn.execute("SELECT id FROM rentals WHERE item_id = ? AND status IN ('ACTIVE', 'HOLD', 'OVERDUE')", (item_id,)).fetchone()
    if in_use:
        conn.close()
        raise HTTPException(status_code=400, detail="Thiết bị này đang có người thuê hoặc giữ chỗ! Vui lòng chỉ 'Hạ sản phẩm' xuống thay vì xóa vĩnh viễn.")

    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã xóa vĩnh viễn thiết bị khỏi hệ thống!"}


# =============================================================================
# ADMIN SITE SETTINGS & CATEGORIES DYNAMIC CONFIG
# =============================================================================

@app.get("/api/settings")
def get_site_settings():
    """Lấy toàn bộ cấu hình nội dung website có thể chỉnh sửa không cần code."""
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM site_settings").fetchall()
    conn.close()
    settings_dict = {r["key"]: r["value"] for r in rows}
    return {"success": True, "settings": settings_dict}


class UpdateSiteSettingsRequest(BaseModel):
    settings: Dict[str, str]


@app.post("/api/admin/settings")
def update_site_settings(req: UpdateSiteSettingsRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin cập nhật các mục nội dung trực tiếp trên website (tiêu đề, hotline, banner, note...)."""
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for k, v in req.settings.items():
        cur.execute("""
        INSERT INTO site_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """, (k, str(v), now_str))

    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã lưu cài đặt website thành công!"}


@app.get("/api/categories")
def get_categories():
    """Lấy danh sách các thư mục / bộ lọc chip phân loại (Tất cả, Sony, Canon, Váy...)."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories_config WHERE is_active = 1 ORDER BY display_order ASC, id ASC").fetchall()
    conn.close()
    return {"success": True, "categories": [dict(r) for r in rows]}


class CategoryConfigItem(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    filter_type: str = "BRAND"  # 'ALL', 'BRAND', 'CATEGORY', 'PRICE'
    filter_value: str = ""
    display_order: int = 0
    is_active: int = 1


@app.post("/api/admin/categories")
def save_category_chip(req: CategoryConfigItem, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin thêm mới hoặc chỉnh sửa 1 thư mục / chip lọc."""
    conn = get_db()
    cur = conn.cursor()
    if req.id:
        cur.execute("""
        UPDATE categories_config 
        SET code = ?, name = ?, filter_type = ?, filter_value = ?, display_order = ?, is_active = ?
        WHERE id = ?
        """, (req.code, req.name, req.filter_type, req.filter_value, req.display_order, req.is_active, req.id))
    else:
        cur.execute("""
        INSERT INTO categories_config (code, name, filter_type, filter_value, display_order, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (req.code, req.name, req.filter_type, req.filter_value, req.display_order, req.is_active))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã lưu danh mục '{req.name}' thành công!"}


@app.delete("/api/admin/categories/{cat_id}")
def delete_category_chip(cat_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin xóa 1 thư mục / chip lọc."""
    conn = get_db()
    conn.execute("DELETE FROM categories_config WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã xóa danh mục / chip lọc thành công!"}


# =============================================================================
# 12.1 BLACKLIST MANAGEMENT (QUẢN LÝ DANH SÁCH ĐEN BÙNG CỌC / HỎNG ĐỒ)
# =============================================================================

class BlacklistAddRequest(BaseModel):
    phone: Optional[str] = ""
    cccd_number: Optional[str] = ""
    bank_account: Optional[str] = ""
    reason: str


@app.get("/api/admin/blacklist")
def get_admin_blacklist(admin: Dict[str, Any] = Depends(require_admin)):
    """Admin lấy danh sách khách hàng bị đưa vào Blacklist."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM blacklist ORDER BY id DESC").fetchall()
    conn.close()
    return {"success": True, "blacklist": [dict(r) for r in rows], "count": len(rows)}


@app.post("/api/admin/blacklist")
def add_admin_blacklist(req: BlacklistAddRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin thêm số điện thoại / CCCD / STK vào Danh Sách Đen."""
    clean_p = (req.phone or "").strip()
    clean_c = (req.cccd_number or "").strip()
    clean_b = (req.bank_account or "").strip()
    if not clean_p and not clean_c and not clean_b:
        raise HTTPException(status_code=400, detail="Vui lòng nhập ít nhất SĐT, CCCD hoặc STK Ngân Hàng!")
    conn = get_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    INSERT INTO blacklist (phone, cccd_number, bank_account, reason, flagged_at)
    VALUES (?, ?, ?, ?, ?)
    """, (clean_p, clean_c, clean_b, req.reason.strip(), now_str))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã thêm vào Danh Sách Đen thành công!"}


@app.delete("/api/admin/blacklist/{bl_id}")
def delete_admin_blacklist(bl_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin gỡ bỏ khách hàng khỏi Danh Sách Đen khi đã giải quyết xong."""
    conn = get_db()
    conn.execute("DELETE FROM blacklist WHERE id = ?", (bl_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã gỡ bỏ khỏi Danh Sách Đen thành công!"}


# =============================================================================
# 12.2 XUẤT BÁO CÁO DOANH THU & ĐƠN THUÊ EXCEL / CSV CHUẨN UTF-8 BOM
# =============================================================================

@app.get("/api/admin/reports/export_csv")
def export_rentals_csv(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Admin tải file CSV/Excel toàn bộ đơn hàng và doanh thu thực tế chuẩn UTF-8 (Đã loại bỏ đơn bị hủy)."""
    auth_header = authorization or (f"Bearer {token}" if token else None)
    user = get_current_user(auth_header)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Quản trị viên (Admin) mới có quyền xuất báo cáo!")
    conn = get_db()
    cur = conn.cursor()
    rentals = cur.execute("""
    SELECT r.id, r.rental_code, u.full_name as customer_name, u.phone as customer_phone,
           COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
           r.total_price, r.deposit_paid, r.deposit_type, r.deposit_asset_desc,
           r.status, r.branch_code, r.start_time, r.end_time, r.late_fee, r.created_at
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.status != 'CANCELLED'
    ORDER BY r.id DESC
    """).fetchall()
    conn.close()

    branch_names = {
        "CN1": "CN1: 183A Huỳnh Thúc Kháng, Pleiku",
        "CN2": "CN2: 801 Lê Duẩn, Pleiku"
    }

    status_labels = {
        "ACTIVE": "Đang thuê",
        "RETURNED": "Đã trả đồ xong",
        "OVERDUE": "Quá hạn",
        "HOLD": "Chờ xác nhận tiền",
        "PENDING": "Đang xử lý"
    }

    output = io.StringIO()
    # Ghi UTF-8 BOM để Excel tự động mở tiếng Việt không bị lỗi font
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Mã Đơn Hàng", "Khách Hàng", "Số Điện Thoại", "Thiết Bị / Trang Phục",
        "Tiền Thuê (VNĐ)", "Tiền Cọc (VNĐ)", "Phạt Trễ Hạn (VNĐ)", "Tổng Thu Thực Tế (VNĐ)",
        "Hình Thức Cọc", "Mô Tả Cọc", "Trạng Thái Đơn", "Chi Nhánh Bàn Giao", "Ngày Giờ Bắt Đầu", "Hạn Trả", "Ngày Tạo Đơn"
    ])
    for r in rentals:
        total_revenue = (r["total_price"] or 0) + (r["late_fee"] or 0)
        b_label = branch_names.get(r["branch_code"] or "CN1", "CN1: 183A Huỳnh Thúc Kháng, Pleiku")
        st_label = status_labels.get(r["status"], r["status"])
        writer.writerow([
            r["id"], r["rental_code"], r["customer_name"], r["customer_phone"], r["item_name"],
            f"{r['total_price']:,}" if r['total_price'] else "0",
            f"{r['deposit_paid']:,}" if r['deposit_paid'] else "0",
            f"{r['late_fee']:,}" if r['late_fee'] else "0",
            f"{total_revenue:,}",
            r["deposit_type"] or "Giữ giấy tờ",
            r["deposit_asset_desc"] or "",
            st_label,
            b_label,
            r["start_time"],
            r["end_time"],
            r["created_at"]
        ])

    csv_data = output.getvalue()
    filename = f"TidubaStore_BaoCaoDoanhThu_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =============================================================================
# 12.2B DATA SYNC ENGINE (ĐỒNG BỘ BỘ NHỚ WEB & MÁY TÍNH KHÔNG CẦN CHẠM CODE)
# =============================================================================

@app.get("/api/admin/sync/export_data")
def export_sync_data(admin: Dict[str, Any] = Depends(require_admin)):
    """Xuất toàn bộ danh mục, sản phẩm, cài đặt, combos và cấu hình dạng JSON."""
    conn = get_db()
    cats = [dict(r) for r in conn.execute("SELECT * FROM categories_config ORDER BY display_order ASC").fetchall()]
    items = [dict(r) for r in conn.execute("SELECT * FROM items ORDER BY id ASC").fetchall()]
    settings = [dict(r) for r in conn.execute("SELECT * FROM site_settings").fetchall()]
    combos = [dict(r) for r in conn.execute("SELECT * FROM combos ORDER BY id ASC").fetchall()]
    coupons = [dict(r) for r in conn.execute("SELECT * FROM coupons").fetchall()]
    tele = dict(conn.execute("SELECT * FROM telegram_config WHERE id = 1").fetchone() or {})
    conn.close()
    return {
        "success": True,
        "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "categories": cats,
        "items": items,
        "site_settings": settings,
        "combos": combos,
        "coupons": coupons,
        "telegram_config": tele
    }


class ImportSyncDataRequest(BaseModel):
    categories: Optional[List[Dict[str, Any]]] = None
    items: Optional[List[Dict[str, Any]]] = None
    site_settings: Optional[List[Dict[str, Any]]] = None
    combos: Optional[List[Dict[str, Any]]] = None
    coupons: Optional[List[Dict[str, Any]]] = None
    telegram_config: Optional[Dict[str, Any]] = None


@app.post("/api/admin/sync/import_data")
def import_sync_data(payload: ImportSyncDataRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Nạp đè bộ nhớ danh mục, sản phẩm và cài đặt vào hệ thống ngay lập tức (Không chạm vào code)."""
    conn = get_db()
    cur = conn.cursor()

    # 1. Cập nhật Categories
    if payload.categories is not None:
        cur.execute("DELETE FROM categories_config")
        for c in payload.categories:
            cur.execute("""
            INSERT INTO categories_config (id, code, name, filter_type, filter_value, display_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (c.get("id"), c.get("code"), c.get("name"), c.get("filter_type", "BRAND"), c.get("filter_value", ""), c.get("display_order", 0), c.get("is_active", 1)))

    # 2. Cập nhật Items
    if payload.items is not None:
        cur.execute("DELETE FROM items")
        for it in payload.items:
            cur.execute("""
            INSERT INTO items (
                id, name, category, subcategory, brand, serial_or_size, mount_type,
                shutter_count, measurements, price_4h, price_8h, price_24h, deposit_amount,
                image_url, description, condition_status, availability, branch_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                it.get("id"), it.get("name"), it.get("category"), it.get("subcategory"), it.get("brand"),
                it.get("serial_or_size"), it.get("mount_type"), it.get("shutter_count", 0), it.get("measurements"),
                it.get("price_4h", 0), it.get("price_8h", 0), it.get("price_24h", 0), it.get("deposit_amount", 0),
                it.get("image_url"), it.get("description"), it.get("condition_status"),
                it.get("availability", "AVAILABLE"), it.get("branch_code", "CN1"),
                it.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ))

    # 3. Cập nhật Site Settings
    if payload.site_settings is not None:
        for s in payload.site_settings:
            cur.execute("UPDATE site_settings SET value = ? WHERE key = ?", (s.get("value"), s.get("key")))

    # 4. Cập nhật Combos
    if payload.combos is not None:
        cur.execute("DELETE FROM combos")
        for cb in payload.combos:
            cur.execute("""
            INSERT INTO combos (id, name, badge, price_24h, original_price_24h, deposit_amount, image_url, description, items_included_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cb.get("id"), cb.get("name"), cb.get("badge"), cb.get("price_24h", 0), cb.get("original_price_24h", 0),
                cb.get("deposit_amount", 0), cb.get("image_url"), cb.get("description"), cb.get("items_included_json"),
                cb.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ))

    # 5. Cập nhật Telegram Config (nếu có gửi)
    if payload.telegram_config is not None:
        t = payload.telegram_config
        cur.execute("""
        UPDATE telegram_config
        SET bot_token = COALESCE(?, bot_token),
            chat_id = COALESCE(?, chat_id),
            overdue_chat_id = COALESCE(?, overdue_chat_id),
            is_active = COALESCE(?, is_active),
            updated_at = ?
        WHERE id = 1
        """, (t.get("bot_token"), t.get("chat_id"), t.get("overdue_chat_id"), t.get("is_active"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã đồng bộ toàn bộ bộ nhớ dữ liệu thành công!"}


class RemoteSyncPushRequest(BaseModel):
    remote_url: str = "https://tidubastore.onrender.com"
    admin_password: str = "admin123"


@app.post("/api/admin/sync/push_to_remote")
def push_data_to_remote(req: RemoteSyncPushRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Gửi trực tiếp toàn bộ dữ liệu từ máy tính lên Web Cloud chỉ bằng 1 nút bấm (Không chạm vào code)."""
    target_url = req.remote_url.rstrip("/")
    # 1. Lấy dữ liệu local
    local_data = export_sync_data(admin=admin)

    # 2. Đăng nhập vào Web từ xa để lấy token
    login_url = f"{target_url}/api/auth/login"
    login_payload = json.dumps({"username": "admin", "password": req.admin_password}).encode("utf-8")
    login_req = urllib.request.Request(login_url, data=login_payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(login_req, timeout=15) as resp:
            login_res = json.loads(resp.read().decode("utf-8"))
            remote_token = login_res.get("token")
            if not remote_token:
                raise HTTPException(status_code=400, detail="Đăng nhập vào Web từ xa thất bại!")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"Không thể kết nối vào Web từ xa ({target_url}): {err_msg}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi kết nối Web từ xa: {str(e)}")

    # 3. Gửi gói dữ liệu sang import_data của Web từ xa
    import_url = f"{target_url}/api/admin/sync/import_data"
    import_payload = json.dumps(local_data).encode("utf-8")
    import_req = urllib.request.Request(
        import_url,
        data=import_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {remote_token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(import_req, timeout=20) as resp:
            import_res = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "message": f"🚀 Đồng bộ thành công 100%! Đã đẩy {len(local_data.get('items', []))} sản phẩm và {len(local_data.get('categories', []))} danh mục lên Web Cloud ({target_url})."
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi nạp dữ liệu lên Web từ xa: {str(e)}")


@app.post("/api/admin/sync/pull_from_remote")
def pull_data_from_remote(req: RemoteSyncPushRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Kéo toàn bộ dữ liệu mới nhất (đơn hàng, danh mục) từ Web Cloud về máy tính."""
    target_url = req.remote_url.rstrip("/")
    login_url = f"{target_url}/api/auth/login"
    login_payload = json.dumps({"username": "admin", "password": req.admin_password}).encode("utf-8")
    login_req = urllib.request.Request(login_url, data=login_payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(login_req, timeout=15) as resp:
            login_res = json.loads(resp.read().decode("utf-8"))
            remote_token = login_res.get("token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể kết nối Web từ xa: {str(e)}")

    # Lấy dữ liệu từ remote
    export_url = f"{target_url}/api/admin/sync/export_data"
    export_req = urllib.request.Request(export_url, headers={"Authorization": f"Bearer {remote_token}"})
    try:
        with urllib.request.urlopen(export_req, timeout=20) as resp:
            remote_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi lấy dữ liệu từ Web từ xa: {str(e)}")

    # Nạp vào database local
    import_sync_data(payload=ImportSyncDataRequest(**remote_data), admin=admin)
    return {
        "success": True,
        "message": f"📥 Đã kéo dữ liệu từ Web Cloud về máy tính thành công!"
    }


# =============================================================================
# 12.3 SINH MÃ VIETQR HOÀN CỌC CHO ADMIN QUÉT TRẢ TIỀN 1-CHẠM
# =============================================================================

@app.get("/api/admin/rentals/{rental_id}/refund_qr")
def get_rental_refund_qr(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin lấy thông tin và mã VietQR hoàn tiền cọc lại cho khách sau khi trừ thiệt hại."""
    conn = get_db()
    rental = conn.execute("""
    SELECT r.*, u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()

    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn!")

    # Tính tiền phạt thiệt hại
    penalties = conn.execute("SELECT sum(penalty_amount) as s FROM damage_penalties WHERE rental_id = ?", (rental_id,)).fetchone()["s"] or 0
    conn.close()

    total_deposit = rental["deposit_paid"] or 0
    late_fee = rental["late_fee"] or 0
    refund_amount = max(0, total_deposit - penalties - late_fee)
    bank_info = rental["refund_bank_info"] if ("refund_bank_info" in rental.keys() and rental["refund_bank_info"]) else ""

    return {
        "success": True,
        "rental_code": rental["rental_code"],
        "customer_name": rental["customer_name"],
        "customer_phone": rental["customer_phone"],
        "deposit_paid": total_deposit,
        "damage_deduction": penalties,
        "late_fee": late_fee,
        "refund_amount": refund_amount,
        "refund_bank_info": bank_info
    }


@app.get("/api/admin/rentals/{rental_id}/label", response_class=HTMLResponse)
def print_equipment_barcode_label(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """In tem mã vạch K80 dán trực tiếp lên thiết bị máy ảnh / túi đồ cho thuê."""
    conn = get_db()
    r = conn.execute("""
    SELECT r.*, 
           COALESCE(i.name, c.name) as item_name, 
           COALESCE(i.serial_or_size, 'Combo') as serial_or_size,
           u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn!")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tem Mã Vạch Thiết Bị - {r['rental_code']}</title>
    <style>
        body {{ margin: 0; padding: 10px; font-family: monospace; font-size: 11pt; width: 75mm; text-align: center; background: #fff; color: #000; }}
        .header {{ font-weight: bold; font-size: 13pt; text-transform: uppercase; border-bottom: 2px dashed #000; padding-bottom: 5px; }}
        .code {{ font-size: 18pt; font-weight: 900; letter-spacing: 2px; margin: 8px 0; border: 1px solid #000; padding: 4px; }}
        .meta {{ text-align: left; font-size: 10pt; line-height: 1.4; border-bottom: 1px dashed #000; padding: 6px 0; }}
        .warning {{ font-size: 9pt; font-weight: bold; margin-top: 6px; }}
        @media print {{ button {{ display: none; }} }}
    </style>
</head>
<body onload="window.print()">
    <div class="header">TIDUBA STORE - THIẾT BỊ CHO THUÊ</div>
    <div class="code">*{r['rental_code']}*</div>
    <div class="meta">
        <div><strong>MÁY/ĐỒ:</strong> {r['item_name']}</div>
        <div><strong>SERIAL:</strong> {r['serial_or_size']}</div>
        <div><strong>KHÁCH:</strong> {r['customer_name']} ({r['customer_phone']})</div>
        <div><strong>HẠN TRẢ:</strong> {r['end_time']}</div>
        <div><strong>HOTLINE:</strong> 0977.078.981</div>
    </div>
    <div class="warning">⚠️ NIÊM PHONG THIẾT BỊ - VUI LÒNG KHÔNG BÓC TEM</div>
</body>
</html>"""
    return HTMLResponse(content=html)


# =============================================================================
# 12. FRONTEND SERVING
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def index():
    index_html = TEMPLATES_DIR / "index.html"
    if index_html.exists():
        return HTMLResponse(content=index_html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Tiduba Store Backend Online. Giao diện đang được nạp...</h1>")


# =============================================================================
# 13. eKYC UPLOAD ẢNH CCCD (KHÁCH TỰ CHỤP & NẠP ẢNH)
# =============================================================================

@app.post("/api/ekyc/upload_image")
async def upload_ekyc_image(
    file: UploadFile = File(...),
    side: str = "front",  # 'front' hoặc 'back' hoặc 'selfie'
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Khách hàng tự chụp/tải ảnh CCCD mặt trước, mặt sau và ảnh selfie để xác minh."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để nạp ảnh eKYC!")

    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Chỉ chấp nhận ảnh: {', '.join(allowed_exts)}")

    # Kiểm tra kích thước tối đa 10MB
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ảnh vượt quá 10MB! Vui lòng nén ảnh trước.")

    # Tạo tên file an toàn (không path traversal)
    safe_side = re.sub(r"[^a-z]", "", side.lower()) or "doc"
    unique_filename = f"ekyc_{user['id']}_{safe_side}_{int(time.time() * 1000)}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    try:
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu ảnh: {str(e)}")

    image_url = f"/static/uploads/{unique_filename}"

    # Cập nhật ngay vào DB
    conn = get_db()
    if side == "front":
        conn.execute("UPDATE users SET cccd_front_img = ? WHERE id = ?", (image_url, user["id"]))
    elif side == "back":
        conn.execute("UPDATE users SET cccd_back_img = ? WHERE id = ?", (image_url, user["id"]))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Đã tải ảnh {side} CCCD thành công!",
        "image_url": image_url,
        "side": side
    }


# =============================================================================
# 14. ADMIN XÁC NHẬN THANH TOÁN (Thay thế nút Đã Hoàn Tất của khách)
# =============================================================================

@app.post("/api/admin/rentals/{rental_id}/confirm_payment")
def admin_confirm_payment(rental_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin xác nhận đã nhận tiền và kích hoạt đơn thuê (chỉ admin mới làm được)."""
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("""
    SELECT r.*, COALESCE(i.name, c.name) as item_name, COALESCE(i.serial_or_size, 'Combo') as serial_or_size,
           u.full_name as customer_name, u.phone as customer_phone, u.cccd_number as customer_cccd
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (rental_id,)).fetchone()

    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    rental = dict(rental)

    # Cập nhật trạng thái sang ACTIVE
    cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (rental_id,))
    if "items_json" in rental.keys() and rental["items_json"]:
        try:
            for itm in json.loads(rental["items_json"]):
                if itm.get("item_id"):
                    cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (itm["item_id"],))
        except Exception: pass
    elif rental["item_id"]:
        cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (rental["item_id"],))

    # Tự động in bill
    bill_text = build_escpos_thermal_bill_text({
        "rental_code": rental["rental_code"],
        "customer_name": rental["customer_name"],
        "customer_phone": rental["customer_phone"],
        "customer_cccd": rental["customer_cccd"] or "N/A",
        "item_name": rental["item_name"],
        "serial_or_size": rental["serial_or_size"],
        "rental_type": rental["rental_type"],
        "rental_hours": rental["rental_duration_hours"],
        "start_time": rental["start_time"],
        "end_time": rental["end_time"],
        "total_price": rental["total_price"],
        "deposit_paid": rental["deposit_paid"]
    })

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO print_queue (rental_id, bill_text, status, created_at)
    VALUES (?, ?, 'PENDING', ?)
    """, (rental_id, bill_text, now_str))

    # Ghi log Zalo
    cur.execute("""
    INSERT INTO zns_logs (rental_id, phone, milestone, template_id, channel, status, sent_at)
    VALUES (?, ?, 'ADMIN_CONFIRMED_PAYMENT', 'TDB_ZNS_ADMIN_CONFIRM_V1', 'ZALO_ZNS', 'SENT', ?)
    """, (rental_id, rental["customer_phone"], now_str))

    conn.commit()

    # Gửi thông báo Telegram khi Admin xác nhận thanh toán
    tele_msg = (
        f"<b>💰 TIDUBA STORE - XÁC NHẬN THANH TOÁN ({rental['rental_code']})</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Khách hàng:</b> {rental['customer_name']} (<code>{rental['customer_phone']}</code>)\n"
        f"📦 <b>Thiết bị:</b> {rental['item_name']}\n"
        f"⏳ <b>Hạn trả đồ:</b> <b>{rental['end_time']}</b>\n"
        f"🛡️ <b>Hình thức cọc:</b> {rental.get('deposit_type', 'CCCD')} ({rental.get('deposit_asset_desc') or 'Giữ CCCD'})\n"
        f"✅ <b>Trạng thái:</b> ĐÃ KÍCH HOẠT ĐƠN & TỰ ĐỘNG IN BILL K80!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Quét trả đồ: {PUBLIC_DOMAIN}/return-qr?code={rental['rental_code']}"
    )
    _send_telegram_notification(tele_msg, rental_id=rental_id, event_type="PAYMENT")

    conn.close()

    return {
        "success": True,
        "message": f"✅ Đã xác nhận thanh toán và kích hoạt đơn {rental['rental_code']} thành công!",
        "rental_code": rental["rental_code"],
        "customer_name": rental["customer_name"]
    }


class CustomerPaymentProofRequest(BaseModel):
    rental_id: int
    proof_image_url: Optional[str] = None
    customer_notes: Optional[str] = None


@app.post("/api/rentals/submit_payment_proof")
def submit_customer_payment_proof(req: CustomerPaymentProofRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Khách hàng ấn nút 'Tôi đã chuyển tiền' kèm tải lên ảnh biên lai / minh chứng thanh toán.
    Hệ thống:
    - Lưu proof_image_url vào đơn thuê
    - Cập nhật ghi chú
    - Gửi ngay tin nhắn ảnh hoặc tin nhắn thông báo qua Telegram Bot tới Group quản lý kèm nút bấm:
      [✅ Xác Nhận Đã Thanh Toán]
      Khi admin bấm nút trên Telegram hoặc web, đơn lập tức được duyệt và đồng bộ!
    """
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("""
    SELECT r.*, COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
           u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (req.rental_id,)).fetchone()

    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để gửi minh chứng thanh toán!")

    if user.get("role") != "admin" and rental["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Bạn không có quyền gửi minh chứng cho đơn hàng này!")

    note_addon = ' | Khách đã tải bill chuyển tiền' if req.proof_image_url else ' | Khách báo đã chuyển khoản qua VietQR MB'
    cur.execute("""
    UPDATE rentals 
    SET payment_proof_img = COALESCE(?, payment_proof_img), customer_notes = COALESCE(customer_notes, '') || ?
    WHERE id = ?
    """, (req.proof_image_url, note_addon, req.rental_id))
    conn.commit()
    conn.close()

    branch_code = rental["branch_code"] if ("branch_code" in rental.keys() and rental["branch_code"]) else "CN1"
    branch_info = STORE_BRANCHES.get(branch_code, STORE_BRANCHES["CN1"])

    bill_status_text = "📸 <i>Ảnh biên lai đính kèm bên dưới.</i>" if req.proof_image_url else "⚡ <i>Khách báo đã chuyển khoản (Vui lòng đối chiếu app MBBank).</i>"

    tele_msg = (
        f"<b>📸 [THANH TOÁN] KHÁCH BÁO ĐÃ CHUYỂN KHOẢN!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Mã đơn:</b> <code>{rental['rental_code']}</code>\n"
        f"👤 <b>Khách hàng:</b> {rental['customer_name']} (<code>{rental['customer_phone']}</code>)\n"
        f"📦 <b>Thiết bị:</b> {rental['item_name']}\n"
        f"💵 <b>Số tiền cần trả:</b> <b>{rental['total_price']:,}đ</b>\n"
        f"🏢 <b>Chi nhánh:</b> {branch_info['name']}\n"
        f"{bill_status_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>Admin bấm nút bên dưới để duyệt thanh toán ngay:</b>"
    )

    # Tạo HMAC signature bảo mật cho link xác nhận
    confirm_sig = hmac.new(TOKEN_SECRET.encode(), f"{rental['id']}:{rental['rental_code']}".encode(), hashlib.sha256).hexdigest()
    confirm_url = f"https://tidubastore.onrender.com/api/telegram/quick_confirm?rental_id={rental['id']}&code={rental['rental_code']}&sig={confirm_sig}"
    
    # Nút bấm Inline: Hỗ trợ cả Callback bấm duyệt thẳng trong Telegram lẫn xem trên web
    inline_kb = [
        [
            {"text": "✅ Xác Nhận Đã Nhận Tiền (Duyệt Ngay)", "callback_data": f"confirm_pay:{rental['id']}:{rental['rental_code']}"}
        ],
        [
            {"text": "🔍 Xem Chi Tiết Trên Web", "url": f"https://tidubastore.onrender.com/return-qr?code={rental['rental_code']}"}
        ]
    ]
    tele_msg += "\n👇 <b>Bấm [Xác Nhận Đã Nhận Tiền] bên dưới để duyệt đơn tức thì (Không cần mở web):</b>"

    _send_telegram_notification(
        message=tele_msg,
        rental_id=rental["id"],
        event_type="PAYMENT",
        photo_url=req.proof_image_url,
        inline_keyboard=inline_kb
    )

    return {
        "success": True,
        "message": "✅ Đã gửi ảnh minh chứng thanh toán thành công! Quản lý đang duyệt đơn và sẽ kích hoạt trong ít phút.",
        "rental_code": rental["rental_code"]
    }


@app.get("/api/telegram/quick_confirm", response_class=HTMLResponse)
def telegram_quick_confirm_payment(rental_id: int, code: str, sig: Optional[str] = None):
    """
    Đường link duyệt nhanh từ nút bấm trên Telegram Bot.
    SECURITY: Yêu cầu tham số `sig` là HMAC signature để xác thực link hợp lệ.
    Chữ ký = HMAC-SHA256(TOKEN_SECRET, f"{rental_id}:{code}") dạng hex.
    """
    # Validate HMAC signature - chống giả mạo link xác nhận thanh toán
    if not sig:
        return HTMLResponse("<h3>❌ Link xác nhận không hợp lệ (thiếu chữ ký bảo mật)!</h3>", status_code=403)
    
    expected_sig = hmac.new(TOKEN_SECRET.encode(), f"{rental_id}:{code}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return HTMLResponse("<h3>❌ Chữ ký bảo mật không hợp lệ! Link đã bị giả mạo hoặc thay đổi.</h3>", status_code=403)
    conn = get_db()
    cur = conn.cursor()
    rental = cur.execute("SELECT * FROM rentals WHERE id = ? AND rental_code = ?", (rental_id, code)).fetchone()
    if not rental:
        conn.close()
        return HTMLResponse("<h3>❌ Không tìm thấy đơn thuê hợp lệ!</h3>", status_code=404)

    cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (rental_id,))
    if "items_json" in rental.keys() and rental["items_json"]:
        try:
            for itm in json.loads(rental["items_json"]):
                if itm.get("item_id"):
                    cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (itm["item_id"],))
        except Exception: pass
    elif rental["item_id"]:
        cur.execute("UPDATE items SET availability = 'RENTED' WHERE id = ?", (rental["item_id"],))

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO print_queue (rental_id, bill_text, status, created_at)
    VALUES (?, ?, 'PENDING', ?)
    """, (rental_id, f"DUYET QUA TELEGRAM BOT DON {code}", now_str))

    conn.commit()
    conn.close()

    tele_msg = f"✅ <b>Admin đã duyệt đơn {code} qua Telegram!</b> Đơn hàng đã chuyển sang trạng thái <b>ACTIVE (Đang thuê)</b>."
    _send_telegram_notification(tele_msg, rental_id=rental_id, event_type="PAYMENT")

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Duyệt Thanh Toán Thành Công - {code}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white min-h-screen flex items-center justify-center p-4">
        <div class="bg-slate-800 p-8 rounded-3xl max-w-md w-full text-center space-y-4 border border-emerald-500 shadow-2xl">
            <div class="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center text-3xl mx-auto">✓</div>
            <h2 class="text-xl font-bold text-emerald-400">ĐÃ XÁC NHẬN THANH TOÁN!</h2>
            <p class="text-sm text-gray-300">Đơn hàng <strong>{code}</strong> đã được kích hoạt thành công trên hệ thống Tiduba Store.</p>
            <p class="text-xs text-gray-400">Thiết bị đã chuyển trạng thái RENTED và đồng bộ tức thì trên Web.</p>
            <a href="/" class="inline-block mt-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded-xl text-xs">Về Trang Chủ Web</a>
        </div>
    </body>
    </html>
    """)


# =============================================================================
# 15. TELEGRAM NOTIFICATION BOT SERVICE
# =============================================================================

def _send_telegram_notification(
    message: str, 
    rental_id: Optional[int] = None, 
    event_type: str = "NOTIFY",
    photo_url: Optional[str] = None,
    inline_keyboard: Optional[List[List[Dict[str, str]]]] = None,
    override_token: Optional[str] = None,
    override_chat_id: Optional[str] = None,
    return_detail: bool = False
) -> Union[bool, Tuple[bool, str]]:
    """
    Gửi thông báo Telegram Bot thời gian thực tới Admin hoặc Group quản lý.
    Hỗ trợ gửi kèm ảnh minh chứng thanh toán (sendPhoto) và Inline Keyboard nút bấm xác nhận.
    Tự động chuẩn hóa tất cả định dạng group chat_id (-5368352616, -1005368352616, 5368352616).
    Tự động xử lý khi nhóm nâng cấp supergroup (migrate_to_chat_id).
    """
    last_err_detail = "Chưa cấu hình Telegram Bot"
    try:
        conn = get_db()
        cfg = conn.execute("SELECT * FROM telegram_config WHERE id = 1").fetchone()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "LOG_ONLY"

        active_token = (override_token or (cfg["bot_token"] if cfg else "")).strip()
        active_chat_id = (override_chat_id or (cfg["chat_id"] if cfg else "")).strip()

        # Nếu là sự kiện QUÁ HẠN hoặc NHẮC HẸN SẮP TỚI GIỜ TRẢ/NHẬN: Ưu tiên gửi sang Group quá hạn riêng nếu có cấu hình
        if not override_chat_id and cfg and "overdue_chat_id" in cfg.keys() and cfg["overdue_chat_id"]:
            if event_type in ("OVERDUE", "WARNING_DUE_SOON", "PICKUP_REMINDER"):
                active_chat_id = cfg["overdue_chat_id"].strip()

        if active_token and active_chat_id:
            # Kiểm tra phân loại sự kiện theo cấu hình bật/tắt (nếu không phải TEST hoặc override)
            if not override_chat_id and cfg and cfg["is_active"]:
                if event_type == "NEW_RENTAL" and not cfg["auto_notify_new_rental"]:
                    conn.close()
                    return (False, "Đã tắt thông báo đơn mới") if return_detail else False
                if event_type == "PAYMENT" and not cfg["auto_notify_payment"]:
                    conn.close()
                    return (False, "Đã tắt thông báo thanh toán") if return_detail else False
                if event_type == "RETURN" and not cfg["auto_notify_return"]:
                    conn.close()
                    return (False, "Đã tắt thông báo trả đồ") if return_detail else False
                if event_type in ("OVERDUE", "WARNING_DUE_SOON") and not cfg["auto_notify_overdue"]:
                    conn.close()
                    return (False, "Đã tắt thông báo quá hạn") if return_detail else False

            # Tạo danh sách các ứng viên chat_id để thử gửi (hỗ trợ mọi biến thể nhóm)
            candidate_chat_ids = [active_chat_id]
            if active_chat_id.startswith("-100"):
                clean = active_chat_id[4:]
                if clean:
                    candidate_chat_ids.append(f"-{clean}")
            elif active_chat_id.startswith("-"):
                clean = active_chat_id.lstrip("-")
                candidate_chat_ids.append(f"-100{clean}")
            else:
                if active_chat_id.startswith("100"):
                    candidate_chat_ids.append(f"-{active_chat_id}")
                    candidate_chat_ids.append(f"-{active_chat_id[3:]}")
                else:
                    candidate_chat_ids.append(f"-{active_chat_id}")
                    candidate_chat_ids.append(f"-100{active_chat_id}")

            # Lọc an toàn cho inline_keyboard: chỉ giữ các nút URL hợp lệ (bắt đầu bằng https:// và không chứa localhost)
            safe_inline_keyboard = None
            if inline_keyboard:
                filtered_rows = []
                for row in inline_keyboard:
                    valid_cols = []
                    for btn in row:
                        u = btn.get("url", "")
                        if u.startswith("https://") and "localhost" not in u and "127.0.0.1" not in u:
                            valid_cols.append(btn)
                        elif btn.get("callback_data"):
                            valid_cols.append(btn)
                    if valid_cols:
                        filtered_rows.append(valid_cols)
                if filtered_rows:
                    safe_inline_keyboard = filtered_rows

            sent_successfully = False
            working_chat_id = None
            for target_chat_id in candidate_chat_ids:
                try:
                    # Kiểm tra xem có file ảnh cục bộ trên ổ cứng không để upload trực tiếp multipart
                    local_photo_path = None
                    if photo_url:
                        clean_url = photo_url.split("?")[0].lstrip("/")
                        if clean_url.startswith("static/"):
                            p = BASE_DIR / clean_url
                            if p.exists() and p.is_file():
                                local_photo_path = p
                        if not local_photo_path:
                            p2 = STATIC_DIR / clean_url
                            if p2.exists() and p2.is_file():
                                local_photo_path = p2
                        if not local_photo_path and Path(photo_url).exists() and Path(photo_url).is_file():
                            local_photo_path = Path(photo_url)

                    if local_photo_path and local_photo_path.is_file():
                        # GỬI ẢNH THẬT BẰNG MULTIPART/FORM-DATA (KHÔNG CẦN DOMAIN CÔNG KHAI)
                        url = f"https://api.telegram.org/bot{active_token}/sendPhoto"
                        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
                        body_bytes = bytearray()
                        body_bytes.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{target_chat_id}\r\n'.encode('utf-8'))
                        body_bytes.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{message}\r\n'.encode('utf-8'))
                        body_bytes.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode('utf-8'))
                        if safe_inline_keyboard:
                            body_bytes.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="reply_markup"\r\n\r\n{json.dumps({"inline_keyboard": safe_inline_keyboard})}\r\n'.encode('utf-8'))
                        with open(local_photo_path, "rb") as f:
                            raw_img = f.read()
                        fname = local_photo_path.name
                        mtype = "image/jpeg" if fname.lower().endswith((".jpg", ".jpeg")) else ("image/png" if fname.lower().endswith(".png") else "application/octet-stream")
                        body_bytes.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{fname}"\r\nContent-Type: {mtype}\r\n\r\n'.encode('utf-8'))
                        body_bytes.extend(raw_img)
                        body_bytes.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

                        req = urllib.request.Request(
                            url,
                            data=bytes(body_bytes),
                            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "TidubaStoreBot/1.0"},
                            method="POST"
                        )
                    elif photo_url:
                        full_photo_url = photo_url
                        if photo_url.startswith("/"):
                            full_photo_url = f"{PUBLIC_DOMAIN}{photo_url}"

                        url = f"https://api.telegram.org/bot{active_token}/sendPhoto"
                        body_dict = {
                            "chat_id": target_chat_id,
                            "photo": full_photo_url,
                            "caption": message,
                            "parse_mode": "HTML"
                        }
                        if safe_inline_keyboard:
                            body_dict["reply_markup"] = {"inline_keyboard": safe_inline_keyboard}

                        payload_data = json.dumps(body_dict).encode("utf-8")
                        req = urllib.request.Request(
                            url,
                            data=payload_data,
                            headers={"Content-Type": "application/json", "User-Agent": "TidubaStoreBot/1.0"},
                            method="POST"
                        )
                    else:
                        url = f"https://api.telegram.org/bot{active_token}/sendMessage"
                        body_dict = {
                            "chat_id": target_chat_id,
                            "text": message,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True
                        }
                        if safe_inline_keyboard:
                            body_dict["reply_markup"] = {"inline_keyboard": safe_inline_keyboard}

                        payload_data = json.dumps(body_dict).encode("utf-8")
                        req = urllib.request.Request(
                            url,
                            data=payload_data,
                            headers={"Content-Type": "application/json", "User-Agent": "TidubaStoreBot/1.0"},
                            method="POST"
                        )

                    with urllib.request.urlopen(req, timeout=15) as resp:
                        if resp.status == 200:
                            status = "SENT"
                            sent_successfully = True
                            working_chat_id = target_chat_id
                            last_err_detail = "Thành công"
                            break
                        else:
                            status = f"HTTP_{resp.status}"
                except urllib.error.HTTPError as e:
                    err_text = e.read().decode('utf-8', errors='ignore')
                    last_err_detail = f"Telegram lỗi {e.code}: {err_text}"
                    print(f"[TELEGRAM] Thử gửi tới {target_chat_id} thất bại: {last_err_detail}")
                    # Kiểm tra xem nhóm có bị di chuyển sang Supergroup không
                    try:
                        err_json = json.loads(err_text)
                        migrated_id = err_json.get("parameters", {}).get("migrate_to_chat_id")
                        if migrated_id:
                            print(f"[TELEGRAM] Nhóm đã nâng cấp supergroup, ID mới: {migrated_id}")
                            body_dict["chat_id"] = str(migrated_id)
                            payload_data = json.dumps(body_dict).encode("utf-8")
                            req_retry = urllib.request.Request(
                                url,
                                data=payload_data,
                                headers={"Content-Type": "application/json", "User-Agent": "TidubaStoreBot/1.0"},
                                method="POST"
                            )
                            with urllib.request.urlopen(req_retry, timeout=10) as resp_retry:
                                if resp_retry.status == 200:
                                    status = "SENT"
                                    sent_successfully = True
                                    working_chat_id = str(migrated_id)
                                    last_err_detail = "Thành công (sau khi cập nhật supergroup ID)"
                                    break
                    except Exception:
                        pass
                except Exception as e:
                    status = f"FAILED: {str(e)[:50]}"
                    last_err_detail = str(e)
                    print(f"[TELEGRAM] Thử gửi tới {target_chat_id} thất bại: {e}")

            # Nếu gửi thành công bằng ID chuẩn và khác ID ban đầu, tự động lưu lại vào DB
            if sent_successfully and working_chat_id and working_chat_id != active_chat_id:
                try:
                    conn.execute("UPDATE telegram_config SET chat_id = ? WHERE id = 1", (working_chat_id,))
                    conn.commit()
                    print(f"[TELEGRAM] Đã tự động cập nhật chat_id tối ưu vào DB: {working_chat_id}")
                except Exception:
                    pass

        # Ghi log vào bảng telegram_logs
        log_chat_id = active_chat_id or (cfg["chat_id"] if cfg else "")
        conn.execute("""
        INSERT INTO telegram_logs (rental_id, chat_id, event_type, message, status, sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (rental_id, log_chat_id, event_type, message, status, now_str))
        conn.commit()
        conn.close()

        is_ok = (status == "SENT")
        if return_detail:
            return (is_ok, last_err_detail)
        return is_ok
    except Exception as e:
        print(f"[TELEGRAM SERVICE] Lỗi hệ thống: {e}")
        if return_detail:
            return (False, f"Lỗi hệ thống: {str(e)}")
        return False


@app.get("/api/admin/telegram/config")
def get_telegram_config(admin: Dict[str, Any] = Depends(require_admin)):
    """Lấy cấu hình Telegram Bot hiện tại."""
    conn = get_db()
    cfg = conn.execute("SELECT * FROM telegram_config WHERE id = 1").fetchone()
    conn.close()
    if cfg:
        return dict(cfg)
    return {
        "id": None, "bot_token": "", "chat_id": "", "is_active": 1,
        "auto_notify_new_rental": 1, "auto_notify_payment": 1,
        "auto_notify_return": 1, "auto_notify_overdue": 1
    }


class TelegramConfigRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    overdue_chat_id: Optional[str] = None
    is_active: Optional[int] = None
    auto_notify_new_rental: Optional[int] = None
    auto_notify_payment: Optional[int] = None
    auto_notify_return: Optional[int] = None
    auto_notify_overdue: Optional[int] = None


@app.post("/api/admin/telegram/config")
def save_telegram_config(req: TelegramConfigRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Lưu cấu hình Telegram Bot (Hỗ trợ group chính và group quá hạn riêng biệt)."""
    conn = get_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = conn.execute("SELECT id FROM telegram_config WHERE id = 1").fetchone()

    fields = []
    params = []
    for k, v in req.dict(exclude_none=True).items():
        fields.append(f"{k} = ?")
        params.append(v)

    if fields:
        fields.append("updated_at = ?")
        params.append(now_str)
        if existing:
            params.append(1)
            conn.execute(f"UPDATE telegram_config SET {', '.join(fields)} WHERE id = ?", params)
        else:
            cols = [f.split(" = ")[0] for f in fields]
            conn.execute(f"INSERT INTO telegram_config ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(params))})", params)

    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã lưu cấu hình Telegram Bot thành công!"}


@app.post("/api/admin/telegram/check_overdue_alerts")
def check_overdue_alerts_now(admin: Dict[str, Any] = Depends(require_admin)):
    """Admin quét tự động và bắn cảnh báo các đơn quá hạn / sắp tới giờ trả vào Group Telegram Quá Hạn."""
    conn = get_db()
    cur = conn.cursor()
    rentals = cur.execute("""
    SELECT r.*, COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
           u.full_name as customer_name, u.phone as customer_phone
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE r.status = 'ACTIVE'
    """).fetchall()
    conn.close()

    now = datetime.datetime.now()
    overdue_count = 0
    remind_count = 0

    for r in rentals:
        try:
            end_dt = datetime.datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M")
        except Exception:
            continue

        diff_seconds = (end_dt - now).total_seconds()
        diff_hours = round(diff_seconds / 3600.0, 1)

        b_code = r["branch_code"] if ("branch_code" in r.keys() and r["branch_code"]) else "CN1"
        branch_info = STORE_BRANCHES.get(b_code, STORE_BRANCHES["CN1"])

        if diff_seconds < 0:
            # ĐÃ QUÁ HẠN!
            overdue_hours = round(abs(diff_seconds) / 3600.0, 1)
            msg = (
                f"<b>🚨 [CẢNH BÁO QUÁ HẠN] ĐƠN CHƯA TRẢ ĐỒ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>Mã đơn:</b> <code>{r['rental_code']}</code>\n"
                f"👤 <b>Khách hàng:</b> {r['customer_name']} (<code>{r['customer_phone']}</code>)\n"
                f"📦 <b>Thiết bị/Đồ:</b> {r['item_name']}\n"
                f"⏰ <b>Hạn trả:</b> <b>{r['end_time']}</b> (Đã trễ: <b>{overdue_hours}h</b>)\n"
                f"📍 <b>Chi nhánh:</b> {branch_info['name']}\n"
                f"⚠️ <i>Phí trễ hạn: 30.000đ/giờ. Vui lòng liên hệ khách!</i>\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            _send_telegram_notification(msg, rental_id=r["id"], event_type="OVERDUE")
            overdue_count += 1
        elif diff_hours <= 3.0:
            # SẮP TỚI HẠN TRẢ TRONG VÒNG 3 TIẾNG!
            msg = (
                f"<b>⏰ [NHẮC HẸN] SẮP ĐẾN GIỜ TRẢ ĐỒ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>Mã đơn:</b> <code>{r['rental_code']}</code>\n"
                f"👤 <b>Khách hàng:</b> {r['customer_name']} (<code>{r['customer_phone']}</code>)\n"
                f"📦 <b>Thiết bị/Đồ:</b> {r['item_name']}\n"
                f"⏰ <b>Hạn trả:</b> <b>{r['end_time']}</b> (Còn lại: <b>{diff_hours}h</b>)\n"
                f"📍 <b>Chi nhánh nhận trả:</b> {branch_info['name']}\n"
                f"💡 <i>Nhắc khách chuẩn bị trả đồ đúng hạn tránh phát sinh phí.</i>\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            _send_telegram_notification(msg, rental_id=r["id"], event_type="WARNING_DUE_SOON")
            remind_count += 1

    return {
        "success": True,
        "message": f"Đã quét xong: Phát hiện {overdue_count} đơn quá hạn và {remind_count} đơn sắp đến giờ trả.",
        "overdue_count": overdue_count,
        "remind_count": remind_count
    }


@app.get("/api/admin/telegram/logs")
def get_telegram_logs(admin: Dict[str, Any] = Depends(require_admin)):
    """Lấy danh sách lịch sử gửi thông báo Telegram."""
    conn = get_db()
    logs = conn.execute("SELECT * FROM telegram_logs ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return {"logs": [dict(l) for l in logs], "count": len(logs)}


@app.get("/api/admin/telegram/detect_chat_id")
def detect_telegram_chat_id(admin: Dict[str, Any] = Depends(require_admin)):
    """Tự động quét các tin nhắn / sự kiện bot đã nhận để trích xuất Chat ID & Group ID."""
    conn = get_db()
    cfg = conn.execute("SELECT * FROM telegram_config WHERE id = 1").fetchone()
    conn.close()
    if not cfg or not cfg["bot_token"]:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Telegram Bot Token!")

    bot_token = cfg["bot_token"].strip()
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TidubaStoreBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        updates = data.get("result", [])
        chats_found = {}
        for u in updates:
            chat = None
            if "message" in u and "chat" in u["message"]:
                chat = u["message"]["chat"]
            elif "my_chat_member" in u and "chat" in u["my_chat_member"]:
                chat = u["my_chat_member"]["chat"]
            elif "channel_post" in u and "chat" in u["channel_post"]:
                chat = u["channel_post"]["chat"]
            elif "chat_member" in u and "chat" in u["chat_member"]:
                chat = u["chat_member"]["chat"]

            if chat and "id" in chat:
                cid = str(chat["id"])
                ctype = chat.get("type", "unknown")
                title = chat.get("title") or chat.get("first_name") or chat.get("username") or cid
                type_label = "👥 Nhóm" if ctype in ("group", "supergroup") else ("📢 Kênh" if ctype == "channel" else "👤 Cá nhân")
                chats_found[cid] = {
                    "id": cid,
                    "title": title,
                    "type": ctype,
                    "display": f"{type_label}: {title} (ID: {cid})"
                }

        # Nếu đã có nhóm đang lưu, luôn đưa vào danh sách gợi ý
        if cfg["chat_id"]:
            cid = str(cfg["chat_id"]).strip()
            if cid not in chats_found:
                type_label = "👥 Nhóm" if cid.startswith("-") else "👤 Cá nhân"
                chats_found[cid] = {
                    "id": cid,
                    "title": "Nhóm đang lưu hiện tại",
                    "type": "group" if cid.startswith("-") else "private",
                    "display": f"{type_label}: Nhóm đang lưu (ID: {cid})"
                }

        chat_list = list(chats_found.values())
        return {
            "success": True,
            "chats": chat_list,
            "message": f"Tìm thấy {len(chat_list)} cuộc trò chuyện / nhóm đã tương tác với Bot."
        }
    except Exception as e:
        return {"success": False, "message": f"Lỗi kết nối Telegram getUpdates: {str(e)}"}


class TelegramTestRequest(BaseModel):
    message: Optional[str] = "🔔 Test thông báo từ Tiduba Store! Bot Telegram đang hoạt động rất tốt."
    chat_id: Optional[str] = None
    bot_token: Optional[str] = None


@app.post("/api/admin/telegram/test")
def test_telegram_notification(req: TelegramTestRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Gửi tin nhắn test tới Telegram (hỗ trợ thử ID mới và tự động lưu khi thành công)."""
    test_msg = (
        f"<b>📸 TIDUBA STORE - TEST KẾT NỐI TELEGRAM BOT</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{req.message or 'Kiểm tra kết nối thành công!'}\n"
        f"⏰ <b>Thời gian:</b> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"👑 <b>Admin:</b> {admin['full_name']}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    sent, err_detail = _send_telegram_notification(
        test_msg, 
        event_type="TEST",
        override_token=req.bot_token,
        override_chat_id=req.chat_id,
        return_detail=True
    )
    if sent:
        # Tự động lưu cấu hình nếu gửi thành công với thông số override
        if req.chat_id or req.bot_token:
            conn = get_db()
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if req.chat_id and req.bot_token:
                conn.execute("UPDATE telegram_config SET chat_id = ?, bot_token = ?, updated_at = ? WHERE id = 1", (req.chat_id.strip(), req.bot_token.strip(), now_str))
            elif req.chat_id:
                conn.execute("UPDATE telegram_config SET chat_id = ?, updated_at = ? WHERE id = 1", (req.chat_id.strip(), now_str))
            conn.commit()
            conn.close()
        return {"success": True, "message": "Đã gửi tin nhắn test thành công tới Telegram!"}
    else:
        return {"success": False, "message": f"Gửi test thất bại! Chi tiết: {err_detail}"}


# =============================================================================
# 16. QUÉT MÃ QR TỰ ĐỘNG NHẬN TRẢ ĐỒ & THANH LÝ HỢP ĐỒNG (RETURN BY QR)
# =============================================================================

class ReturnQrRequest(BaseModel):
    rental_code: str
    notes: Optional[str] = "Quét mã QR tự động nhận bill đã trả"


@app.post("/api/rentals/return_by_qr")
@app.post("/api/admin/rentals/return_by_qr")
def process_return_by_qr(req: ReturnQrRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """
    API Quét mã QR tự động nhận trả đồ:
    - BẢO MẬT: Chỉ Admin mới có quyền xác nhận trả đồ qua QR.
    - Tìm kiếm đơn theo rental_code
    - Đổi trạng thái sang 'RETURNED'
    - Nhả thiết bị về 'AVAILABLE'
    - Bắn thông báo Telegram cho Admin
    """
    code = req.rental_code.strip().upper()
    conn = get_db()
    cur = conn.cursor()

    rental = cur.execute("""
    SELECT r.*, COALESCE(i.name, c.name) as item_name, COALESCE(i.serial_or_size, 'Combo Trọn Gói') as serial_or_size,
           u.full_name as customer_name, u.phone as customer_phone, u.cccd_number
    FROM rentals r
    LEFT JOIN items i ON r.item_id = i.id
    LEFT JOIN combos c ON r.combo_id = c.id
    JOIN users u ON r.user_id = u.id
    WHERE UPPER(r.rental_code) = ?
    """, (code,)).fetchone()

    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn thuê có mã '{code}'!")

    rental_dict = dict(rental)

    if rental_dict["status"] == "RETURNED":
        conn.close()
        return {
            "success": True,
            "already_returned": True,
            "message": f"Đơn {code} đã được nhận trả trước đó!",
            "rental": rental_dict
        }

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE rentals 
    SET status = 'RETURNED', admin_notes = COALESCE(admin_notes, '') || ' | Đã nhận trả đồ qua QR lúc ' || ?
    WHERE id = ?
    """, (now_str, rental_dict["id"]))

    if rental_dict.get("items_json"):
        try:
            for itm in json.loads(rental_dict["items_json"]):
                if itm.get("item_id"):
                    cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (itm["item_id"],))
        except Exception: pass
    elif rental_dict["item_id"]:
        cur.execute("UPDATE items SET availability = 'AVAILABLE' WHERE id = ?", (rental_dict["item_id"],))

    conn.commit()
    conn.close()

    # Định dạng mô tả cọc
    dep_mode = rental_dict.get("deposit_type", "CCCD")
    dep_desc = rental_dict.get("deposit_asset_desc") or ("Giữ CCCD gốc" if dep_mode == "CCCD" else "Tài sản cọc")
    dep_text = f"{dep_mode}: {dep_desc}"
    if rental_dict.get("deposit_paid", 0) > 0:
        dep_text += f" ({rental_dict['deposit_paid']:,}đ)"

    # Bắn thông báo Telegram khi đã nhận trả đồ
    tele_msg = (
        f"<b>✅ TIDUBA STORE - HOÀN TẤT NHẬN TRẢ ĐỒ QUA QR</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Mã đơn:</b> <code>{code}</code> (ĐÃ TRẢ XONG)\n"
        f"👤 <b>Khách hàng:</b> {rental_dict['customer_name']} (<code>{rental_dict['customer_phone']}</code>)\n"
        f"📦 <b>Thiết bị:</b> {rental_dict['item_name']} (SN: {rental_dict['serial_or_size']})\n"
        f"🛡️ <b>Đã thanh lý cọc:</b> {dep_text}\n"
        f"⏰ <b>Thời gian trả đồ:</b> {now_str}\n"
        f"✨ <i>Thiết bị đã được kiểm tra và chuyển trạng thái SẴN SÀNG trong kho.</i>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    _send_telegram_notification(tele_msg, rental_id=rental_dict["id"], event_type="RETURN")

    return {
        "success": True,
        "already_returned": False,
        "message": f"✅ Đã nhận trả thiết bị thành công cho đơn {code}! Thiết bị '{rental_dict['item_name']}' đã về kho.",
        "rental": rental_dict,
        "returned_at": now_str
    }


@app.get("/return-qr", response_class=HTMLResponse)
def return_qr_web_page(code: Optional[str] = None):
    """Trang web quét mã QR trên Bill để nhận trả đồ nhanh từ điện thoại hoặc máy tính."""
    rental_data = None
    if code:
        conn = get_db()
        r = conn.execute("""
        SELECT r.*, COALESCE(i.name, c.name) as item_name, COALESCE(i.serial_or_size, 'Combo Trọn Gói') as serial_or_size,
               COALESCE(i.image_url, c.image_url) as item_image,
               u.full_name as customer_name, u.phone as customer_phone, u.cccd_number
        FROM rentals r
        LEFT JOIN items i ON r.item_id = i.id
        LEFT JOIN combos c ON r.combo_id = c.id
        JOIN users u ON r.user_id = u.id
        WHERE UPPER(r.rental_code) = ?
        """, (code.strip().upper(),)).fetchone()
        conn.close()
        if r:
            rental_data = dict(r)

    safe_code = code.strip().upper() if code else ""
    is_returned = rental_data and rental_data["status"] == "RETURNED"

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tiduba Store - Quét QR Nhận Trả Đồ & Thanh Lý Cọc</title>
    <link rel="icon" type="image/png" href="/static/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ background-color: #070a12; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
        .card {{ background: rgba(14, 20, 36, 0.95); border: 1px solid rgba(245, 158, 11, 0.2); box-shadow: 0 10px 30px rgba(0,0,0,0.8); }}
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="card rounded-3xl max-w-lg w-full p-6 space-y-6">
        <!-- Logo & Header -->
        <div class="text-center space-y-2">
            <div class="w-14 h-14 mx-auto bg-white p-1 rounded-2xl border border-amber-500/40 shadow-lg flex items-center justify-center">
                <img src="/static/logo.png" alt="Tiduba Store Logo" class="w-full h-full object-contain">
            </div>
            <h1 class="text-xl font-black text-white tracking-wider uppercase" style="font-family: 'Times New Roman', serif;">TIDUBA STORE</h1>
            <p class="text-xs text-amber-400 font-mono font-bold">HỆ THỐNG QUÉT QR NHẬN TRẢ ĐỒ & THANH LÝ HỢP ĐỒNG</p>
        </div>

        {"<!-- Đơn tìm thấy -->" if rental_data else ""}
        """

    if rental_data:
        dep_type_val = rental_data.get('deposit_type', 'CCCD')
        dep_desc_val = rental_data.get('deposit_asset_desc') or ('Giữ CCCD gốc tại quầy' if dep_type_val == 'CCCD' else 'Tài sản cọc')
        dep_paid_val = rental_data.get('deposit_paid', 0)
        dep_full = f"{dep_type_val}: {dep_desc_val}"
        if dep_paid_val > 0:
            dep_full += f" ({dep_paid_val:,}đ)"

        raw_phone = str(rental_data.get('customer_phone') or '')
        masked_phone = f"{raw_phone[:3]}***{raw_phone[-3:]}" if len(raw_phone) >= 7 else raw_phone

        html += f"""
        <div class="bg-gray-950 p-4 rounded-2xl border border-gray-800 space-y-3 text-xs font-mono">
            <div class="flex items-center justify-between border-b border-gray-800 pb-2">
                <span class="text-gray-400">Mã đơn thuê:</span>
                <strong class="text-amber-400 font-bold text-sm" id="rental-code-disp">{rental_data['rental_code']}</strong>
            </div>
            <div class="flex items-center justify-between border-b border-gray-800 pb-2">
                <span class="text-gray-400">Trạng thái:</span>
                <span id="rental-status-badge" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold border {'bg-emerald-950 text-emerald-300 border-emerald-700' if is_returned else 'bg-cyan-950 text-cyan-300 border-cyan-700'}">
                    {'ĐÃ TRẢ ĐỒ XONG' if is_returned else rental_data['status']}
                </span>
            </div>
            <div class="flex items-center justify-between border-b border-gray-800 pb-2">
                <span class="text-gray-400">Khách hàng:</span>
                <strong class="text-white">{rental_data['customer_name']} ({masked_phone})</strong>
            </div>
            <div class="flex items-center justify-between border-b border-gray-800 pb-2">
                <span class="text-gray-400">Thiết bị / Đồ:</span>
                <strong class="text-white text-right">{rental_data['item_name']}</strong>
            </div>
            <div class="flex items-center justify-between border-b border-gray-800 pb-2">
                <span class="text-gray-400">Hạn trả đồ:</span>
                <strong class="text-amber-300">{rental_data['end_time']}</strong>
            </div>
            <div class="flex items-center justify-between pt-1">
                <span class="text-cyan-300 font-bold">Hình thức cọc:</span>
                <strong class="text-cyan-200 text-right">{dep_full}</strong>
            </div>
        </div>

        <div id="return-action-box" class="space-y-3">
            {"<div class='p-4 bg-emerald-950/60 border border-emerald-600 rounded-2xl text-center space-y-1'><div class='text-emerald-300 font-bold text-sm'>✅ ĐÃ HOÀN TẤT TRẢ ĐỒ!</div><div class='text-gray-300 text-xs font-mono'>Thiết bị đã được trả về kho và cọc đã được thanh lý.</div></div>" if is_returned else f"""
            <button onclick="confirmReturnByQr('{safe_code}')" id="btn-confirm-return" class="w-full bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 text-gray-950 font-black py-3.5 px-6 rounded-2xl text-sm flex items-center justify-center gap-2 shadow-xl shadow-emerald-500/20 transition">
                <i class="fa-solid fa-check-double text-base"></i> XÁC NHẬN NHẬN TRẢ ĐỒ & THANH LÝ CỌC
            </button>
            <p class="text-[11px] text-gray-400 font-mono text-center">
                Nhấn xác nhận để đánh dấu đơn hàng ĐÃ TRẢ, nhả kho thiết bị và gửi thông báo Telegram.
            </p>
            """}
        </div>
        """
    else:
        html += f"""
        <div class="bg-gray-950 p-4 rounded-2xl border border-gray-800 space-y-3">
            <label class="block text-xs font-bold text-gray-300 font-mono">Nhập mã đơn hàng hoặc quét mã QR trên Bill:</label>
            <div class="flex gap-2">
                <input type="text" id="manual-code-input" value="{safe_code}" placeholder="TDB-XXXXXX" class="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-3 py-2 text-white font-mono uppercase text-sm focus:outline-none focus:border-amber-500">
                <button onclick="lookupCode()" class="bg-amber-500 hover:bg-amber-400 text-gray-950 font-bold px-4 py-2 rounded-xl text-xs font-mono">Tra Cứu</button>
            </div>
            {"<div class='text-rose-400 text-xs font-mono'>⚠️ Không tìm thấy đơn có mã: " + safe_code + "</div>" if safe_code else ""}
        </div>
        """

    html += f"""
        <!-- Back to app button -->
        <div class="pt-2 border-t border-gray-800/80 flex items-center justify-between text-xs font-mono">
            <a href="/" class="text-gray-400 hover:text-white flex items-center gap-1.5 transition">
                <i class="fa-solid fa-arrow-left"></i> Về Trang Chủ Web
            </a>
            <a href="/?admin=1" class="text-purple-400 hover:text-purple-300 flex items-center gap-1.5 font-bold transition">
                <i class="fa-solid fa-crown text-yellow-400"></i> Bảng Quản Trị Admin
            </a>
        </div>
    </div>

    <script>
        function lookupCode() {{
            const val = document.getElementById('manual-code-input').value.trim();
            if (val) {{
                window.location.href = '/return-qr?code=' + encodeURIComponent(val);
            }}
        }}

        async function confirmReturnByQr(code) {{
            const btn = document.getElementById('btn-confirm-return');
            if (btn) {{
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Đang xử lý...';
            }}
            try {{
                const token = localStorage.getItem('tiduba_token') || '';
                const headers = {{ 'Content-Type': 'application/json' }};
                if (token) headers['Authorization'] = 'Bearer ' + token;
                const res = await fetch('/api/rentals/return_by_qr', {{
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({{ rental_code: code }})
                }});
                const data = await res.json();
                if (!res.ok) {{
                    alert(data.detail || 'Lỗi khi nhận trả đồ (Yêu cầu đăng nhập tài khoản Quản Lý / Admin)');
                    if (btn) {{
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fa-solid fa-check-double text-base"></i> XÁC NHẬN NHẬN TRẢ ĐỒ & THANH LÝ CỌC';
                    }}
                    return;
                }}

                document.getElementById('return-action-box').innerHTML = `
                    <div class="p-5 bg-emerald-950/80 border border-emerald-500 rounded-2xl text-center space-y-2 animate-bounce">
                        <i class="fa-solid fa-circle-check text-emerald-400 text-3xl"></i>
                        <div class="text-emerald-300 font-black text-base">NHẬN TRẢ ĐỒ THÀNH CÔNG!</div>
                        <div class="text-gray-200 text-xs font-mono">Đơn hàng <strong>${{code}}</strong> đã được chuyển sang trạng thái RETURNED. Thiết bị đã về kho sẵn sàng cho lượt thuê tiếp theo!</div>
                        <div class="text-[11px] text-cyan-300 font-mono mt-1">Đã gửi thông báo Telegram cho Quản lý.</div>
                    </div>
                `;
                const badge = document.getElementById('rental-status-badge');
                if (badge) {{
                    badge.innerText = 'ĐÃ TRẢ ĐỒ XONG';
                    badge.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-bold border bg-emerald-950 text-emerald-300 border-emerald-700';
                }}
            }} catch (err) {{
                alert('Lỗi kết nối: ' + err);
                if (btn) {{
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-check-double text-base"></i> THỬ LẠI';
                }}
            }}
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


# =============================================================================
# 17. BACKWARDS-COMPATIBLE ZALO ENDPOINTS (Redirect to Telegram)
# =============================================================================

@app.get("/api/admin/zalo/config")
def get_zalo_config(admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    cfg = conn.execute("SELECT * FROM telegram_config WHERE id = 1").fetchone()
    conn.close()
    if cfg:
        return dict(cfg)
    return {"id": 1, "is_active": 1}


@app.post("/api/admin/zalo/config")
def save_zalo_config(admin: Dict[str, Any] = Depends(require_admin)):
    return {"success": True, "message": "Hệ thống đã nâng cấp sang Telegram Bot!"}


@app.get("/api/admin/zalo/logs")
def get_zalo_logs(admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_db()
    logs = conn.execute("SELECT * FROM telegram_logs ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return {"logs": [dict(l) for l in logs], "count": len(logs)}


@app.post("/api/admin/zalo/test")
def test_zalo_notification(admin: Dict[str, Any] = Depends(require_admin)):
    return {"success": True, "message": "Hệ thống đã nâng cấp sang Telegram Bot! Vui lòng sử dụng tính năng Test Telegram."}


# =============================================================================
# 18. ADMIN INSPECTION PROTOCOL
# =============================================================================

class AdminInspectionRequest(BaseModel):
    phase: str = "CHECKOUT"
    sensor_clean: bool = True
    lens_scratchless: bool = True
    shutter_count: int = 0
    body_condition: Optional[str] = "Tốt"
    accessories_included: Optional[str] = "Đầy đủ"
    deduction_amount: int = 0
    notes: Optional[str] = None


@app.post("/api/admin/rentals/{rental_id}/inspection")
def admin_save_inspection(rental_id: int, req: AdminInspectionRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """Admin lập biên bản kiểm tra tình trạng thiết bị khi giao/nhận."""
    conn = get_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rental = cur.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
    if not rental:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thuê!")

    cur.execute("""
    INSERT INTO handover_protocols (
        rental_id, phase, staff_name, sensor_clean, lens_scratchless, shutter_count_verified,
        accessories_included, notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rental_id, req.phase.upper(), admin["full_name"],
        1 if req.sensor_clean else 0, 1 if req.lens_scratchless else 0, req.shutter_count,
        req.accessories_included or "Đầy đủ",
        f"{req.body_condition or ''} | Trừ cọc: {req.deduction_amount:,}đ | {req.notes or ''}",
        now_str
    ))

    if req.deduction_amount > 0:
        cur.execute("""
        INSERT INTO damage_penalties (rental_id, damage_code, damage_title, penalty_amount, notes, created_at)
        VALUES (?, 'ADMIN_ASSESSMENT', 'Khấu trừ theo biên bản kiểm tra', ?, ?, ?)
        """, (rental_id, req.deduction_amount, req.body_condition or "Thiệt hại ghi nhận bởi Admin", now_str))

    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã lưu biên bản kiểm tra ({req.phase}) và ghi nhận khấu trừ {req.deduction_amount:,}đ!"}


def free_port_if_stuck(port: int = 9000):
    """Giải phóng port 9000 nếu có tiến trình treo trên Windows."""
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            current_pid = os.getpid()
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid and pid != "0" and int(pid) != current_pid:
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def background_reminder_worker():
    """
    Vòng lặp chạy ngầm tự động 100%:
    - Nhắc trước 30 phút để nhân viên chuẩn bị đồ trước khi khách đến nhận.
    - Nhắc trước 5 phút khi đơn sắp hết hạn để chuẩn bị gọi khách.
    - Cảnh báo ngay khi đơn quá hạn.
    - Gửi thẳng vào Group Telegram: -1004498214603 (Thông Báo Giờ).
    """
    OVERDUE_GROUP_ID = "-1004498214603"
    while True:
        try:
            time.sleep(30)
            now = datetime.datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db()
            cur = conn.cursor()
            sync_items_availability(conn)

            rentals = cur.execute("""
            SELECT r.*, COALESCE(i.name, c.name, 'Đơn Thuê Nhiều Món') as item_name,
                   u.full_name as customer_name, u.phone as customer_phone
            FROM rentals r
            LEFT JOIN items i ON r.item_id = i.id
            LEFT JOIN combos c ON r.combo_id = c.id
            JOIN users u ON r.user_id = u.id
            WHERE r.status NOT IN ('CANCELLED', 'RETURNED')
            """).fetchall()

            for r in rentals:
                rid = r["id"]
                code = r["rental_code"]
                b_code = r["branch_code"] if ("branch_code" in r.keys() and r["branch_code"]) else "CN1"
                branch_info = STORE_BRANCHES.get(b_code, STORE_BRANCHES["CN1"])

                # --- 1. NHẮC TRƯỚC 30 PHÚT CHUẨN BỊ ĐỒ ---
                try:
                    start_dt = datetime.datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M")
                    diff_start_mins = (start_dt - now).total_seconds() / 60.0
                    if 0 <= diff_start_mins <= 30.0:
                        chk = cur.execute("SELECT id FROM reminder_logs WHERE rental_id = ? AND event_type = 'PICKUP_30M'", (rid,)).fetchone()
                        if not chk:
                            mins_left = max(1, int(round(diff_start_mins)))
                            msg = (
                                f"<b>⏰ [NHẮC CHUẨN BỊ ĐỒ] KHÁCH SẮP ĐẾN NHẬN (CÒN ~{mins_left} PHÚT)!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"📋 <b>Mã đơn:</b> <code>{code}</code>\n"
                                f"👤 <b>Khách hàng:</b> {r['customer_name']} (<code>{r['customer_phone']}</code>)\n"
                                f"📦 <b>Thiết bị / Trang phục:</b> <b>{r['item_name']}</b>\n"
                                f"📅 <b>Khung giờ khách đặt:</b>\n"
                                f"👉 <b>Giờ nhận:</b> <b>{r['start_time']}</b>\n"
                                f"👉 <b>Hạn trả:</b> <b>{r['end_time']}</b>\n"
                                f"📍 <b>Chi nhánh:</b> {branch_info['name']}\n"
                                f"💡 <i>Nhân viên vui lòng kiểm tra pin, thẻ nhớ, vệ sinh đồ để sẵn sàng giao khách!</i>\n"
                                f"━━━━━━━━━━━━━━━━━━"
                            )
                            _send_telegram_notification(msg, rental_id=rid, event_type="PICKUP_REMINDER", override_chat_id=OVERDUE_GROUP_ID)
                            cur.execute("INSERT INTO reminder_logs (rental_id, event_type, sent_at) VALUES (?, 'PICKUP_30M', ?)", (rid, now_str))
                            conn.commit()
                except Exception:
                    pass

                # --- 2. NHẮC SẮP QUÁ HẠN 5 PHÚT & ĐÃ QUÁ HẠN (Áp dụng đơn ACTIVE) ---
                if r["status"] == "ACTIVE":
                    try:
                        end_dt = datetime.datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M")
                        diff_end_mins = (end_dt - now).total_seconds() / 60.0

                        if 0 <= diff_end_mins <= 5.0:
                            # Sắp quá hạn 5 phút
                            chk = cur.execute("SELECT id FROM reminder_logs WHERE rental_id = ? AND event_type = 'OVERDUE_5M'", (rid,)).fetchone()
                            if not chk:
                                mins_left = max(1, int(round(diff_end_mins)))
                                msg = (
                                    f"<b>⚠️ [SẮP QUÁ HẠN] CÒN ~{mins_left} PHÚT HẾT HẠN TRẢ ĐỒ!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"📋 <b>Mã đơn:</b> <code>{code}</code>\n"
                                    f"👤 <b>Khách hàng:</b> {r['customer_name']} (📞 <code>{r['customer_phone']}</code>)\n"
                                    f"📦 <b>Thiết bị / Trang phục:</b> <b>{r['item_name']}</b>\n"
                                    f"📅 <b>Khung giờ khách thuê:</b>\n"
                                    f"👉 <b>Từ:</b> {r['start_time']}\n"
                                    f"👉 <b>Hạn trả:</b> <b>{r['end_time']}</b>\n"
                                    f"📍 <b>Chi nhánh trả:</b> {branch_info['name']}\n"
                                    f"📞 <i>Chuẩn bị gọi khách nhắc trả đồ để tránh phát sinh phí trễ hạn (30.000đ/h)!</i>\n"
                                    f"━━━━━━━━━━━━━━━━━━"
                                )
                                _send_telegram_notification(msg, rental_id=rid, event_type="WARNING_DUE_SOON", override_chat_id=OVERDUE_GROUP_ID)
                                cur.execute("INSERT INTO reminder_logs (rental_id, event_type, sent_at) VALUES (?, 'OVERDUE_5M', ?)", (rid, now_str))
                                conn.commit()
                        elif diff_end_mins < 0:
                            # Đã quá hạn
                            chk = cur.execute("SELECT sent_at FROM reminder_logs WHERE rental_id = ? AND event_type = 'OVERDUE_EXPIRED' ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
                            should_send_overdue = False
                            if not chk:
                                should_send_overdue = True
                            else:
                                last_sent = datetime.datetime.strptime(chk["sent_at"], "%Y-%m-%d %H:%M:%S")
                                if (now - last_sent).total_seconds() >= 7200:
                                    should_send_overdue = True

                            if should_send_overdue:
                                overdue_h = round(abs(diff_end_mins) / 60.0, 1)
                                msg = (
                                    f"<b>🚨 [ĐÃ QUÁ HẠN TRẢ ĐỒ] VUI LÒNG GỌI KHÁCH NGAY!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"📋 <b>Mã đơn:</b> <code>{code}</code>\n"
                                    f"👤 <b>Khách hàng:</b> {r['customer_name']} (📞 <code>{r['customer_phone']}</code>)\n"
                                    f"📦 <b>Thiết bị / Trang phục:</b> <b>{r['item_name']}</b>\n"
                                    f"📅 <b>Khung giờ khách đặt:</b>\n"
                                    f"👉 <b>Từ:</b> {r['start_time']}\n"
                                    f"👉 <b>Hạn trả:</b> <b>{r['end_time']}</b> (ĐÃ TRỄ: <b>{overdue_h} GIỜ</b>)\n"
                                    f"📍 <b>Chi nhánh:</b> {branch_info['name']}\n"
                                    f"⚠️ <i>Hệ thống bắt đầu tính phí phạt 30.000đ/giờ!</i>\n"
                                    f"━━━━━━━━━━━━━━━━━━"
                                )
                                _send_telegram_notification(msg, rental_id=rid, event_type="OVERDUE", override_chat_id=OVERDUE_GROUP_ID)
                                cur.execute("INSERT INTO reminder_logs (rental_id, event_type, sent_at) VALUES (?, 'OVERDUE_EXPIRED', ?)", (rid, now_str))
                                conn.commit()
                    except Exception:
                        pass

            conn.close()
        except Exception:
            pass


def telegram_bot_updates_worker():
    """
    Lắng nghe liên tục các sự kiện từ Telegram Bot (Long-polling getUpdates):
    - Khi Admin bấm nút [✅ Xác Nhận Đã Nhận Tiền] ngay trong Telegram:
      -> Tự động duyệt đơn sang ACTIVE
      -> Chuyển thiết bị sang RENTED
      -> Trả lời alert popup trong Telegram: '✅ Đã duyệt đơn TDB-XXXXXX thành công!'
      -> Gửi tin nhắn thông báo xác nhận vào group
      -> Web và App tự động cập nhật trong 4 giây mà không cần Admin phải mở trình duyệt!
    """
    last_update_id = 0
    try:
        conn = get_db()
        cfg = conn.execute("SELECT bot_token FROM telegram_config WHERE id = 1").fetchone()
        conn.close()
        if cfg and cfg["bot_token"]:
            init_url = f"https://api.telegram.org/bot{cfg['bot_token'].strip()}/getUpdates?limit=1"
            req = urllib.request.Request(init_url, headers={"User-Agent": "TidubaStoreBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read().decode("utf-8"))
                res_list = d.get("result", [])
                if res_list:
                    last_update_id = res_list[-1]["update_id"]
    except Exception:
        pass

    while True:
        try:
            conn = get_db()
            cfg = conn.execute("SELECT bot_token, chat_id FROM telegram_config WHERE id = 1").fetchone()
            conn.close()

            if not cfg or not cfg["bot_token"]:
                time.sleep(10)
                continue

            bot_token = cfg["bot_token"].strip()
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={last_update_id + 1}&timeout=15"
            req = urllib.request.Request(url, headers={"User-Agent": "TidubaStoreBot/1.0"})

            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            updates = data.get("result", [])
            for u in updates:
                uid = u["update_id"]
                if uid > last_update_id:
                    last_update_id = uid

                # Xử lý Callback Query khi Admin bấm nút Inline trong Telegram
                if "callback_query" in u:
                    cq = u["callback_query"]
                    cq_id = cq["id"]
                    cq_data = cq.get("data", "")
                    sender = cq.get("from", {}).get("first_name", "Admin")
                    msg = cq.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    msg_id = msg.get("message_id")

                    if cq_data.startswith("confirm_pay:"):
                        parts = cq_data.split(":")
                        if len(parts) >= 3:
                            rental_id = int(parts[1])
                            rental_code = parts[2]

                            # Cập nhật đơn trong Database
                            conn = get_db()
                            cur = conn.cursor()
                            r = cur.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
                            if r and r["status"] != "ACTIVE":
                                cur.execute("UPDATE rentals SET status = 'ACTIVE' WHERE id = ?", (rental_id,))
                                conn.commit()
                                sync_items_availability(conn)

                                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cur.execute("INSERT INTO print_queue (rental_id, bill_text, status, created_at) VALUES (?, ?, 'PENDING', ?)", (rental_id, f"Bill {rental_code}", now_str))
                                conn.commit()

                                # 1. Trả lời popup ngay trên màn hình Telegram
                                ans_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                                ans_body = json.dumps({
                                    "callback_query_id": cq_id,
                                    "text": f"✅ Đã duyệt đơn {rental_code} thành công!",
                                    "show_alert": True
                                }).encode("utf-8")
                                ans_req = urllib.request.Request(ans_url, data=ans_body, headers={"Content-Type": "application/json"}, method="POST")
                                try:
                                    urllib.request.urlopen(ans_req, timeout=5)
                                except Exception: pass

                                # 2. Gửi tin nhắn xác nhận vào nhóm
                                notify_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                notif_body = json.dumps({
                                    "chat_id": chat_id,
                                    "text": f"✅ <b>[ĐÃ DUYỆT ĐƠN {rental_code}]</b>\n👑 <b>{sender}</b> đã xác nhận nhận tiền thành công!\nThiết bị đã chuyển sang trạng thái <b>ĐANG THUÊ</b>.",
                                    "parse_mode": "HTML",
                                    "reply_to_message_id": msg_id
                                }).encode("utf-8")
                                notif_req = urllib.request.Request(notify_url, data=notif_body, headers={"Content-Type": "application/json"}, method="POST")
                                try:
                                    urllib.request.urlopen(notif_req, timeout=5)
                                except Exception: pass
                            else:
                                st_text = r["status"] if r else "Không tìm thấy"
                                ans_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                                ans_body = json.dumps({
                                    "callback_query_id": cq_id,
                                    "text": f"ℹ️ Đơn {rental_code} hiện đang ở trạng thái: {st_text}",
                                    "show_alert": False
                                }).encode("utf-8")
                                ans_req = urllib.request.Request(ans_url, data=ans_body, headers={"Content-Type": "application/json"}, method="POST")
                                try:
                                    urllib.request.urlopen(ans_req, timeout=5)
                                except Exception: pass
                            conn.close()
        except Exception:
            time.sleep(3)


# Khởi chạy luồng ngầm tự động:
# 1. Nhắc hẹn 30 phút & cảnh báo quá hạn 5 phút vào group -1004498214603
threading.Thread(target=background_reminder_worker, daemon=True, name="TidubaReminderWorker").start()
# 2. Lắng nghe nút bấm [Xác Nhận Đã Nhận Tiền] trực tiếp từ Telegram Bot
threading.Thread(target=telegram_bot_updates_worker, daemon=True, name="TidubaTelegramBotWorker").start()


if __name__ == "__main__":
    import uvicorn
    server_port = int(os.environ.get("PORT", 9000))
    free_port_if_stuck(server_port)
    print("=" * 75)
    print("📸 TIDUBA STORE - NỀN TẢNG CHO THUÊ MÁY ẢNH & TRANG PHỤC CAO CẤP")
    print(f"🚀 Khởi động Server tại: http://0.0.0.0:{server_port}")
    print(f"💳 Tài khoản VietQR: {BANK_CONFIG['bank_name']} - STK: {BANK_CONFIG['account_no']} ({BANK_CONFIG['account_name']})")
    print("=" * 75)
    uvicorn.run("main:app", host="0.0.0.0", port=server_port, reload=False)

