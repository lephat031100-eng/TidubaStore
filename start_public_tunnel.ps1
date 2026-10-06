# =============================================================================
# TIDUBASTORE.COM - KHỞI CHẠY HỆ THỐNG & ĐƯỜNG TRUYỀN CÔNG KHAI
# =============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   📸 TIDUBASTORE.COM - CHO THUÊ MÁY ẢNH & TRANG PHỤC GIA LAI" -ForegroundColor Yellow
Write-Host "   CN1: 183A Huỳnh Thúc Kháng, Pleiku | CN2: 801 Lê Duẩn, Pleiku" -ForegroundColor White
Write-Host "   Hotline / Zalo: 0977.078.981" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $CurrentDir

# 1. Kiểm tra Backend server port 9000
$portListening = Get-NetTCPConnection -LocalPort 9000 -State Listen -ErrorAction SilentlyContinue
if (-not $portListening) {
    Write-Host "[*] Đang khởi chạy Server Backend port 9000..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn main:app --host 0.0.0.0 --port 9000" -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

Write-Host "[+] Web nội bộ máy tính:" -ForegroundColor Green
Write-Host "    👉 http://tidubastore.com (Cổng 80 - Gõ thẳng trên trình duyệt)" -ForegroundColor Cyan
Write-Host "    👉 http://127.0.0.1:9000" -ForegroundColor Cyan

# 2. Khởi chạy Cloudflare Tunnel công khai
if (Test-Path "$CurrentDir\cloudflared.exe") {
    Write-Host "`n[*] Đang tạo link công khai Internet qua Cloudflare Tunnel..." -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
    & "$CurrentDir\cloudflared.exe" tunnel --url http://127.0.0.1:9000
} else {
    Write-Host "[*] Khởi chạy qua LocalTunnel..." -ForegroundColor Yellow
    npx --yes localtunnel --port 9000 --subdomain tidubastore
}
