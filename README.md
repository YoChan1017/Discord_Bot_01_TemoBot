# 🎮 TemoBot — 게임 예약 · 웨이팅 관리 Discord Bot

> **Discord에서 게임 시간대를 예약하고, 정원 초과 시 웨이팅을 자동 관리하는 예약 봇**
>
> Python · discord.py · SQLite · aiohttp · Docker

---

## 📌 프로젝트 소개

**TemoBot**은 Discord 서버에서 게임 시간대를 예약할 수 있도록 만든 **예약 관리 Discord Bot**입니다.

시간대별 최대 인원을 제한하고, 정원이 마감된 경우 자동으로 웨이팅을 등록합니다. 확정 예약이 취소되면 웨이팅 순서에 따라 자동으로 확정 예약으로 승격하며, 매일 자정에 예약 데이터를 초기화합니다.

또한 `feature/addWeb` 브랜치에서는 기존 Discord 기반 예약 시스템에 **웹 예약 현황 페이지를 추가**하여 Discord에 접속하지 않고도 현재 예약 상황을 브라우저에서 확인할 수 있도록 기능을 확장했습니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|---|---|
| 🎮 시간대 예약 | Discord에서 원하는 시간대를 선택하여 예약 |
| 👥 인원 제한 | 시간대별 최대 예약 인원 관리 |
| ⏳ 웨이팅 | 정원 초과 또는 이미 지난 시간대 예약 시 자동 웨이팅 |
| 🔄 자동 승격 | 확정 예약 취소 시 웨이팅 1번을 자동 확정 |
| 🔢 순번 재정렬 | 웨이팅 취소 및 승격 후 대기 순번 자동 정리 |
| 📋 예약 현황 | 전체 시간대의 확정 / 웨이팅 현황 조회 |
| 👤 내 예약 | 사용자의 당일 예약 내역만 개인 메시지로 조회 |
| 🌅 일일 초기화 | 매일 00:00 KST에 예약 데이터 초기화 |
| 🌐 웹 조회 | 웹 브라우저에서 오늘 예약 현황 확인 |
| ❤️ Health Check | 웹 서버 상태 확인용 `/` 엔드포인트 제공 |
| 🐳 Docker | 컨테이너 환경에서 실행할 수 있도록 구성 |

---

## 🏗️ 전체 동작 구조

```text
                         ┌────────────────────┐
                         │      Discord       │
                         │  /예약 /취소 /현황  │
                         │     /내예약        │
                         └─────────┬──────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────┐
│                    TemoBot                         │
│                                                     │
│  Discord Command                                    │
│        ↓                                            │
│  예약 / 취소 / 현황 처리                              │
│        ↓                                            │
│  예약 비즈니스 로직                                   │
│        ↓                                            │
│  SQLite Database                                    │
└───────────────────────┬─────────────────────────────┘
                        │
                        │ feature/addWeb
                        ▼
              ┌───────────────────┐
              │   aiohttp Web     │
              │                   │
              │ GET /             │
              │ GET /status       │
              └─────────┬─────────┘
                        │
                        ▼
                  Web Browser
```

---

## 🔄 예약 처리 로직

### 예약 가능 시간

현재 시각보다 이후의 시간대이고 확정 인원이 정원보다 적다면 바로 예약을 확정합니다.

```text
예약 요청
   ↓
현재 시간 확인
   ↓
┌────────────────────────┐
│ 이후 시간대인가?        │
└───────────┬────────────┘
            │ Yes
            ▼
      확정 인원 확인
            │
     ┌──────┴──────┐
     ▼             ▼
   자리 있음      정원 마감
     │             │
     ▼             ▼
  확정 예약       웨이팅
```

### 지난 시간대

이미 시간이 지난 슬롯은 확정 예약이 아닌 웨이팅으로 등록합니다.

```text
현재 시각 이전 시간대
          ↓
       웨이팅 등록
          ↓
     순번 부여
```

### 웨이팅 자동 승격

확정 예약이 취소되면 가장 먼저 등록된 웨이팅 사용자를 자동으로 확정합니다.

```text
확정 예약 취소
      ↓
웨이팅 1번 조회
      ↓
예약 확정으로 변경
      ↓
남은 웨이팅 순번 재정렬
```

---

## 📋 Discord 명령어

| 명령어 | 설명 |
|---|---|
| `/예약` | 예약 가능한 시간대 목록을 확인하고 예약 |
| `/취소 [시간]` | 해당 시간대의 예약 또는 웨이팅 취소 |
| `/현황` | 오늘 전체 예약 현황 확인 |
| `/내예약` | 본인의 오늘 예약 내역 확인 |

### `/예약`

시간 선택 드롭다운을 통해 원하는 시간대를 선택할 수 있습니다.

각 시간대에는 현재 상태가 표시됩니다.

```text
✅ 잔여석 있음
⏳ 웨이팅
🔒 마감
```

---

## 🌐 웹 예약 현황

`feature/addWeb` 브랜치에서 추가한 기능입니다.

기존 Discord Bot에 `aiohttp` 기반 웹 서버를 함께 실행하도록 확장했습니다.

### Endpoint

| Method | Path | 설명 |
|---|---|---|
| GET | `/` | Health Check |
| GET | `/status` | 오늘 예약 현황 페이지 |

### `/`

서버가 정상적으로 실행되고 있는지 확인할 수 있는 간단한 Health Check 엔드포인트입니다.

```text
GET /
   ↓
200 OK
   ↓
OK
```

### `/status`

오늘의 전체 예약 현황을 웹 브라우저에서 확인할 수 있습니다.

```text
┌─────────────────────────────────────────┐
│         🎮 Temo Bot 예약 현황            │
│                                         │
│ 시간 │ 확정 인원 │ 확정자 │ 웨이팅       │
├─────────────────────────────────────────┤
│ 18:00 │ 3 / 5    │ User A │ —           │
│ 19:00 │ 5 / 5    │ User B │ 1번 User D  │
│ 20:00 │ 2 / 5    │ User C │ —           │
└─────────────────────────────────────────┘
```

페이지는 **30초마다 자동 새로고침**되어 최신 예약 상태를 확인할 수 있도록 구성했습니다.

---

## 🔗 Discord와 웹 기능 연동

웹 기능을 추가하면서 `/현황` 명령어에서도 웹 페이지로 바로 이동할 수 있도록 확장했습니다.

```text
/현황
  ↓
오늘 예약 현황 Embed
  +
🌐 웹에서 보기
  ↓
/status 링크
```

환경 변수 `WEB_URL`에 웹 서버의 주소를 지정하면 Discord 메시지에서 예약 현황 페이지를 바로 열 수 있습니다.

---

## 🌿 브랜치별 개발 내용

### `main`

기본 예약 기능을 구현한 버전입니다.

```text
main
├── Discord 예약
├── 예약 취소
├── 웨이팅
├── 자동 승격
├── 순번 재정렬
├── 일일 DB 초기화
└── 내 예약 조회
```

### `feature/addWeb`

기존 예약 기능에 웹 조회 기능을 추가한 확장 버전입니다.

```text
feature/addWeb
├── main 기능 전체
│
├── 🌐 aiohttp Web Server
│   ├── GET /
│   └── GET /status
│
├── 🔗 /현황 → 웹 페이지 링크
├── 👤 display_name 저장
├── 🗄️ 기존 DB 자동 마이그레이션
└── 🐳 웹 포트 포함 Docker 실행
```

현재 `feature/addWeb`은 `main`을 기반으로 **웹 기능 확장과 관련된 3개의 추가 커밋**이 존재합니다.

---

## 🧩 Web Feature 주요 구현

### 1. aiohttp 기반 웹 서버 추가

기존 Discord Bot 프로세스에서 별도의 웹 서버를 함께 실행하도록 구성했습니다.

```text
Python Process
      │
      ├───────────────┐
      ▼               ▼
Discord Bot       aiohttp
      │               │
      ▼               ▼
 Discord API        HTTP
                      │
                      ▼
                 Web Browser
```

Discord Bot과 웹 서버를 하나의 Python 프로세스에서 함께 실행하기 위해 `asyncio` 기반으로 실행 구조를 구성했습니다.

---

### 2. `/status` 예약 현황 페이지

SQLite에 저장된 당일 예약 데이터를 조회한 후 시간대별로 그룹화하여 HTML 테이블로 구성합니다.

```text
SQLite
  ↓
오늘 날짜 데이터 조회
  ↓
시간대별 분류
  ↓
확정 / 웨이팅 분리
  ↓
HTML 생성
  ↓
HTTP Response
```

---

### 3. `display_name` 추가

기존에는 Discord 사용자 이름만 저장했지만, 웹 및 예약 현황 표시를 위해 **서버 닉네임(`display_name`)을 별도로 저장**하도록 확장했습니다.

```text
user_id
    ├── Discord 고유 식별자
    │
user_name
    ├── Discord 계정 이름
    │
display_name
    └── 서버에서 표시되는 닉네임
```

예약 현황에서는 `display_name`을 우선 사용하고, 값이 없는 경우 기존 `user_name`을 사용하도록 처리했습니다.

---

### 4. 기존 DB 자동 마이그레이션

기존 데이터베이스에 `display_name` 컬럼이 없는 경우 봇 실행 시 컬럼을 자동으로 추가하도록 구성했습니다.

```text
기존 reservations.db
        ↓
display_name 컬럼 확인
        ↓
없음 ─────→ ALTER TABLE
        ↓
컬럼 추가
        ↓
정상 서비스
```

이를 통해 기존 데이터베이스를 삭제하지 않고 새로운 스키마를 적용할 수 있도록 구성했습니다.

---

## 🗄️ 데이터베이스

SQLite를 사용하여 예약 정보를 관리합니다.

### `reservations`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | INTEGER | 예약 고유 번호 |
| `user_id` | TEXT | Discord 사용자 고유 ID |
| `user_name` | TEXT | Discord 계정 이름 |
| `display_name` | TEXT | 서버 닉네임 |
| `reserve_time` | TEXT | 예약 날짜 및 시간 |
| `is_waiting` | INTEGER | 확정 여부 (`0`: 확정, `1`: 웨이팅) |
| `queue_order` | INTEGER | 웨이팅 순번 |

### 예약 상태

```text
is_waiting = 0
→ 확정 예약

is_waiting = 1
→ 웨이팅
```

`queue_order`는 웨이팅 중인 사용자에게만 순번을 부여하며, 확정 예약은 `0`으로 관리합니다.

---

## 🕛 일일 초기화

매일 **00:00 KST**에 예약 데이터를 초기화하고 Discord 알림 채널에 새로운 예약 시작 메시지를 전송합니다.

```text
00:00 KST
    ↓
예약 DB 초기화
    ↓
오늘 날짜 시작
    ↓
Discord 알림 전송
```

이를 통해 하루 단위로 예약 데이터를 관리할 수 있도록 구성했습니다.

---

## 🐳 Docker

Docker 환경에서 실행할 수 있도록 `Dockerfile`을 구성했습니다.

```text
Docker
  ↓
Python 3.11
  ↓
requirements.txt 설치
  ↓
Temo_Bot/bot.py 실행
  ↓
Discord Bot + Web Server
```

웹 서버는 `8080` 포트를 사용하며 컨테이너 내부에 `/app/data` 디렉터리를 생성하여 SQLite DB를 저장하도록 구성했습니다.

---

## ⚙️ 환경 변수

프로젝트 루트의 `.env` 파일에 다음 값을 설정합니다.

```env
DISCORD_TOKEN=여기에_봇_토큰_입력
GUILD_ID=서버_ID
ANNOUNCE_CHANNEL_ID=알림_채널_ID

# feature/addWeb
WEB_URL=http://localhost:8080
PORT=8080
```

| 변수 | 설명 |
|---|---|
| `DISCORD_TOKEN` | Discord Bot Token |
| `GUILD_ID` | Discord 서버 ID |
| `ANNOUNCE_CHANNEL_ID` | 자정 알림을 보낼 채널 ID |
| `WEB_URL` | 웹 예약 현황 페이지의 외부 주소 |
| `PORT` | 웹 서버 포트, 기본값 `8080` |

---

## 📦 설치

```bash
pip install -r requirements.txt
```

---

## ▶️ 실행

### 기본 `main` 버전

```bash
python Temo_Bot/bot.py
```

### `feature/addWeb` 버전

```bash
python Temo_Bot/bot.py
```

봇이 실행되면 Discord Bot과 웹 서버가 함께 시작됩니다.

웹 서버:

```text
http://localhost:8080
```

예약 현황:

```text
http://localhost:8080/status
```

---

## 📁 프로젝트 구조

```text
Discord_Bot_01_TemoBot/
├── Temo_Bot/
│   └── bot.py
│
├── .env
├── .env예시.txt
├── .gitignore
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── plan.txt
└── README.md
```

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| Language | Python 3.11 |
| Discord | discord.py |
| Web | aiohttp |
| Database | SQLite |
| Async | asyncio |
| Environment | python-dotenv |
| Timezone | pytz |
| Deployment | Docker |

---

## 📷 서비스 화면

### 시작 알림
<img width="412" height="155" alt="image" src="https://github.com/user-attachments/assets/2cdbbd08-a53f-4fbd-ac34-d4bbf12c47c7" />

### 명령어 목록
<img width="813" height="266" alt="image" src="https://github.com/user-attachments/assets/f836208c-dafa-494b-a9ad-6d59bc65e2b4" />

### 명령어 - /예약
<img width="483" height="406" alt="image" src="https://github.com/user-attachments/assets/53b0e6d3-c79b-41e2-9fab-e2c7b4c3ec7f" />

### 명령어 - /현황
<img width="331" height="223" alt="image" src="https://github.com/user-attachments/assets/446c2315-5461-4d06-b053-bed318674a4f" />
<br>
<img width="655" height="902" alt="image" src="https://github.com/user-attachments/assets/2a5d9a18-6382-4321-896b-c619c8b0122d" />


### 명령어 - /내예약
<img width="348" height="174" alt="image" src="https://github.com/user-attachments/assets/e129235f-bf63-4db1-9bf7-5ee24e785973" />

### 명령어 - /취소
<img width="345" height="156" alt="image" src="https://github.com/user-attachments/assets/97d2baef-faf2-4908-aee2-665f7046f3f9" />

---

## 📚 프로젝트를 통해 경험한 내용

- Discord Slash Command 기반 Bot 개발
- Discord UI의 Select / Embed 활용
- 시간대별 예약 상태 관리
- 예약 정원 및 웨이팅 비즈니스 로직 구현
- 취소에 따른 자동 승격 및 순번 재정렬
- SQLite 기반 데이터 저장 및 조회
- 기존 DB 스키마를 고려한 간단한 마이그레이션 처리
- `asyncio` 기반 비동기 프로그램 구성
- aiohttp 기반 HTTP 서버 추가
- Discord Bot과 웹 서버의 통합 실행
- Docker 기반 애플리케이션 실행 환경 구성
- Health Check 엔드포인트 구현

---

## 🚨 구현 과정에서 고려한 사항

### 예약 중복 방지

Discord 사용자 ID와 예약 시간을 기준으로 이미 동일한 예약 또는 웨이팅이 존재하는지 확인한 후 중복 등록을 방지합니다.

```text
user_id + reserve_time
        ↓
기존 예약 검색
        ↓
존재 → 중복 예약
없음 → 예약 처리
```

### 웨이팅 순서 관리

웨이팅 사용자가 취소되거나 확정 예약이 취소되어 승격이 발생할 때 남은 사용자의 순번을 다시 계산하여 순서가 유지되도록 처리했습니다.

---

## 🔮 향후 개선 방향

- 예약 정보를 날짜별로 보관하는 구조로 확장
- 관리자 전용 웹 예약 관리 기능 추가
- 웹에서 예약 취소 및 관리 기능 제공
- Discord와 웹의 예약 상태 실시간 동기화
- SQLite에서 PostgreSQL / MySQL 등 서버형 DB로 확장
- 예약 동시성 제어 강화
- 웹 인증 및 접근 권한 추가
- 테스트 코드 작성 및 예약 로직 단위 테스트
- Docker Compose 기반 배포 환경 구성

---

<div align="center">

### 🎮 TemoBot

**Discord Game Reservation & Waiting Management Bot**

Python · Discord · SQLite · aiohttp · Docker

</div>
