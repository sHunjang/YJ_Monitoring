# ==============================================
# Modbus TCP 연결 관리자 (연결 풀 패턴)
# ==============================================
"""
Modbus RTU over TCP 연결 관리

이 모듈은 Modbus RTU over TCP 연결을 효율적으로 관리합니다.
(Hercules 등 Raw TCP 기반 Modbus 장비와 통신)

주요 기능:
1. 연결 풀 관리 (IP:Port별로 연결 재사용)
2. 자동 재연결
3. 스레드 안전성 (Lock)
4. 싱글톤 패턴
5. Modbus RTU Framer 사용 (CRC 포함)

사용 예:
    manager = ModbusTcpManager.get_instance()
    client = manager.get_client('192.168.0.81', 8899)
    
    with manager.get_lock('192.168.0.81', 8899):
        result = client.read_holding_registers(...)
"""

import logging
import threading
from typing import Dict, Optional
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import ModbusRtuFramer  # RTU Framer (CRC 포함)

from core.config import get_config

logger = logging.getLogger(__name__)


class ModbusTcpManager:
    """
    Modbus RTU over TCP 연결 관리자 (싱글톤)
    
    여러 센서가 같은 IP를 공유할 때 연결을 재사용합니다.
    각 IP:Port별로 하나의 클라이언트만 유지합니다.
    """
    
    _instance = None
    _init_lock = threading.Lock()
    
    def __init__(self):
        """초기화"""
        if ModbusTcpManager._instance is not None:
            raise Exception("싱글톤 클래스입니다. get_instance()를 사용하세요.")
        
        self.config = get_config()
        
        # 연결 풀 {"IP:Port": ModbusTcpClient}
        self.clients: Dict[str, ModbusTcpClient] = {}
        
        # 각 연결별 Lock {"IP:Port": Lock}
        self.locks: Dict[str, threading.Lock] = {}
        
        # 전역 Lock (연결 풀 관리용)
        self._lock = threading.Lock()
        
        # 타임아웃 설정
        self.timeout = self.config.modbus_tcp_timeout
        
        logger.info("=" * 70)
        logger.info("ModbusTcpManager 초기화 (RTU over TCP)")
        logger.info("=" * 70)
        logger.info(f"  타임아웃    : {self.timeout}초")
        logger.info(f"  프로토콜    : Modbus RTU over TCP")
        logger.info("=" * 70)
    
    @classmethod
    def get_instance(cls) -> 'ModbusTcpManager':
        """
        싱글톤 인스턴스 가져오기
        
        Returns:
            ModbusTcpManager: 싱글톤 인스턴스
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_client(self, ip: str, port: int = 502) -> Optional[ModbusTcpClient]:
        """
        Modbus RTU over TCP 클라이언트 가져오기
        
        Args:
            ip: IP 주소
            port: TCP 포트 (기본값: 502)
            
        Returns:
            ModbusTcpClient: 클라이언트 인스턴스
            None: 연결 실패 시
        """
        # 연결 키
        connection_key = f"{ip}:{port}"
        
        with self._lock:
            # 기존 연결 확인
            if connection_key in self.clients:
                client = self.clients[connection_key]
                
                if client.connected:
                    logger.debug(f"[{connection_key}] 기존 연결 재사용")
                    return client
                else:
                    logger.warning(f"[{connection_key}] 연결 끊어짐. 재연결 시도...")
                    try:
                        client.close()
                    except:
                        pass
                    del self.clients[connection_key]
                    if connection_key in self.locks:
                        del self.locks[connection_key]
            
            # 새 연결 생성
            try:
                logger.info(f"[{connection_key}] Modbus RTU over TCP 연결 시도...")
                
                # Modbus RTU over TCP (Hercules와 호환)
                client = ModbusTcpClient(
                    host=ip,
                    port=port,
                    timeout=self.timeout,
                    framer=ModbusRtuFramer  # RTU Framer 사용 (CRC 포함)
                )
                
                if client.connect():
                    self.clients[connection_key] = client
                    self.locks[connection_key] = threading.Lock()
                    logger.info(f"✓ [{connection_key}] Modbus RTU over TCP 연결 성공")
                    return client
                else:
                    logger.error(f"✗ [{connection_key}] Modbus RTU over TCP 연결 실패")
                    return None
                    
            except Exception as e:
                logger.error(f"✗ [{connection_key}] Modbus RTU over TCP 연결 오류: {e}", exc_info=True)
                return None
    
    def get_lock(self, ip: str, port: int = 502) -> threading.Lock:
        """
        특정 연결의 Lock 가져오기
        
        Args:
            ip: IP 주소
            port: TCP 포트
            
        Returns:
            threading.Lock: Lock 객체
        """
        connection_key = f"{ip}:{port}"
        
        with self._lock:
            if connection_key not in self.locks:
                self.locks[connection_key] = threading.Lock()
            return self.locks[connection_key]
    
    def is_connected(self, ip: str, port: int = 502) -> bool:
        """
        연결 상태 확인
        
        Args:
            ip: IP 주소
            port: TCP 포트
            
        Returns:
            bool: 연결되어 있으면 True
        """
        connection_key = f"{ip}:{port}"
        
        with self._lock:
            if connection_key in self.clients:
                return self.clients[connection_key].connected
            return False
    
    def close_all(self):
        """모든 연결 종료"""
        with self._lock:
            logger.info("모든 Modbus RTU over TCP 연결 종료 중...")
            
            for connection_key, client in self.clients.items():
                try:
                    client.close()
                    logger.debug(f"[{connection_key}] 연결 종료")
                except Exception as e:
                    logger.error(f"[{connection_key}] 연결 종료 오류: {e}")
            
            self.clients.clear()
            self.locks.clear()
            
            logger.info("✓ 모든 Modbus RTU over TCP 연결 종료 완료")
    
    def __del__(self):
        """소멸자"""
        self.close_all()
