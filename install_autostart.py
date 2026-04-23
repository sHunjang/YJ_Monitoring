# ==============================================
# 윈도우 자동 시작 등록 스크립트
# ==============================================
"""
프로그램을 윈도우 시작프로그램에 등록합니다.
작업 스케줄러를 사용하여 PC 부팅 시 자동 실행됩니다.

사용법:
    python install_autostart.py          # 자동 시작 등록
    python install_autostart.py --remove # 자동 시작 해제
    python install_autostart.py --status # 등록 상태 확인
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

TASK_NAME = "YeoJu_Sensor_Monitor"
TASK_DESCRIPTION = "여주 센서 모니터링 시스템 자동 시작"


def get_paths():
    """실행 경로 계산"""
    project_root = Path(__file__).resolve().parent
    main_script  = project_root / 'src' / 'main.py'

    # conda 환경 또는 시스템 Python 자동 감지
    python_exe = Path(sys.executable)

    return project_root, main_script, python_exe


def register_task():
    """작업 스케줄러에 자동 시작 등록"""
    project_root, main_script, python_exe = get_paths()

    if not main_script.exists():
        print(f"✗ 오류: {main_script} 를 찾을 수 없습니다.")
        return False

    # XML 작업 정의
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>{TASK_DESCRIPTION}</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </LogonTrigger>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT1M</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>10</Count>
    </RestartOnFailure>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>{main_script}</Arguments>
      <WorkingDirectory>{project_root}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # XML 파일 저장
    xml_path = project_root / 'autostart_task.xml'
    xml_path.write_text(xml_content, encoding='utf-16')

    # 작업 스케줄러 등록
    try:
        # 기존 작업 제거 후 재등록
        subprocess.run(
            ['schtasks', '/Delete', '/TN', TASK_NAME, '/F'],
            capture_output=True
        )
        result = subprocess.run(
            ['schtasks', '/Create', '/TN', TASK_NAME,
             '/XML', str(xml_path), '/F'],
            capture_output=True, text=True
        )
        xml_path.unlink(missing_ok=True)  # XML 파일 삭제

        if result.returncode == 0:
            print(f"✓ 자동 시작 등록 완료")
            print(f"  작업 이름: {TASK_NAME}")
            print(f"  Python:    {python_exe}")
            print(f"  스크립트:  {main_script}")
            print(f"  트리거:    로그인 후 30초 / 부팅 후 1분")
            print(f"  실패 시:   1분 후 자동 재시작 (최대 10회)")
            return True
        else:
            print(f"✗ 등록 실패: {result.stderr}")
            return False

    except FileNotFoundError:
        print("✗ schtasks 명령을 찾을 수 없습니다. Windows에서 실행하세요.")
        return False


def remove_task():
    """작업 스케줄러에서 자동 시작 해제"""
    try:
        result = subprocess.run(
            ['schtasks', '/Delete', '/TN', TASK_NAME, '/F'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✓ 자동 시작 해제 완료: {TASK_NAME}")
            return True
        else:
            print(f"✗ 해제 실패 (이미 없을 수 있음): {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("✗ schtasks 명령을 찾을 수 없습니다.")
        return False


def check_status():
    """등록 상태 확인"""
    try:
        result = subprocess.run(
            ['schtasks', '/Query', '/TN', TASK_NAME, '/FO', 'LIST'],
            capture_output=True, text=True, encoding='cp949'
        )
        if result.returncode == 0:
            print(f"✓ 자동 시작 등록됨\n")
            print(result.stdout)
        else:
            print("✗ 자동 시작 미등록")
    except FileNotFoundError:
        print("✗ Windows 환경에서만 확인 가능합니다.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='자동 시작 등록 관리')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--remove', action='store_true', help='자동 시작 해제')
    group.add_argument('--status', action='store_true', help='등록 상태 확인')
    args = parser.parse_args()

    print("=" * 60)
    print("여주 센서 모니터링 시스템 — 자동 시작 관리")
    print("=" * 60)

    if args.remove:
        remove_task()
    elif args.status:
        check_status()
    else:
        register_task()
