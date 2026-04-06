# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['photon_descent.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/title_ambient.mp3', 'assets'),
        ('assets/light_phase.mp3', 'assets'),
        ('assets/gravity_phase.mp3', 'assets'),
        ('assets/hyper_phase.mp3', 'assets'),
        ('assets/mirror_phase.mp3', 'assets'),
    ],
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
    name='PhotonDescent',
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
    icon=['assets/game.ico'],
)
