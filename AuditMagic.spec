# AuditMagic.spec
import os
import sys
import qt_material
import openpyxl

qt_material_path = os.path.dirname(qt_material.__file__)
openpyxl_path = os.path.dirname(openpyxl.__file__)

if sys.platform == "darwin":
    icon_file = os.path.join(SPECPATH, "icon.icns")
elif sys.platform == "win32":
    icon_file = os.path.join(SPECPATH, "icon.ico")
else:
    icon_file = os.path.join(SPECPATH, "icon.png")

# Bundle the platform-appropriate icon as a data file for runtime use
if sys.platform == "darwin":
    _extra_datas = [(os.path.join(SPECPATH, "icon.icns"), ".")]
elif sys.platform == "win32":
    _extra_datas = [(os.path.join(SPECPATH, "icon.ico"), ".")]
else:
    _extra_datas = [(os.path.join(SPECPATH, "icon.png"), ".")]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/ui/forms/MainWindow.ui', 'src/ui/forms'),
        ('alembic.ini', '.'),
        ('alembic', 'alembic'),
        (qt_material_path, 'qt_material'),
        (openpyxl_path, 'openpyxl'),
        *_extra_datas,
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
        'logging.config',
        'logging.handlers',
        'openpyxl',
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
    icon=icon_file,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="AuditMagic.app",
        icon=icon_file,
        bundle_identifier="com.chevit.auditmagic",
    )
