# ==============================================
# 설정 파일 관리 서비스
# ==============================================
"""
JSON 설정 파일 로드/저장 관리

주요 기능:
1. box_ips.json 로드/저장
2. power_meter_config.json 로드/저장
3. 설정 검증
4. 기본 설정 생성
5. IP 및 Slave ID 동적 업데이트

사용 예:
    from services.config_service import ConfigService
    
    service = ConfigService()
    heatpump_ips = service.get_heatpump_ips()
    power_config = service.get_power_meter_config()
    
    # IP 업데이트
    service.update_device_ip('HP_1', '192.168.1.150')
    
    # Slave ID 업데이트
    service.update_device_slave_ids('HP_1', temp1_slave_id=10)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.config import get_config

logger = logging.getLogger(__name__)


class ConfigService:
    """
    설정 파일 관리 서비스
    
    config/ 디렉토리의 JSON 설정 파일을 읽고 쓰는 기능을 제공합니다.
    """
    
    def __init__(self):
        """초기화"""
        config = get_config()
        self.config_dir = config.project_root / 'config'
        
        # 설정 파일 경로
        self.box_ips_file = self.config_dir / 'box_ips.json'
        self.power_meter_file = self.config_dir / 'power_meter_config.json'
        
        # config 디렉토리 생성 (없으면)
        self.config_dir.mkdir(exist_ok=True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 플라스틱 함 IP 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def load_box_ips(self) -> Optional[Dict[str, Any]]:
        """
        플라스틱 함 IP 설정 로드
        
        Returns:
            dict: 설정 딕셔너리 (실패 시 None)
            
        Example:
            >>> service = ConfigService()
            >>> config = service.load_box_ips()
            >>> print(config['heatpump'][0]['ip'])
            '192.168.1.101'
        """
        try:
            if not self.box_ips_file.exists():
                logger.warning(f"설정 파일 없음: {self.box_ips_file}")
                return None
            
            with open(self.box_ips_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"플라스틱 함 IP 설정 로드: {self.box_ips_file}")
            return data
            
        except Exception as e:
            logger.error(f"플라스틱 함 IP 설정 로드 실패: {e}", exc_info=True)
            return None
    
    def save_box_ips(self, data: Dict[str, Any]) -> bool:
        """
        플라스틱 함 IP 설정 저장
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            bool: 저장 성공 시 True
        """
        try:
            # 수정 시간 업데이트
            data['last_updated'] = datetime.now().isoformat()
            
            # JSON 저장
            with open(self.box_ips_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"플라스틱 함 IP 설정 저장: {self.box_ips_file}")
            return True
            
        except Exception as e:
            logger.error(f"플라스틱 함 IP 설정 저장 실패: {e}", exc_info=True)
            return False
    
    def get_heatpump_ips(self) -> List[Dict[str, Any]]:
        """
        히트펌프 IP 목록 조회
        
        Returns:
            list: 히트펌프 설정 리스트
            
        Example:
            >>> service = ConfigService()
            >>> heatpumps = service.get_heatpump_ips()
            >>> for hp in heatpumps:
            >>>     print(hp['device_id'], hp['ip'])
        """
        data = self.load_box_ips()
        if data and 'heatpump' in data:
            return data['heatpump']
        return []
    
    def get_groundpipe_ips(self) -> List[Dict[str, Any]]:
        """
        지중배관 IP 목록 조회
        
        Returns:
            list: 지중배관 설정 리스트
        """
        data = self.load_box_ips()
        if data and 'groundpipe' in data:
            return data['groundpipe']
        return []
    
    def get_device_config(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 장치의 전체 설정 조회 (IP + Slave IDs)
        
        Args:
            device_id: 장치 ID (예: 'HP_1', 'GP_1')
            
        Returns:
            dict: 장치 설정 (IP, port, sensors 포함)
            None: 찾을 수 없음
            
        Example:
            >>> service = ConfigService()
            >>> config = service.get_device_config('HP_1')
            >>> if config:
            >>>     print(config['ip'])
            >>>     print(config['sensors']['temp1_slave_id'])
        """
        data = self.load_box_ips()
        if not data:
            return None
        
        # 히트펌프에서 찾기
        for device in data.get('heatpump', []):
            if device['device_id'] == device_id:
                return device
        
        # 지중배관에서 찾기
        for device in data.get('groundpipe', []):
            if device['device_id'] == device_id:
                return device
        
        logger.warning(f"장치를 찾을 수 없음: {device_id}")
        return None
    
    def update_device_ip(
        self,
        device_id: str,
        new_ip: str,
        new_port: Optional[int] = None
    ) -> bool:
        """
        장치 IP 주소 업데이트
        
        Args:
            device_id: 장치 ID (예: 'HP_1', 'GP_1')
            new_ip: 새 IP 주소
            new_port: 새 포트 (None이면 유지)
            
        Returns:
            bool: 업데이트 성공 시 True
            
        Example:
            >>> service = ConfigService()
            >>> service.update_device_ip('HP_1', '192.168.1.150')
            >>> service.update_device_ip('GP_1', '192.168.1.200', 502)
        """
        data = self.load_box_ips()
        if not data:
            logger.error("설정 파일을 로드할 수 없습니다.")
            return False
        
        updated = False
        
        # 히트펌프에서 찾아서 업데이트
        for device in data.get('heatpump', []):
            if device['device_id'] == device_id:
                old_ip = device['ip']
                device['ip'] = new_ip
                if new_port is not None:
                    device['port'] = new_port
                updated = True
                logger.info(
                    f"[{device_id}] IP 업데이트: {old_ip} → {new_ip}"
                )
                break
        
        # 지중배관에서 찾아서 업데이트
        if not updated:
            for device in data.get('groundpipe', []):
                if device['device_id'] == device_id:
                    old_ip = device['ip']
                    device['ip'] = new_ip
                    if new_port is not None:
                        device['port'] = new_port
                    updated = True
                    logger.info(
                        f"[{device_id}] IP 업데이트: {old_ip} → {new_ip}"
                    )
                    break
        
        if updated:
            return self.save_box_ips(data)
        else:
            logger.error(f"장치를 찾을 수 없음: {device_id}")
            return False
    
    def update_device_slave_ids(
        self,
        device_id: str,
        temp1_slave_id: Optional[int] = None,
        temp2_slave_id: Optional[int] = None,
        flow_slave_id: Optional[int] = None
    ) -> bool:
        """
        장치 Slave ID 업데이트
        
        Args:
            device_id: 장치 ID
            temp1_slave_id: 온도센서 1 Slave ID (None이면 유지)
            temp2_slave_id: 온도센서 2 Slave ID (None이면 유지)
            flow_slave_id: 유량센서 Slave ID (None이면 유지)
            
        Returns:
            bool: 업데이트 성공 시 True
            
        Example:
            >>> service = ConfigService()
            >>> # 온도1만 변경
            >>> service.update_device_slave_ids('HP_1', temp1_slave_id=10)
            >>> # 모든 센서 ID 변경
            >>> service.update_device_slave_ids(
            >>>     'HP_1',
            >>>     temp1_slave_id=10,
            >>>     temp2_slave_id=11,
            >>>     flow_slave_id=12
            >>> )
        """
        data = self.load_box_ips()
        if not data:
            logger.error("설정 파일을 로드할 수 없습니다.")
            return False
        
        updated = False
        
        # 업데이트할 장치 찾기
        target_device = None
        for device in data.get('heatpump', []):
            if device['device_id'] == device_id:
                target_device = device
                break
        
        if not target_device:
            for device in data.get('groundpipe', []):
                if device['device_id'] == device_id:
                    target_device = device
                    break
        
        if target_device:
            # sensors 키가 없으면 생성
            if 'sensors' not in target_device:
                target_device['sensors'] = {}
            
            # Slave ID 업데이트
            if temp1_slave_id is not None:
                target_device['sensors']['temp1_slave_id'] = temp1_slave_id
                logger.info(
                    f"[{device_id}] 온도1 Slave ID 업데이트: {temp1_slave_id}"
                )
                updated = True
            
            if temp2_slave_id is not None:
                target_device['sensors']['temp2_slave_id'] = temp2_slave_id
                logger.info(
                    f"[{device_id}] 온도2 Slave ID 업데이트: {temp2_slave_id}"
                )
                updated = True
            
            if flow_slave_id is not None:
                target_device['sensors']['flow_slave_id'] = flow_slave_id
                logger.info(
                    f"[{device_id}] 유량 Slave ID 업데이트: {flow_slave_id}"
                )
                updated = True
        
        if updated:
            return self.save_box_ips(data)
        else:
            logger.error(f"장치를 찾을 수 없거나 변경사항이 없음: {device_id}")
            return False
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 전력량계 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def load_power_meter_config(self) -> Optional[Dict[str, Any]]:
        """
        전력량계 설정 로드
        
        Returns:
            dict: 설정 딕셔너리 (실패 시 None)
        """
        try:
            if not self.power_meter_file.exists():
                logger.warning(f"설정 파일 없음: {self.power_meter_file}")
                return None
            
            with open(self.power_meter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"전력량계 설정 로드: {self.power_meter_file}")
            return data
            
        except Exception as e:
            logger.error(f"전력량계 설정 로드 실패: {e}", exc_info=True)
            return None
    
    def save_power_meter_config(self, data: Dict[str, Any]) -> bool:
        """
        전력량계 설정 저장
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            bool: 저장 성공 시 True
        """
        try:
            # 수정 시간 업데이트
            data['last_updated'] = datetime.now().isoformat()
            
            # JSON 저장
            with open(self.power_meter_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"전력량계 설정 저장: {self.power_meter_file}")
            return True
            
        except Exception as e:
            logger.error(f"전력량계 설정 저장 실패: {e}", exc_info=True)
            return False
    
    def get_power_meter_config(self) -> Optional[Dict[str, Any]]:
        """
        전력량계 전체 설정 조회
        
        Returns:
            dict: 전력량계 설정
        """
        return self.load_power_meter_config()
    
    def get_power_meter_ip(self) -> str:
        """
        전력량계 IP 주소 조회
        
        Returns:
            str: IP 주소 (기본값: 192.168.1.200)
        """
        data = self.load_power_meter_config()
        if data and 'ip' in data:
            return data['ip']
        return '192.168.1.200'
    
    def get_power_meters(self) -> List[Dict[str, Any]]:
        """
        전력량계 목록 조회
        
        Returns:
            list: 전력량계 설정 리스트
        """
        data = self.load_power_meter_config()
        if data and 'meters' in data:
            return data['meters']
        return []
    
    def update_power_meter_ip(self, new_ip: str, new_port: Optional[int] = None) -> bool:
        """
        전력량계 IP 주소 업데이트
        
        Args:
            new_ip: 새 IP 주소
            new_port: 새 포트 (None이면 유지)
            
        Returns:
            bool: 업데이트 성공 시 True
            
        Example:
            >>> service = ConfigService()
            >>> service.update_power_meter_ip('192.168.1.210')
        """
        data = self.load_power_meter_config()
        if not data:
            logger.error("전력량계 설정 파일을 로드할 수 없습니다.")
            return False
        
        old_ip = data.get('ip', 'N/A')
        data['ip'] = new_ip
        
        if new_port is not None:
            data['port'] = new_port
        
        logger.info(f"전력량계 IP 업데이트: {old_ip} → {new_ip}")
        
        return self.save_power_meter_config(data)
    
    def update_power_meter_slave_id(self, device_id: str, new_slave_id: int) -> bool:
        """
        특정 전력량계의 Slave ID 업데이트
        
        Args:
            device_id: 전력량계 장치 ID (예: 'HP_1', '열풍기_1')
            new_slave_id: 새 Slave ID
            
        Returns:
            bool: 업데이트 성공 시 True
            
        Example:
            >>> service = ConfigService()
            >>> service.update_power_meter_slave_id('HP_1', 20)
        """
        data = self.load_power_meter_config()
        if not data:
            logger.error("전력량계 설정 파일을 로드할 수 없습니다.")
            return False
        
        updated = False
        for meter in data.get('meters', []):
            if meter['device_id'] == device_id:
                old_slave_id = meter.get('slave_id', 'N/A')
                meter['slave_id'] = new_slave_id
                logger.info(
                    f"[{device_id}] 전력량계 Slave ID 업데이트: "
                    f"{old_slave_id} → {new_slave_id}"
                )
                updated = True
                break
        
        if updated:
            return self.save_power_meter_config(data)
        else:
            logger.error(f"전력량계를 찾을 수 없음: {device_id}")
            return False


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """
    설정 서비스 테스트
    
    실행: python src/services/config_service.py
    """
    from core.logging_config import setup_logging
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("설정 서비스 테스트")
    print("=" * 70)
    
    service = ConfigService()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 플라스틱 함 IP 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] 히트펌프 IP 조회")
    heatpump_ips = service.get_heatpump_ips()
    print(f"히트펌프 개수: {len(heatpump_ips)}개")
    for hp in heatpump_ips:
        print(f"  - {hp['device_id']}: {hp['ip']}")
        if 'sensors' in hp:
            sensors = hp['sensors']
            print(f"    Slave IDs: T1={sensors.get('temp1_slave_id')}, "
                  f"T2={sensors.get('temp2_slave_id')}, "
                  f"F={sensors.get('flow_slave_id')}")
    
    print("\n[테스트 2] 지중배관 IP 조회")
    groundpipe_ips = service.get_groundpipe_ips()
    print(f"지중배관 개수: {len(groundpipe_ips)}개")
    for gp in groundpipe_ips[:3]:
        print(f"  - {gp['device_id']}: {gp['ip']}")
    print(f"  ... (나머지 {len(groundpipe_ips) - 3}개)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 특정 장치 설정 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 3] 특정 장치 설정 조회")
    device_config = service.get_device_config('HP_1')
    if device_config:
        print(f"HP_1 설정:")
        print(f"  IP: {device_config['ip']}")
        print(f"  Port: {device_config['port']}")
        if 'sensors' in device_config:
            print(f"  Sensors: {device_config['sensors']}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 전력량계 설정 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 4] 전력량계 설정 조회")
    power_config = service.get_power_meter_config()
    if power_config:
        print(f"전력량계 IP: {power_config['ip']}")
        print(f"전력량계 개수: {len(power_config['meters'])}개")
        for meter in power_config['meters'][:5]:
            print(f"  - {meter['device_id']}: Slave ID {meter['slave_id']}")
        print(f"  ... (나머지 {len(power_config['meters']) - 5}개)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 업데이트 테스트 (주석 처리 - 실제 변경 방지)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 5] IP/Slave ID 업데이트 (테스트 모드 - 실행 안 함)")
    print("  실제 업데이트를 테스트하려면 아래 주석을 해제하세요:")
    print("  # service.update_device_ip('HP_1', '192.168.1.150')")
    print("  # service.update_device_slave_ids('HP_1', temp1_slave_id=10)")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
