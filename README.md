# 여주 센서 모니터링 시스템 v1.1

Modbus TCP 기반 센서 데이터 수집 및 모니터링 시스템

## 📋 시스템 구성

### 센서 타입
- **센서 장치 분전반**
  - 히트펌프용
  - 지중배관용
  - 각 함 구성: 온도센서 2개(ID 1,2) + 유량센서 1개(ID 3)
  - .env 파일을 통해 유동적 설정
  
- **전력량계** (개수 설정 가능)
  - 모두 동일 IP 사용
  - Slave ID로 구분

### 통신 방식
- Modbus TCP/IP (무선)
- 각 플라스틱 함은 개별 IP 주소 사용
- GUI에서 IP 주소 설정 가능

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# 가상환경 생성
conda create -n [가상환경이름] python=3.10 -y

# 가상환경 활성화 (Windows)
conda activate [가상환경이름]

# 패키지 설치
pip install -r requirements.txt
