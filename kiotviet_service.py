"""
TIDUBA STORE - KIOTVIET INTEGRATION SERVICE
Module đồng bộ kho hàng chuyên sâu giữa KiotViet và Tiduba Store:
1. Đồng bộ Trực tuyến qua KiotViet Open API (OAuth 2.0 Client Credentials).
2. Nhập kho hàng loạt từ File Excel (.xlsx) / CSV xuất từ KiotViet.
3. Tự động ánh xạ danh mục, giá thuê theo ca (4h/8h/24h), tồn kho và hình ảnh.
"""

import re
import io
import csv
import json
import sqlite3
import datetime
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


def parse_kiotviet_price(val: Any) -> int:
    """
    Chuyển đổi giá trị tiền tệ KiotViet sang số nguyên (VNĐ) chuẩn xác 100%:
    - Xử lý float từ openpyxl: 350000.0 -> 350000 (KHÔNG bị nhân 10 thành 3.500.000)
    - Xử lý chuỗi định dạng: '350.000 đ' -> 350000, '350,000' -> 350000
    - Giữ nguyên giá KiotViet, KHÔNG tự ý kẹp giá tối thiểu 50k hay mặc định 100k.
    """
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(round(val)))
    s = str(val).strip()
    s = re.sub(r'[đĐ\sVNDvnd]', '', s)
    if not s:
        return 0
    # Chuỗi số thực float từ excel dạng '350000.0' hoặc '350000.00'
    if s.endswith('.0'):
        s = s[:-2]
    elif s.endswith('.00'):
        s = s[:-3]
    # Lấy sạch các chữ số nguyên
    clean = re.sub(r'[^\d]', '', s)
    return int(clean) if clean else 0


def normalize_str(s: str) -> str:
    """Chuẩn hóa chuỗi tìm kiếm không dấu, chữ thường."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[đ]', 'd', s)
    return s


def classify_product_category(cat_name: str, prod_name: str) -> Tuple[str, str, str]:
    """
    Phân loại thông minh sản phẩm KiotViet vào Tiduba Store:
    Trả về: (category, subcategory, brand)
    - category: 'CAMERA_GEAR' hoặc 'COSTUME_FASHION'
    """
    cn = normalize_str(cat_name)
    pn = normalize_str(prod_name)
    combined = f"{cn} {pn}"

    # 1. Phát hiện Brand
    brand = "Khác"
    if "sony" in combined:
        brand = "Sony"
    elif "canon" in combined:
        brand = "Canon"
    elif "fuji" in combined or "fujifilm" in combined:
        brand = "Fujifilm"
    elif "dji" in combined:
        brand = "DJI"
    elif "nikon" in combined:
        brand = "Nikon"
    elif "lumix" in combined or "panasonic" in combined:
        brand = "Lumix"
    elif "godox" in combined:
        brand = "Godox"
    elif "blackmagic" in combined:
        brand = "Blackmagic"
    elif any(k in combined for k in ["ao dai", "ao_dai", "aodai"]):
        brand = "Áo Dài"
    elif any(k in combined for k in ["co phuc", "viet phuc", "nhat binh", "tac"]):
        brand = "Việt Phục"
    elif any(k in combined for k in ["vay", "dam", "dress"]):
        brand = "Váy Tiệc"
    elif any(k in combined for k in ["yem"]):
        brand = "Yếm"
    elif any(k in combined for k in ["boot", "giay"]):
        brand = "Boot"
    elif any(k in combined for k in ["tui", "balo"]):
        brand = "Túi Xách"
    elif any(k in combined for k in ["phu kien"]):
        brand = "Phụ Kiện"

    # 2. Phát hiện Category lớn (CAMERA_GEAR vs COSTUME_FASHION)
    # Từ khóa máy ảnh phải chính xác từ ngữ, KHÔNG bắt từ đơn lẻ như 'den' (màu đen) hay 'sac' (sắc sảo/màu sắc)
    camera_keywords = [
        "may anh", "camera", "body", "lens", "ong kinh", "gimbal", "flycam", "drone",
        "tripod", "chan may", "chan may anh", "micro", "thu am", "den flash", "the nho", "pin sac",
        "ronin", "dji", "sony", "canon", "fujifilm", "nikon"
    ]
    costume_keywords = [
        "vay", "dam", "ao", "quan", "set", "trang phuc", "co phuc", "viet phuc",
        "nhat binh", "ao dai", "yem", "vest", "blazer", "khoac", "dong", "len",
        "du lich", "chup anh", "boot", "non", "khan", "bikini", "do boi", "suon xam",
        "dich vu", "phu kien", "tui", "giay", "guoc"
    ]

    is_costume = any(k in combined for k in costume_keywords)
    is_camera = any(k in combined for k in camera_keywords) or any(k in pn for k in ["r50", "m50", "sony", "canon", "fuji", "fujifilm", "nikon", "lumix", "blackmagic"])

    # Ưu tiên nếu tên sản phẩm hoặc nhóm hàng chứa váy/đầm/áo/set/bikini/dịch vụ thì 100% là COSTUME_FASHION
    if is_costume and not ("may anh" in combined or "camera" in combined or "lens" in combined or "flycam" in combined or "gimbal" in combined or "r50" in pn or "m50" in pn):
        category = "COSTUME_FASHION"
        if "bikini" in combined or "do boi" in combined:
            subcategory = "Bikini & Đồ Bơi"
        elif "suon xam" in combined:
            subcategory = "Sườn Xám"
        elif "ao dai" in combined:
            subcategory = "Áo Dài Thiết Kế"
        elif any(k in combined for k in ["co phuc", "viet phuc", "nhat binh"]):
            subcategory = "Việt Phục Hoàng Cung"
        elif "yem" in combined:
            subcategory = "Yếm Dân Gian"
        elif any(k in combined for k in ["vay", "dam", "cvay"]):
            subcategory = "Váy Tiệc"
        elif "khoac" in combined or "dong" in combined or "len" in combined or "choang" in combined:
            subcategory = "Áo Khoác"
        elif "du lich" in combined or "set" in combined:
            subcategory = "Du Lịch - Chụp Ảnh"
        elif any(k in combined for k in ["boot", "bot", "guoc", "giay", "dep"]):
            subcategory = "Boot"
        elif any(k in combined for k in ["tui", "balo"]):
            subcategory = "Túi Xách"
        elif any(k in combined for k in ["non", "mu"]):
            subcategory = "Nón & Mũ"
        else:
            subcategory = cat_name or "Trang Phục Concept"
    elif is_camera:
        category = "CAMERA_GEAR"
        if any(k in combined for k in ["lens", "ong kinh"]):
            subcategory = "Ống Kính (Lens)"
        elif any(k in combined for k in ["flycam", "drone"]):
            subcategory = "Flycam / Drone"
        elif any(k in combined for k in ["gimbal", "chong rung", "ronin"]):
            subcategory = "Gimbal Chống Rung"
        elif any(k in combined for k in ["den flash", "flash", "led"]):
            subcategory = "Đèn Flash & Ánh Sáng"
        elif any(k in combined for k in ["micro", "thu am"]):
            subcategory = "Micro Thu Âm"
        else:
            subcategory = "Máy Ảnh"
    else:
        # Mặc định theo nhóm hàng nếu là Dịch vụ hoặc Trang phục
        if any(k in cn for k in ["dich vu", "trang phuc", "thoi trang", "vay", "dam", "ao"]):
            category = "COSTUME_FASHION"
            subcategory = cat_name or "Trang Phục Concept"
        else:
            category = "CAMERA_GEAR"
            subcategory = cat_name or "Thiết Bị"

    # Nếu nhóm hàng KiotViet là chung chung như "Dịch vụ" hoặc "Hàng hóa", dùng từ khóa thông minh
    generic_cats = ["dich vu", "hang hoa", "san pham", "khac", ""]
    if cat_name and cat_name.strip() and normalize_str(cat_name) not in generic_cats:
        subcategory = cat_name.strip()

    return category, subcategory, brand


def get_kiotviet_token(client_id: str, client_secret: str) -> Tuple[bool, str]:
    """Lấy access_token từ máy chủ xác thực KiotViet OAuth 2.0."""
    url = "https://id.kiotviet.vn/connect/token"
    payload = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
        "grant_type": "client_credentials",
        "scopes": "PublicApi.Access"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "TidubaStore/3.5 (KiotViet Sync)"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token")
            if token:
                return True, token
            return False, "Không nhận được access_token từ KiotViet!"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return False, f"Lỗi xác thực KiotViet ({e.code}): {err_msg}"
    except Exception as e:
        return False, f"Lỗi kết nối máy chủ KiotViet: {str(e)}"


def fetch_kiotviet_categories(retailer: str, token: str) -> List[Dict[str, Any]]:
    """Lấy toàn bộ danh sách nhóm hàng từ KiotViet."""
    url = "https://public.kiotapi.com/categories"
    req = urllib.request.Request(
        url,
        headers={
            "Retailer": retailer.strip(),
            "Authorization": f"Bearer {token}",
            "User-Agent": "TidubaStore/3.5"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception as e:
        print(f"[KIOTVIET] Lỗi lấy nhóm hàng: {e}")
        return []


def fetch_kiotviet_products(retailer: str, token: str, page_size: int = 100) -> List[Dict[str, Any]]:
    """Lấy toàn bộ danh sách hàng hóa từ KiotViet (hỗ trợ phân trang đầy đủ)."""
    all_products = []
    current_item = 0

    while True:
        url = f"https://public.kiotapi.com/products?pageSize={page_size}&currentItem={current_item}&includeInventory=true"
        req = urllib.request.Request(
            url,
            headers={
                "Retailer": retailer.strip(),
                "Authorization": f"Bearer {token}",
                "User-Agent": "TidubaStore/3.5"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                prods = data.get("data", [])
                if not prods:
                    break
                all_products.extend(prods)
                total = data.get("total", 0)
                current_item += len(prods)
                if current_item >= total:
                    break
        except Exception as e:
            print(f"[KIOTVIET] Lỗi lấy hàng hóa tại currentItem {current_item}: {e}")
            break

    return all_products


def sync_kiotviet_to_database(db_conn: sqlite3.Connection, retailer: str, client_id: str, client_secret: str, branch_name: str = "") -> Dict[str, Any]:
    """
    Thực hiện kéo toàn bộ kho hàng KiotViet nạp vào Tiduba Store:
    1. Đồng bộ nhóm hàng -> categories_config
    2. Đồng bộ sản phẩm -> items
    3. Cập nhật tồn kho (onHand <= 0 -> UNAVAILABLE)
    """
    ok, token_or_err = get_kiotviet_token(client_id, client_secret)
    if not ok:
        return {"success": False, "message": token_or_err}

    token = token_or_err
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Đồng bộ Categories
    cats = fetch_kiotviet_categories(retailer, token)
    cat_synced = 0
    cur = db_conn.cursor()

    for c in cats:
        cid = c.get("categoryId")
        cname = (c.get("categoryName") or "").strip()
        if not cname:
            continue
        code = f"kv_cat_{cid}"
        exists = cur.execute("SELECT id FROM categories_config WHERE LOWER(name) = ? OR LOWER(code) = ?", (cname.lower(), code.lower())).fetchone()
        if not exists:
            max_order = cur.execute("SELECT MAX(display_order) as m FROM categories_config").fetchone()["m"] or 20
            cur.execute("""
            INSERT INTO categories_config (code, name, filter_type, filter_value, display_order, is_active)
            VALUES (?, ?, 'CATEGORY', ?, ?, 1)
            """, (code, cname, cname, max_order + 1))
            cat_synced += 1

    # 2. Đồng bộ Products
    products = fetch_kiotviet_products(retailer, token)
    created_count = 0
    updated_count = 0

    for p in products:
        kv_id = p.get("id")
        code = (p.get("code") or "").strip()
        name = (p.get("name") or "").strip()
        if not name:
            continue

        cat_name = p.get("categoryName") or ""
        base_price = parse_kiotviet_price(p.get("basePrice"))
        on_hand = int(p.get("onHand") or 0)
        is_active = p.get("isActive", True)

        category, subcategory, brand = classify_product_category(cat_name, name)

        # Giữ nguyên giá KiotViet 100%, không kẹp giá tối thiểu 50k
        price_24h = base_price
        if category == "COSTUME_FASHION":
            price_4h = price_24h
            price_8h = price_24h
        else:
            price_4h = int(price_24h * 0.5)
            price_8h = int(price_24h * 0.7)

        # Lấy hình ảnh
        images = p.get("images") or []
        image_url = images[0] if (images and isinstance(images, list) and images[0]) else "/static/logo.png"

        description = p.get("description") or f"Thiết bị / Trang phục từ kho KiotViet ({cat_name})"
        serial_or_size = code or f"KV-{kv_id}"

        # Kiểm tra tồn kho
        availability = "AVAILABLE" if (on_hand > 0 and is_active) else "UNAVAILABLE"

        # Kiểm tra xem sản phẩm đã có trong kho chưa (theo kiotviet_id, hoặc kiotviet_code, hoặc serial_or_size)
        existing = cur.execute("""
            SELECT id, availability FROM items 
            WHERE (kiotviet_id = ? AND kiotviet_id > 0)
               OR (kiotviet_code = ? AND kiotviet_code != '')
               OR serial_or_size = ?
        """, (kv_id, code, serial_or_size)).fetchone()

        if existing:
            # Nếu đang có người thuê (RENTED) thì giữ RENTED, không đè về AVAILABLE
            final_avail = existing["availability"] if existing["availability"] == "RENTED" else availability
            cur.execute("""
                UPDATE items 
                SET name = ?, category = ?, subcategory = ?, brand = ?,
                    price_4h = ?, price_8h = ?, price_24h = ?, image_url = COALESCE(NULLIF(image_url, '/static/logo.png'), ?),
                    description = ?, availability = ?, kiotviet_id = ?, kiotviet_code = ?, on_hand = ?
                WHERE id = ?
            """, (
                name, category, subcategory, brand, price_4h, price_8h, price_24h,
                image_url, description, final_avail, kv_id, code, on_hand, existing["id"]
            ))
            updated_count += 1
        else:
            cur.execute("""
                INSERT INTO items (
                    name, category, subcategory, brand, serial_or_size, mount_type,
                    shutter_count, measurements, price_4h, price_8h, price_24h, deposit_amount,
                    image_url, description, condition_status, availability, branch_code,
                    kiotviet_id, kiotviet_code, on_hand, created_at
                ) VALUES (?, ?, ?, ?, ?, '', 0, '', ?, ?, ?, 0, ?, ?, 'Đẹp 99%', ?, 'CN1', ?, ?, ?, ?)
            """, (
                name, category, subcategory, brand, serial_or_size, price_4h, price_8h, price_24h,
                image_url, description, availability, kv_id, code, on_hand, now_str
            ))
            created_count += 1

    # Cập nhật kiotviet_config log
    cur.execute("""
        UPDATE kiotviet_config
        SET last_sync_at = ?, last_sync_status = 'SUCCESS'
        WHERE id = 1
    """, (now_str,))

    # Ghi log
    cur.execute("""
        INSERT INTO kiotviet_sync_logs (sync_type, items_synced, status, detail, created_at)
        VALUES ('API_PRODUCTS', ?, 'SUCCESS', ?, ?)
    """, (len(products), f"Thêm mới: {created_count}, Cập nhật: {updated_count}, Nhóm hàng: {cat_synced}", now_str))

    db_conn.commit()

    return {
        "success": True,
        "message": f"🚀 Đồng bộ kho KiotViet thành công! Tổng {len(products)} sản phẩm (Thêm mới: {created_count}, Cập nhật: {updated_count}, Nhóm hàng: {cat_synced}).",
        "total_fetched": len(products),
        "created_count": created_count,
        "updated_count": updated_count,
        "categories_synced": cat_synced
    }


def import_kiotviet_excel_or_csv(db_conn: sqlite3.Connection, file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Nhập kho hàng loạt từ file Excel (.xlsx) hoặc CSV xuất từ KiotViet:
    - Tự động nhận diện cột Mã hàng, Tên hàng, Nhóm hàng, Giá bán, Tồn kho, Ảnh, Ghi chú.
    - Cập nhật kho và danh mục Tiduba Store ngay lập tức.
    """
    rows_data: List[Dict[str, Any]] = []
    fname = filename.lower()

    if fname.endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            header_row = None
            for r in rows_iter:
                # Tìm dòng tiêu đề
                str_r = [normalize_str(str(c or "")) for c in r]
                if any("ten hang" in c or "ma hang" in c or "ten san pham" in c for c in str_r):
                    header_row = [str(c or "").strip() for c in r]
                    break
            
            if not header_row:
                return {"success": False, "message": "Không tìm thấy dòng tiêu đề cột hợp lệ (Mã hàng, Tên hàng...) trong file Excel KiotViet!"}

            # Map index chính xác theo định dạng KiotViet:
            # Ưu tiên cột "Nhóm hàng" trước cột "Loại hàng"
            header_norm = [normalize_str(h) for h in header_row]
            idx_code = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ma hang", "ma vach", "code", "barcode"])), -1)
            idx_name = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ten hang", "ten san pham", "name"])), -1)
            
            # Ưu tiên "nhom hang" hoặc "nhom hang(3 cap)", KHÔNG lấy cột "loai hang" (chứa Dịch vụ)
            idx_cat = next((i for i, h in enumerate(header_norm) if "nhom hang" in h), -1)
            if idx_cat == -1:
                idx_cat = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["category", "nhom"])), -1)
            if idx_cat == -1:
                idx_cat = next((i for i, h in enumerate(header_norm) if "loai hang" in h), -1)

            idx_price = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["gia ban", "gia thue", "gia le", "price"])), -1)
            idx_stock = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ton kho", "so luong", "ton", "onhand", "qty"])), -1)
            idx_img = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["hinh anh", "anh", "image"])), -1)
            idx_desc = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["mo ta", "ghi chu", "description"])), -1)

            if idx_name == -1:
                return {"success": False, "message": "File Excel thiếu cột 'Tên hàng'!"}

            for r in rows_iter:
                if not any(r): continue
                name_val = str(r[idx_name] or "").strip() if idx_name < len(r) else ""
                if not name_val: continue
                code_val = str(r[idx_code] or "").strip() if idx_code != -1 and idx_code < len(r) and r[idx_code] is not None else ""
                cat_val = str(r[idx_cat] or "").strip() if idx_cat != -1 and idx_cat < len(r) and r[idx_cat] is not None else ""
                
                price_val = 0
                if idx_price != -1 and idx_price < len(r) and r[idx_price] is not None:
                    price_val = parse_kiotviet_price(r[idx_price])

                stock_val = 1
                if idx_stock != -1 and idx_stock < len(r) and r[idx_stock] is not None:
                    try:
                        stock_val = int(float(str(r[idx_stock]).replace(",", "").strip() or 0))
                    except Exception:
                        stock_val = 1

                img_val = str(r[idx_img] or "").strip() if idx_img != -1 and idx_img < len(r) and r[idx_img] is not None else ""
                desc_val = str(r[idx_desc] or "").strip() if idx_desc != -1 and idx_desc < len(r) and r[idx_desc] is not None else ""

                rows_data.append({
                    "code": code_val,
                    "name": name_val,
                    "categoryName": cat_val,
                    "basePrice": price_val,
                    "onHand": stock_val,
                    "image": img_val,
                    "description": desc_val
                })
        except Exception as e:
            return {"success": False, "message": f"Lỗi đọc file Excel KiotViet: {str(e)}"}
    else:
        # File CSV
        try:
            # Thử decode UTF-8, nếu lỗi thử Latin/Windows
            content_str = None
            for enc in ["utf-8-sig", "utf-8", "cp1258", "latin1"]:
                try:
                    content_str = file_content.decode(enc)
                    break
                except Exception:
                    pass
            if not content_str:
                return {"success": False, "message": "Không đọc được bảng mã của file CSV!"}

            reader = csv.reader(io.StringIO(content_str))
            header_row = None
            for r in reader:
                str_r = [normalize_str(c) for c in r]
                if any("ten hang" in c or "ma hang" in c for c in str_r):
                    header_row = r
                    break
            
            if not header_row:
                return {"success": False, "message": "Không tìm thấy dòng tiêu đề cột hợp lệ trong file CSV KiotViet!"}

            header_norm = [normalize_str(h) for h in header_row]
            idx_code = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ma hang", "code"])), -1)
            idx_name = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ten hang", "name"])), -1)
            
            idx_cat = next((i for i, h in enumerate(header_norm) if "nhom hang" in h), -1)
            if idx_cat == -1:
                idx_cat = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["category", "nhom"])), -1)
            if idx_cat == -1:
                idx_cat = next((i for i, h in enumerate(header_norm) if "loai hang" in h), -1)

            idx_price = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["gia ban", "price"])), -1)
            idx_stock = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["ton kho", "onhand"])), -1)
            idx_img = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["hinh anh", "image"])), -1)
            idx_desc = next((i for i, h in enumerate(header_norm) if any(k in h for k in ["mo ta", "description"])), -1)

            for r in reader:
                if not any(r): continue
                name_val = r[idx_name].strip() if idx_name < len(r) else ""
                if not name_val: continue
                code_val = r[idx_code].strip() if idx_code != -1 and idx_code < len(r) else ""
                cat_val = r[idx_cat].strip() if idx_cat != -1 and idx_cat < len(r) else ""
                price_val = parse_kiotviet_price(r[idx_price]) if idx_price != -1 and idx_price < len(r) else 0
                stock_val = int(re.sub(r'[^\d]', '', r[idx_stock]) or 1) if idx_stock != -1 and idx_stock < len(r) else 1
                img_val = r[idx_img].strip() if idx_img != -1 and idx_img < len(r) else ""
                desc_val = r[idx_desc].strip() if idx_desc != -1 and idx_desc < len(r) else ""

                rows_data.append({
                    "code": code_val,
                    "name": name_val,
                    "categoryName": cat_val,
                    "basePrice": price_val,
                    "onHand": stock_val,
                    "image": img_val,
                    "description": desc_val
                })
        except Exception as e:
            return {"success": False, "message": f"Lỗi đọc file CSV KiotViet: {str(e)}"}

    if not rows_data:
        return {"success": False, "message": "Không tìm thấy dữ liệu hàng hóa nào trong file!"}

    # Nạp dữ liệu vào Database
    cur = db_conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_count = 0
    updated_count = 0

    for item_row in rows_data:
        code = item_row["code"]
        name = item_row["name"]
        cat_name = item_row["categoryName"]
        base_price = item_row["basePrice"]
        on_hand = item_row["onHand"]
        img_url = item_row["image"] or "/static/logo.png"
        desc = item_row["description"] or f"Sản phẩm từ kho KiotViet ({cat_name})"

        category, subcategory, brand = classify_product_category(cat_name, name)
        # Giữ nguyên giá KiotViet 100%, không tự ý can thiệp giá
        price_24h = int(base_price)
        if category == "COSTUME_FASHION":
            price_4h = price_24h
            price_8h = price_24h
        else:
            price_4h = int(price_24h * 0.5)
            price_8h = int(price_24h * 0.7)
        serial_or_size = code or f"SP-{int(datetime.datetime.now().timestamp()*1000)%1000000}"
        availability = "AVAILABLE" if on_hand > 0 else "UNAVAILABLE"

        # Tự động tạo category chip nếu chưa có nhóm hàng này (ví dụ: Bikini, Đồ bơi...)
        if cat_name and cat_name.strip():
            clean_cat = cat_name.strip()
            c_code = normalize_str(clean_cat).replace(" ", "_")
            c_exists = cur.execute("SELECT id FROM categories_config WHERE LOWER(name) = ? OR LOWER(code) = ?", (clean_cat.lower(), c_code.lower())).fetchone()
            if not c_exists:
                max_order = cur.execute("SELECT MAX(display_order) as m FROM categories_config").fetchone()["m"] or 20
                cur.execute("""
                INSERT INTO categories_config (code, name, filter_type, filter_value, display_order, is_active)
                VALUES (?, ?, 'CATEGORY', ?, ?, 1)
                """, (c_code, clean_cat, clean_cat, max_order + 1))

        # Kiểm tra sản phẩm đã có chưa
        existing = cur.execute("""
            SELECT id, availability FROM items 
            WHERE (kiotviet_code = ? AND kiotviet_code != '')
               OR serial_or_size = ?
               OR name = ?
        """, (code, serial_or_size, name)).fetchone()

        if existing:
            final_avail = existing["availability"] if existing["availability"] == "RENTED" else availability
            cur.execute("""
                UPDATE items 
                SET name = ?, category = ?, subcategory = ?, brand = ?,
                    price_4h = ?, price_8h = ?, price_24h = ?, image_url = COALESCE(NULLIF(image_url, '/static/logo.png'), ?),
                    description = ?, availability = ?, kiotviet_code = ?, on_hand = ?
                WHERE id = ?
            """, (name, category, subcategory, brand, price_4h, price_8h, price_24h, img_url, desc, final_avail, code, on_hand, existing["id"]))
            updated_count += 1
        else:
            cur.execute("""
                INSERT INTO items (
                    name, category, subcategory, brand, serial_or_size, mount_type,
                    shutter_count, measurements, price_4h, price_8h, price_24h, deposit_amount,
                    image_url, description, condition_status, availability, branch_code,
                    kiotviet_id, kiotviet_code, on_hand, created_at
                ) VALUES (?, ?, ?, ?, ?, '', 0, '', ?, ?, ?, 0, ?, ?, 'Đẹp 99%', ?, 'CN1', 0, ?, ?, ?)
            """, (
                name, category, subcategory, brand, serial_or_size, price_4h, price_8h, price_24h,
                img_url, desc, availability, code, on_hand, now_str
            ))
            created_count += 1

    cur.execute("""
        INSERT INTO kiotviet_sync_logs (sync_type, items_synced, status, detail, created_at)
        VALUES ('EXCEL_IMPORT', ?, 'SUCCESS', ?, ?)
    """, (len(rows_data), f"File {filename}: Thêm mới {created_count}, Cập nhật {updated_count}", now_str))

    db_conn.commit()

    return {
        "success": True,
        "message": f"🎉 Nạp kho KiotViet từ file thành công! Đã nạp {len(rows_data)} sản phẩm (Thêm mới: {created_count}, Cập nhật: {updated_count}).",
        "total": len(rows_data),
        "created_count": created_count,
        "updated_count": updated_count
    }
