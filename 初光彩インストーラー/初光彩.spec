# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\uto\\Desktop\\初光彩インストーラー\\system\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\uto\\Desktop\\初光彩インストーラー\\system\\install.bat', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='初光彩',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\uto\\Desktop\\初光彩インストーラー\\system\\image\\icon.ico'],
)
