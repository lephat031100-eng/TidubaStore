# One-Click Launch Script cho Tiduba Store trên Windows PowerShell
$root = $PSScriptRoot

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "📸 KHỞI ĐỘNG TIDUBA STORE - HỆ THỐNG THUÊ MÁY ẢNH & TRANG PHỤC" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Kiểm tra port 9000
$conn = Get-NetTCPConnection -LocalPort 9000 -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "[*] Giải phóng port 9000 (PID: $($conn.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}

$python = "F:\AI\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

# Khởi chạy main.py
Write-Host "[*] Đang khởi động Tiduba Store trên http://localhost:9000..." -ForegroundColor Green
Start-Process -FilePath $python -ArgumentList "main.py" -WorkingDirectory $root

Start-Sleep -Seconds 2
Write-Host "[+] Tiduba Store đã online thành công!" -ForegroundColor Green
Write-Host "• Truy cập trình duyệt : http://localhost:9000" -ForegroundColor Yellow
Write-Host "• Tài khoản Admin mẫu  : admin / admin123" -ForegroundColor Yellow
Write-Host "• Tài khoản Khách mẫu  : khachhang / 123456" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan

Start-Process "http://localhost:9000"
