# AuditMagic.spec
import os
import qt_material

qt_material_path = os.path.dirname(qt_material.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui/MainWindow.ui', 'ui'),
        ('alembic.ini', '.'),
        ('alembic', 'alembic'),
        (qt_material_path, 'qt_material'),
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
    ],
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
    name='AuditMagic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # windowed mode, no console
    disable_windowed_traceback=False,
    icon='icon.ico',
)
