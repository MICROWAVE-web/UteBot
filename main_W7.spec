# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Z:\\Projects\\UteBot\\main_W7.py'],
    pathex=[],
    binaries=[],
    datas=[('Z:\\Projects\\UteBot\\icon.ico', '.'), ('Z:\\Projects\\UteBot\\icons.qrc', '.'), ('Z:\\Projects\\UteBot\\inteface_W7.ui', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main_W7',
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
    icon=['Z:\\Projects\\UteBot\\icon.ico'],
)
