# 서버 → 클라이언트 원격 DB 연동 설정 가이드

## 구조

```
서버 현장 PC (데이터 수집 + 저장)
    ↓ INSERT (원격 DB 저장)
클라이언트 회사 PC (PostgreSQL 서버 — 데이터 받는 쪽)
```

---

## 클라이언트 회사 PC 설정 (데이터 받는 쪽)

### 1. postgresql.conf 수정

파일 위치: `C:\Program Files\PostgreSQL\{버전}\data\postgresql.conf`

```
# 변경 — 외부 접속 허용
listen_addresses = '*'
```

### 2. pg_hba.conf 수정

파일 위치: `C:\Program Files\PostgreSQL\{버전}\data\pg_hba.conf`

파일 맨 아래에 추가:
```
# 서버 현장 PC 공인 IP만 허용 (/32 = 해당 IP 1개만)
host    DB_NAME    postgres    {서버_공인_IP}/32    md5
```

### 3. Windows 방화벽 5432 포트 열기

관리자 권한 PowerShell에서 실행:
```powershell
netsh advfirewall firewall add rule name="PostgreSQL 5432" protocol=TCP dir=in localport=5432 action=allow
```

### 4. 공유기 포트포워딩

| 항목 | 값 |
|------|----|
| 외부 포트 | 5432 |
| 내부 IP | 클라이언트 PC 내부 IP (예: 192.168.x.x) |
| 내부 포트 | 5432 |
| 프로토콜 | TCP |

### 5. DB 및 테이블 생성

```powershell
# psql 접속
psql -U postgres

# DB 생성
CREATE DATABASE DB_NAME;

# 테이블 생성 (init.sql 실행)
\c DB_NAME
\i C:\경로\YJ_sensor\sql\init.sql
```

### 6. PostgreSQL 재시작

```powershell
net stop postgresql-x64-16
net start postgresql-x64-16
```

---

## 서버 현장 PC 설정 (데이터 보내는 쪽)

### 1. .env 설정

```env
DB_REMOTE_ENABLED=true
DB_REMOTE_HOST=[클라이언트 공인 IP]
DB_REMOTE_PORT=5432
DB_REMOTE_NAME=DB_NAME
DB_REMOTE_USER=postgres
DB_REMOTE_PASSWORD=****
```

> 서버 PC는 데이터를 보내는 쪽이므로 방화벽/포트포워딩 설정 불필요

---

## 접속 확인 (서버 PC에서 테스트)

```powershell
psql -h [클라이언트 PC IP 주소] -p 5432 -U postgres -d DB_NAME
```

접속 성공 시 연동 준비 완료

---

## 요약

| 항목 | 서버 PC | 클라이언트 PC |
|------|---------|---------|
| 역할 | 데이터 수집 + 전송 | 데이터 수신 |
| 방화벽 설정 | 불필요 | 5432 포트 열기 |
| 포트포워딩 | 불필요 | 5432 포트 포워딩 |
| `.env` 설정 | DB_REMOTE_* 입력 | 불필요 |
| `pg_hba.conf` | 불필요 | 서버 공인 IP 허용 |

---

## 참고 — IP 주소 확인 방법

- **서버 공인 IP**: 서버 PC에서 https://myip.com 접속
- **클라이언트 공인 IP**: 클라이언트 PC에서 https://myip.com 접속
- **클라이언트 내부 IP**: `ipconfig` 명령어로 확인