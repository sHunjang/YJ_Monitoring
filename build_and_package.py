"""
배포 패키지 자동 생성 스크립트

실행:
    python build_and_package.py
"""

import shutil
import subprocess
from pathlib import Path

# 프로젝트 설정
APP_NAME = "여주센서모니터링"
VERSION = "1.0.0"
DIST_FOLDER = Path("dist")
PACKAGE_FOLDER = Path(f"dist/{APP_NAME}_v{VERSION}")

def clean_build():
    """이전 빌드 결과 삭제"""
    print("=" * 70)
    print("🗑️  이전 빌드 결과 삭제 중...")
    print("=" * 70)
    
    folders_to_clean = ["build", "dist"]
    for folder in folders_to_clean:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"✓ {folder}/ 삭제 완료")
    
    print()

def build_exe():
    """PyInstaller로 EXE 빌드"""
    print("=" * 70)
    print("🔨 PyInstaller 빌드 시작...")
    print("=" * 70)
    
    result = subprocess.run(
        ["pyinstaller", "yj_sensor.spec"],
        capture_output=False
    )
    
    if result.returncode != 0:
        print("\n❌ 빌드 실패!")
        exit(1)
    
    print("\n✓ 빌드 완료!")
    print()

def create_package():
    """배포 패키지 생성"""
    print("=" * 70)
    print("📦 배포 패키지 생성 중...")
    print("=" * 70)
    
    # 패키지 폴더 생성
    PACKAGE_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # EXE 파일 복사
    exe_file = DIST_FOLDER / f"{APP_NAME}.exe"
    if exe_file.exists():
        shutil.copy(exe_file, PACKAGE_FOLDER)
        print(f"✓ {APP_NAME}.exe 복사 완료")
    else:
        print(f"❌ {APP_NAME}.exe를 찾을 수 없습니다!")
        exit(1)
    
    # .env 파일 복사
    if Path(".env").exists():
        shutil.copy(".env", PACKAGE_FOLDER)
        print("✓ .env 복사 완료")
    
    # config 폴더 복사
    if Path("config").exists():
        shutil.copytree("config", PACKAGE_FOLDER / "config", dirs_exist_ok=True)
        print("✓ config/ 복사 완료")
    
    # logs 폴더 생성
    (PACKAGE_FOLDER / "logs").mkdir(exist_ok=True)
    print("✓ logs/ 폴더 생성 완료")
    
    # README.txt 생성
    readme_content = f"""
{'=' * 70}
{APP_NAME} v{VERSION}
{'=' * 70}

[실행 방법]
1. {APP_NAME}.exe를 더블클릭하여 실행
2. GUI가 자동으로 실행되며, 백그라운드에서 데이터 수집이 시작됩니다.

[콘솔 모드 실행]
명령 프롬프트에서 다음과 같이 실행:
    {APP_NAME}.exe --console

[필수 사항]
1. PostgreSQL 데이터베이스가 실행 중이어야 합니다.
2. .env 파일의 DB 설정이 올바른지 확인하세요.
3. config/ 폴더의 설정 파일을 확인하세요.

[데이터베이스 초기화]
처음 실행 시 데이터베이스 테이블을 생성해야 합니다:
    psql -U postgres -d sensor_yeoju -f sql/init.sql

[설정 파일]
- .env: 데이터베이스 및 시스템 설정
- config/box_ips.json: 히트펌프 및 지중배관 IP 설정
- config/power_meter_config.json: 전력량계 설정

[로그 파일]
- logs/app.log: 애플리케이션 로그

[문의]
SoluWins (솔루윈스)
{'=' * 70}
"""
    
    with open(PACKAGE_FOLDER / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✓ README.txt 생성 완료")
    
    print()
    print("=" * 70)
    print(f"✅ 배포 패키지 생성 완료!")
    print(f"📂 위치: {PACKAGE_FOLDER.resolve()}")
    print("=" * 70)

def main():
    """메인 함수"""
    print("\n" + "=" * 70)
    print(f"🚀 {APP_NAME} v{VERSION} 배포 패키지 빌드")
    print("=" * 70)
    print()
    
    # 1. 이전 빌드 삭제
    clean_build()
    
    # 2. EXE 빌드
    build_exe()
    
    # 3. 배포 패키지 생성
    create_package()
    
    print("\n✨ 모든 작업이 완료되었습니다!")
    print(f"\n배포 패키지를 압축하여 배포하세요:")
    print(f"  → {PACKAGE_FOLDER.resolve()}")

if __name__ == "__main__":
    main()
