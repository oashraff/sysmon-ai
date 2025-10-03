# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['sysmon_ai/cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('sysmon_ai/data/schema.sql', 'sysmon_ai/data'),
        ('config.example.yaml', '.'),
    ],
    hiddenimports=[
        'sklearn.utils._weight_vector',
        'sklearn.neighbors._partition_nodes',
        'sklearn.tree._utils',
        'scipy.special.cython_special',
        'scipy._lib.messagestream',
        'scipy.stats._continuous_distns',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='sysmon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
