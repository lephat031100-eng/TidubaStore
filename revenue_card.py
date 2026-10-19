"""
TIDUBA STORE - REVENUE INFOGRAPHIC CARD GENERATOR
Vẽ ảnh thẻ báo cáo doanh thu sang trọng 100% chuẩn giao diện Dashboard Dark Luxury
để gửi trực tiếp làm ảnh trong Telegram Bot!
"""

import os
import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Lấy font chữ Segoe UI hoặc Arial tiếng Việt chuẩn nét."""
    paths = [
        BASE_DIR / "static" / "fonts" / ("bold.ttf" if bold else "regular.ttf"),
        Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for p in paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def format_short_currency(val: int) -> str:
    """Định dạng tiền ngắn gọn: 1500000 -> 1.5M, 710000 -> 710k, 0 -> 0đ."""
    v = int(val or 0)
    if v == 0:
        return "0đ"
    if v >= 1_000_000:
        millions = v / 1_000_000
        return f"{millions:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        thousands = v / 1_000
        return f"{thousands:.0f}k"
    return f"{v:,}đ"


def draw_rounded_card(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    """Vẽ hình chữ nhật bo tròn góc."""
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def generate_revenue_card_image(metrics: Dict[str, Any], output_path: Optional[str] = None) -> Image.Image:
    """Tạo file ảnh đồ họa 1280x720 chuẩn HD cực kỳ sang trọng."""
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), "#050b14")
    draw = ImageDraw.Draw(im)

    # Gradient background tinh tế
    for y in range(H):
        # Chuyển sắc từ #060c18 sang #0a1324
        ratio = y / H
        r = int(6 + ratio * 4)
        g = int(12 + ratio * 7)
        b = int(24 + ratio * 12)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Khung Card Lớn Bao Quanh
    margin_x, margin_y = 35, 25
    card_w = W - 2 * margin_x
    card_h = H - 2 * margin_y
    draw_rounded_card(
        draw,
        (margin_x, margin_y, margin_x + card_w, margin_y + card_h),
        radius=26,
        fill="#0b1526",
        outline="#1e293b",
        width=2
    )

    # 1. HEADER
    f_header = get_font(24, bold=True)
    f_sub = get_font(18, bold=False)
    f_title_bold = get_font(20, bold=True)
    f_hero_num = get_font(52, bold=True)
    f_body = get_font(17, bold=False)
    f_badge = get_font(13, bold=True)

    header_y = margin_y + 24
    header_x = margin_x + 32

    # Logo Tiduba Store
    logo_path = BASE_DIR / "static" / "logo.png"
    if logo_path.exists():
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_img.thumbnail((44, 44), Image.Resampling.LANCZOS)
            im.paste(logo_img, (header_x, header_y - 4), logo_img)
            text_header_x = header_x + 54
        except Exception:
            text_header_x = header_x
    else:
        text_header_x = header_x

    draw.text((text_header_x, header_y), "TIDUBA STORE", font=get_font(16, bold=True), fill="#c86d51")
    draw.text((text_header_x + 130, header_y - 2), "BÁO CÁO DOANH THU", font=f_header, fill="#ffffff")

    # Ngày giờ góc phải
    now_dt = datetime.datetime.now()
    now_time_str = now_dt.strftime("%d/%m/%Y • %H:%M:%S")
    draw.text((margin_x + card_w - 32, header_y + 3), now_time_str, font=f_sub, fill="#94a3b8", anchor="ra")

    # Đường phân cách mảnh dưới header
    draw.line(
        [(margin_x + 28, header_y + 44), (margin_x + card_w - 28, header_y + 44)],
        fill="#1e293b",
        width=1
    )

    # 2. KHỐI TỔNG QUAN DOANH THU (BÊN TRÁI)
    box_left_x1 = margin_x + 28
    box_left_y1 = header_y + 60
    box_left_w = 640
    box_left_h = 230

    draw_rounded_card(
        draw,
        (box_left_x1, box_left_y1, box_left_x1 + box_left_w, box_left_y1 + box_left_h),
        radius=20,
        fill="#111f35",
        outline="#1e293b",
        width=2
    )

    # Nội dung cột trái
    total_rev = metrics.get("total_revenue", 0)
    total_rent = metrics.get("total_rent", 0)
    total_late = metrics.get("total_late", 0)
    total_bills = metrics.get("total_bills", 0)
    cn1 = metrics.get("bills_cn1", 0)
    cn2 = metrics.get("bills_cn2", 0)

    draw.text((box_left_x1 + 28, box_left_y1 + 22), "DOANH THU HÔM NAY:", font=f_title_bold, fill="#ffffff")
    draw.text((box_left_x1 + 28, box_left_y1 + 52), f"{total_rev:,}đ", font=f_hero_num, fill="#facc15")

    short_rent = format_short_currency(total_rent)
    short_late = format_short_currency(total_late)
    draw.text(
        (box_left_x1 + 28, box_left_y1 + 130),
        f"Thuê: {short_rent}  |  Phụ thu/Trễ: {short_late}",
        font=f_body,
        fill="#94a3b8"
    )

    draw.text(
        (box_left_x1 + 28, box_left_y1 + 164),
        f"Tổng đơn: {total_bills} bill  (CN1: {cn1}  |  CN2: {cn2})",
        font=get_font(18, bold=True),
        fill="#cbd5e1"
    )

    # 3. HAI THẺ BÊN PHẢI (THIẾT BỊ & TIỀN CỌC)
    box_right_x1 = box_left_x1 + box_left_w + 20
    box_right_w = (margin_x + card_w - 28) - box_right_x1

    # Thẻ Thiết bị
    box_dev_y1 = box_left_y1
    box_dev_h = 105
    draw_rounded_card(
        draw,
        (box_right_x1, box_dev_y1, box_right_x1 + box_right_w, box_dev_y1 + box_dev_h),
        radius=18,
        fill="#111f35",
        outline="#1e293b",
        width=2
    )

    # Vẽ icon hộp hàng
    draw.text((box_right_x1 + 24, box_dev_y1 + 30), "📦", font=get_font(28), fill="#f59e0b")
    draw.text((box_right_x1 + 78, box_dev_y1 + 20), "Thiết bị", font=f_title_bold, fill="#ffffff")
    ret_cnt = metrics.get("returned_count", 0)
    act_cnt = metrics.get("active_count", 0)
    draw.text(
        (box_right_x1 + 78, box_dev_y1 + 54),
        f"Đã trả: {ret_cnt}  |  Đang thuê: {act_cnt}",
        font=get_font(18, bold=True),
        fill="#cbd5e1"
    )

    # Thẻ Tiền Cọc
    box_dep_y1 = box_dev_y1 + box_dev_h + 20
    box_dep_h = 105
    draw_rounded_card(
        draw,
        (box_right_x1, box_dep_y1, box_right_x1 + box_right_w, box_dep_y1 + box_dep_h),
        radius=18,
        fill="#111f35",
        outline="#1e293b",
        width=2
    )

    draw.text((box_right_x1 + 24, box_dep_y1 + 30), "🛡️", font=get_font(28), fill="#38bdf8")
    draw.text((box_right_x1 + 78, box_dep_y1 + 20), "Tiền cọc", font=f_title_bold, fill="#ffffff")
    dep_paid = metrics.get("total_deposit_paid", 0)
    dep_ref = metrics.get("total_deposit_refunded", 0)
    draw.text(
        (box_right_x1 + 78, box_dep_y1 + 54),
        f"Thu: {format_short_currency(dep_paid)}  |  Hoàn: {format_short_currency(dep_ref)}",
        font=get_font(18, bold=True),
        fill="#38bdf8"
    )

    # 4. KHỐI CHI TIẾT ĐƠN HÀNG (BÊN DƯỚI)
    box_bot_x1 = box_left_x1
    box_bot_y1 = box_left_y1 + box_left_h + 20
    box_bot_w = margin_x + card_w - 28 - box_bot_x1
    box_bot_h = (margin_y + card_h - 26) - box_bot_y1

    draw_rounded_card(
        draw,
        (box_bot_x1, box_bot_y1, box_bot_x1 + box_bot_w, box_bot_y1 + box_bot_h),
        radius=20,
        fill="#111f35",
        outline="#1e293b",
        width=2
    )

    draw.text(
        (box_bot_x1 + 28, box_bot_y1 + 18),
        "CHI TIẾT ĐƠN HÀNG TRONG NGÀY",
        font=get_font(15, bold=True),
        fill="#94a3b8"
    )

    rentals = metrics.get("rentals", [])
    row_start_y = box_bot_y1 + 50
    row_height = 42

    if not rentals:
        draw.text(
            (box_bot_x1 + 28, row_start_y + 40),
            "Hôm nay chưa có đơn thuê nào phát sinh.",
            font=f_body,
            fill="#64748b"
        )
    else:
        for idx, r in enumerate(rentals[:4], 1):
            curr_y = row_start_y + (idx - 1) * row_height
            # Kẻ dòng mờ phân cách giữa các đơn
            if idx > 1:
                draw.line(
                    [(box_bot_x1 + 20, curr_y - 6), (box_bot_x1 + box_bot_w - 20, curr_y - 6)],
                    fill="#172640",
                    width=1
                )

            code = r.get("rental_code", "")
            cus = r.get("customer_name", "Khách")
            price = r.get("total_price", 0)
            dep = r.get("deposit_paid", 0)
            st = r.get("status", "ACTIVE")

            dep_str = f" (Cọc {format_short_currency(dep)})" if dep > 0 else ""
            line_txt = f"{idx}. {code}  •  {cus}  •  {price:,}đ{dep_str}"
            draw.text((box_bot_x1 + 28, curr_y), line_txt, font=get_font(16, bold=True), fill="#f1f5f9")

            # Badge trạng thái bên phải
            badge_x2 = box_bot_x1 + box_bot_w - 28
            if st == "RETURNED":
                bg_badge = "#14532d"
                bd_badge = "#16a34a"
                fg_badge = "#4ade80"
                txt_badge = "✓ Đã trả"
            elif st == "ACTIVE":
                bg_badge = "#713f12"
                bd_badge = "#ca8a04"
                fg_badge = "#fde047"
                txt_badge = "⏳ Đang thuê"
            elif st == "OVERDUE":
                bg_badge = "#881337"
                bd_badge = "#e11d48"
                fg_badge = "#fda4af"
                txt_badge = "🚨 Quá hạn"
            else:
                bg_badge = "#1e293b"
                bd_badge = "#475569"
                fg_badge = "#94a3b8"
                txt_badge = st

            badge_w, badge_h = 100, 26
            badge_box = (badge_x2 - badge_w, curr_y - 2, badge_x2, curr_y - 2 + badge_h)
            draw_rounded_card(draw, badge_box, radius=8, fill=bg_badge, outline=bd_badge, width=1)
            draw.text((badge_x2 - badge_w // 2, curr_y + 2), txt_badge, font=f_badge, fill=fg_badge, anchor="mt")

        if len(rentals) > 4:
            draw.text(
                (box_bot_x1 + 28, row_start_y + 4 * row_height + 4),
                f"... và {len(rentals) - 4} đơn hàng khác trong ngày.",
                font=get_font(13),
                fill="#64748b"
            )

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        im.save(str(out_p), format="PNG", quality=95)

    return im
