# -*- mode: python ; coding: utf-8 -*-
"""
여주 센서 모니터링 시스템 PyInstaller 빌드 스펙 파일

사용법:
    pyinstaller YJ_Sensor.spec

빌드 후:
    1. dist/여주센서모니터링/ 폴더 생성됨
    2. .env 파일을 dist/여주센서모니터링/에 복사
    3. 여주센서모니터링.exe 실행
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 숨겨진 import 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
hiddenimports = []

# 1. sensors 패키지 (자동 수집)
hiddenimports += collect_submodules('sensors')
hiddenimports += collect_submodules('sensors.power')
hiddenimports += collect_submodules('sensors.box')

# 2. core 패키지
hiddenimports += collect_submodules('core')

# 3. ui 패키지
hiddenimports += collect_submodules('ui')
hiddenimports += collect_submodules('ui.dialogs')
hiddenimports += collect_submodules('ui.widgets')

# 4. services 패키지
hiddenimports += collect_submodules('services')

# 5. 필수 라이브러리
hiddenimports += [
    # Modbus TCP
    'pymodbus.client',
    'pymodbus.client.tcp',
    'pymodbus.exceptions',
    
    # PostgreSQL
    'psycopg2',
    'psycopg2.extensions',
    'psycopg2.extras',
    
    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtCharts',
    
    # PyQtGraph (차트)
    'pyqtgraph',
    'pyqtgraph.graphicsItems',
    'pyqtgraph.Qt',
    
    # Pandas (데이터 처리)
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timedeltas',
    
    # Excel 내보내기
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.styles',
    
    # 환경 변수
    'dotenv',
]

# 6. 모델 파일 명시적 포함
hiddenimports += [
    'sensors.power.models',
    'sensors.box.models',
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 데이터 파일 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
datas = []

# src 폴더 전체 포함
datas.append(('src', 'src'))

# config 폴더
datas.append(('config', 'config'))

# sql 폴더
datas.append(('sql', 'sql'))

# PyQtGraph 데이터 파일 포함 (차트 필수)
try:
    import pyqtgraph
    pg_datas, pg_binaries, pg_hiddenimports = collect_all('pyqtgraph')
    datas += pg_datas
    hiddenimports += pg_hiddenimports
except:
    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tests',
        'matplotlib',
        'PIL',
        'tkinter',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYZ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='여주센서모니터링',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # True: 콘솔 표시 (디버깅용), False: GUI만
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLLECT (onedir 모드)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='여주센서모니터링'
)
