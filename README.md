# 🎮 게임 예약 디스코드 봇

시간대별 인원 제한, 웨이팅, 자동 승격을 지원하는 Discord 예약 봇입니다.

---

## 📦 설치

```bash
pip install -r requirements.txt
```

---

## ⚙️ 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 값을 입력하세요.

```env
DISCORD_TOKEN=여기에_봇_토큰_입력
GUILD_ID=서버_ID
ANNOUNCE_CHANNEL_ID=알림_채널_ID
```

| 변수 | 설명 |
|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal에서 발급받은 봇 토큰 |
| `GUILD_ID` | 봇을 사용할 서버 ID |
| `ANNOUNCE_CHANNEL_ID` | 자정 알림을 보낼 채널 ID |

> **ID 확인 방법:** Discord 설정 → 고급 → **개발자 모드** 활성화 후, 서버/채널 우클릭 → **ID 복사**

`bot.py` 내 추가 설정:

| 변수 | 설명 |
|---|---|
| `MAX_PLAYERS` | 시간대 당 최대 인원 (기본 5명) |
| `TIME_SLOTS` | 선택 가능한 시간대 목록 |

---

## ▶️ 실행

```bash
python bot.py
```

---

## 📋 명령어

| 명령어 | 설명 |
|---|---|
| `/예약` | 시간대 선택 드롭다운으로 예약 |
| `/취소 [시간]` | 특정 시간대 예약/웨이팅 취소 |
| `/현황` | 오늘 전체 예약 현황 공개 조회 |
| `/내예약` | 내 예약 내역 확인 (본인만) |

---

## 🔄 동작 방식

```
현재 시각 이후 시간대
  └─ 잔여석 있음 (< 5명)  →  확정 예약
  └─ 마감 (= 5명)         →  웨이팅 자동 전환

현재 시각 이전 시간대
  └─ 무조건 웨이팅

웨이팅 중 확정석 취소 발생
  └─ 웨이팅 1번 자동 확정 승격
  └─ 나머지 웨이팅 순번 재정렬

매일 00:00 KST
  └─ DB 전체 초기화
  └─ 알림 채널에 오픈 메시지 전송
```

---

## 🗄️ DB 구조 (reservations.db)

```sql
id           INTEGER  PK AUTOINCREMENT
user_id      TEXT     Discord 고유 ID
user_name    TEXT     유저 이름 (표시용)
reserve_time TEXT     선택 시간 (예: "20:00")
is_waiting   INTEGER  0=확정, 1=웨이팅
queue_order  INTEGER  웨이팅 순번 (확정은 0)
```

---

## 📁 프로젝트 구조

```
.
├── bot.py
├── .env              # 토큰 등 민감 정보 (Git 제외)
├── .gitignore
├── requirements.txt
└── reservations.db   # 실행 후 자동 생성 (Git 제외)
```