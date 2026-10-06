# -*- mode: python ; coding: utf-8 -*-
# TidubaStore Admin Desktop App - PyInstaller Spec
# Build: pyinstaller TidubaStoreAdmin.spec

import os
from pathlib import Path

BASE = Path(SPECPATH)

a = Analysis(
    ['admin_app.py'],
    pathex=[str(BASE)],
    binaries=[],
    datas=[
        # Đóng gói toàn bộ giao diện web và static vào exe
        (str(BASE / 'templates'), 'templates'),
        (str(BASE / 'static'), 'static'),
        (str(BASE / 'main.py'), '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.responses',
        'fastapi.middleware.cors',
        'pydantic',
        'pydantic.v1',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.staticfiles',
        'anyio',
        'anyio._backends._asyncio',
        'h11',
        'httptools',
        'websockets',
        'webview',
        'sqlite3',
        'hmac',
        'hashlib',
        'shutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL', 'cv2'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TidubaStoreAdmin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Không hiện cửa sổ console (app ẩn)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE / 'static' / 'favicon.png') if (BASE / 'static' / 'favicon.png').exists() else None,
)
