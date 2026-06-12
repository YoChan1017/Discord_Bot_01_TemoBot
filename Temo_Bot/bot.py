import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import asyncio
from datetime import datetime, timedelta
import pytz
import sys
import os
from dotenv import load_dotenv
from aiohttp import web

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
WEB_URL = os.getenv("WEB_URL", "").rstrip("/") 

KST = pytz.timezone("Asia/Seoul")
MAX_PLAYERS = 5                      # 시간대 당 최대 인원

# 선택 가능한 시간대 목록
TIME_SLOTS = [
    "10:00", "11:00", "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00", "18:00", "19:00",
    "20:00", "21:00", "22:00",
]

# ─────────────────────────────────────────
# 날짜 헬퍼
# ─────────────────────────────────────────
def today_str() -> str:
    """오늘 날짜 문자열 반환 (예: '2026-06-10')"""
    return datetime.now(KST).strftime("%Y-%m-%d")

def make_reserve_time(time_slot: str) -> str:
    """날짜+시간 합성 (예: '2026-06-10 20:00')"""
    return f"{today_str()} {time_slot}"

def strip_time(reserve_time: str) -> str:
    """DB 저장값에서 시간만 추출 (예: '2026-06-10 20:00' → '20:00')"""
    return reserve_time.split(" ")[1] if " " in reserve_time else reserve_time

# ─────────────────────────────────────────
# DB 초기화
# ─────────────────────────────────────────
# 1. 경로를 확실한 절대 경로로 변경
DB_PATH = "/app/data/reservations.db"

def init_db():
    # 2. sqlite3.connect를 하기 전에, 폴더가 없으면 무조건 강제로 생성하는 코드 추가!
    os.makedirs("/app/data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT    NOT NULL,
            user_name    TEXT    NOT NULL,
            display_name TEXT    NOT NULL DEFAULT '',
            reserve_time TEXT    NOT NULL,
            is_waiting   INTEGER NOT NULL DEFAULT 0,
            queue_order  INTEGER NOT NULL DEFAULT 0
        )
    """)
    # 기존 DB에 display_name 컬럼이 없으면 추가 (마이그레이션)
    try:
        c.execute("ALTER TABLE reservations ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass  # 이미 존재하면 무시
    conn.commit()
    conn.close()

def reset_db():
    """하루가 지나면 모든 예약 초기화"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reservations")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# 예약 로직 헬퍼
# ─────────────────────────────────────────
def get_slot_info(time_slot: str) -> dict:
    """특정 시간대의 확정/웨이팅 인원 반환 (오늘 날짜 기준)"""
    reserve_time = make_reserve_time(time_slot)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM reservations WHERE reserve_time=? AND is_waiting=0",
        (reserve_time,)
    )
    confirmed = c.fetchone()[0]
    c.execute(
        "SELECT COUNT(*) FROM reservations WHERE reserve_time=? AND is_waiting=1",
        (reserve_time,)
    )
    waiting = c.fetchone()[0]
    conn.close()
    return {"confirmed": confirmed, "waiting": waiting}

def is_past_slot(time_slot: str) -> bool:
    """현재 시각보다 이전 시간대이면 True"""
    now = datetime.now(KST)
    slot_hour = int(time_slot.split(":")[0])
    return now.hour >= slot_hour

def add_reservation(user_id: str, user_name: str, display_name: str, time_slot: str) -> dict:
    """
    예약 추가.
    반환: {"status": "confirmed"|"waiting"|"duplicate", "queue_order": int}
    """
    reserve_time = make_reserve_time(time_slot)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 중복 예약 확인 (오늘 날짜 기준)
    c.execute(
        "SELECT id FROM reservations WHERE user_id=? AND reserve_time=?",
        (user_id, reserve_time)
    )
    if c.fetchone():
        conn.close()
        return {"status": "duplicate", "queue_order": 0}

    info = get_slot_info(time_slot)

    if is_past_slot(time_slot):
        queue_order = info["waiting"] + 1
        c.execute(
            "INSERT INTO reservations (user_id, user_name, display_name, reserve_time, is_waiting, queue_order) VALUES (?,?,?,?,1,?)",
            (user_id, user_name, display_name, reserve_time, queue_order)
        )
        conn.commit()
        conn.close()
        return {"status": "waiting", "queue_order": queue_order}

    if info["confirmed"] < MAX_PLAYERS:
        c.execute(
            "INSERT INTO reservations (user_id, user_name, display_name, reserve_time, is_waiting, queue_order) VALUES (?,?,?,?,0,0)",
            (user_id, user_name, display_name, reserve_time)
        )
        conn.commit()
        conn.close()
        return {"status": "confirmed", "queue_order": 0}

    # 5명 초과 → 웨이팅
    queue_order = info["waiting"] + 1
    c.execute(
        "INSERT INTO reservations (user_id, user_name, display_name, reserve_time, is_waiting, queue_order) VALUES (?,?,?,?,1,?)",
        (user_id, user_name, display_name, reserve_time, queue_order)
    )
    conn.commit()
    conn.close()
    return {"status": "waiting", "queue_order": queue_order}

def cancel_reservation(user_id: str, time_slot: str) -> bool:
    """예약 취소. 웨이팅 순번 재정렬 포함."""
    reserve_time = make_reserve_time(time_slot)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "SELECT id, is_waiting FROM reservations WHERE user_id=? AND reserve_time=?",
        (user_id, reserve_time)
    )
    row = c.fetchone()
    if not row:
        conn.close()
        return False

    rid, was_waiting = row
    c.execute("DELETE FROM reservations WHERE id=?", (rid,))

    # 확정 취소 시 → 웨이팅 1번을 확정으로 승격
    if was_waiting == 0:
        c.execute(
            "SELECT id FROM reservations WHERE reserve_time=? AND is_waiting=1 ORDER BY queue_order ASC LIMIT 1",
            (reserve_time,)
        )
        promote = c.fetchone()
        if promote:
            c.execute(
                "UPDATE reservations SET is_waiting=0, queue_order=0 WHERE id=?",
                (promote[0],)
            )
            c.execute(
                "SELECT id FROM reservations WHERE reserve_time=? AND is_waiting=1 ORDER BY queue_order ASC",
                (reserve_time,)
            )
            remaining = c.fetchall()
            for idx, (wid,) in enumerate(remaining, start=1):
                c.execute("UPDATE reservations SET queue_order=? WHERE id=?", (idx, wid))

    conn.commit()
    conn.close()
    return True

def get_all_reservations() -> list[dict]:
    """오늘 날짜 예약만 반환"""
    today = today_str()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM reservations WHERE reserve_time LIKE ? ORDER BY reserve_time, is_waiting, queue_order",
        (f"{today}%",)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ─────────────────────────────────────────
# Discord UI: 시간 선택 드롭다운
# ─────────────────────────────────────────
class TimeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(TimeSelect())

class TimeSelect(discord.ui.Select):
    def __init__(self):
        now_hour = datetime.now(KST).hour
        options = []
        for slot in TIME_SLOTS:
            h = int(slot.split(":")[0])
            info = get_slot_info(slot)
            label = slot

            if h < now_hour:
                label += "  (마감)"
                emoji = "🔒"
            elif info["confirmed"] >= MAX_PLAYERS:
                label += f"  (웨이팅 {info['waiting']}명)"
                emoji = "⏳"
            else:
                remaining = MAX_PLAYERS - info["confirmed"]
                label += f"  (잔여 {remaining}자리)"
                emoji = "✅"

            options.append(discord.SelectOption(label=label, value=slot, emoji=emoji))

        super().__init__(placeholder="예약할 시간을 선택하세요", options=options)

    async def callback(self, interaction: discord.Interaction):
        time_slot = self.values[0]
        user = interaction.user
        display_name = user.display_name if hasattr(user, "display_name") else str(user)
        result = add_reservation(str(user.id), str(user), display_name, time_slot)

        if result["status"] == "confirmed":
            embed = discord.Embed(
                title="✅ 예약 완료",
                description=f"**{user.display_name}** 님의 **{time_slot}** 예약이 확정되었습니다!",
                color=discord.Color.green()
            )
        elif result["status"] == "waiting":
            embed = discord.Embed(
                title="⏳ 웨이팅 등록",
                description=(
                    f"**{user.display_name}** 님은 **{time_slot}** 웨이팅 "
                    f"**{result['queue_order']}번**으로 등록되었습니다.\n"
                    "앞 순서 취소 시 자동 확정됩니다."
                ),
                color=discord.Color.orange()
            )
        elif result["status"] == "duplicate":
            embed = discord.Embed(
                title="⚠️ 중복 예약",
                description=f"이미 **{time_slot}** 에 예약/웨이팅 중입니다.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(title="❌ 오류", color=discord.Color.red())

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────
# 봇 설정
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ─────────────────────────────────────────
# 00시 자정 알림 + DB 초기화 태스크
# ─────────────────────────────────────────
@tasks.loop(minutes=1)
async def midnight_reset():
    now = datetime.now(KST)
    if now.hour == 0 and now.minute == 0:
        reset_db()
        channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            today = now.strftime("%Y년 %m월 %d일")
            embed = discord.Embed(
                title="🌅 새로운 하루가 시작되었습니다!",
                description=(
                    f"**{today}** 예약이 오픈되었습니다.\n"
                    "`/예약` 명령어로 원하는 시간대를 선택하세요!"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="매일 00:00에 초기화됩니다")
            await channel.send(embed=embed)


# ─────────────────────────────────────────
# 슬래시 커맨드
# ─────────────────────────────────────────
@tree.command(name="예약", description="게임 시간대를 선택하여 예약합니다")
async def reserve_cmd(interaction: discord.Interaction):
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")
    embed = discord.Embed(
        title=f"📅 {today} 예약",
        description="✅ 잔여석 있음  |  ⏳ 웨이팅  |  🔒 마감\n\n원하는 시간대를 선택하세요.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=TimeSelectView(), ephemeral=True)


@tree.command(name="취소", description="예약 또는 웨이팅을 취소합니다")
@app_commands.describe(time_slot="취소할 시간대 (예: 20:00)")
async def cancel_cmd(interaction: discord.Interaction, time_slot: str):
    success = cancel_reservation(str(interaction.user.id), time_slot)
    if success:
        embed = discord.Embed(
            title="🗑️ 예약 취소 완료",
            description=f"**{time_slot}** 예약이 취소되었습니다.",
            color=discord.Color.greyple()
        )
    else:
        embed = discord.Embed(
            title="⚠️ 예약 없음",
            description=f"**{time_slot}** 에 예약 내역이 없습니다.",
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="현황", description="오늘 전체 예약 현황을 확인합니다")
async def status_cmd(interaction: discord.Interaction):
    rows = get_all_reservations()
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")

    embed = discord.Embed(
        title=f"📋 {today} 예약 현황",
        color=discord.Color.gold()
    )

    slot_map: dict[str, dict] = {s: {"confirmed": [], "waiting": []} for s in TIME_SLOTS}
    for r in rows:
        slot = strip_time(r["reserve_time"])
        if slot not in slot_map:
            continue
        nick = r.get("display_name") or r["user_name"]
        if r["is_waiting"] == 0:
            slot_map[slot]["confirmed"].append(nick)
        else:
            slot_map[slot]["waiting"].append((r["queue_order"], nick))

    has_any = False
    for slot in TIME_SLOTS:
        confirmed = slot_map[slot]["confirmed"]
        waiting = sorted(slot_map[slot]["waiting"], key=lambda x: x[0])
        if not confirmed and not waiting:
            continue
        has_any = True
        lines = [f"✅ 확정 ({len(confirmed)}/{MAX_PLAYERS})"]
        for name in confirmed:
            lines.append(f"  • {name}")
        if waiting:
            lines.append(f"⏳ 웨이팅 ({len(waiting)}명)")
            for order, name in waiting:
                lines.append(f"  {order}번 - {name}")
        embed.add_field(name=f"🕐 {slot}", value="\n".join(lines), inline=False)

    if not has_any:
        embed.description = "아직 예약이 없습니다."

    if WEB_URL:
        embed.add_field(
            name="🌐 웹에서 보기",
            value=f"[예약 현황 페이지 열기]({WEB_URL}/status)",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@tree.command(name="내예약", description="내 예약 내역을 확인합니다")
async def my_reservation_cmd(interaction: discord.Interaction):
    today = today_str()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM reservations WHERE user_id=? AND reserve_time LIKE ? ORDER BY reserve_time",
        (str(interaction.user.id), f"{today}%")
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if not rows:
        await interaction.response.send_message("오늘 예약 내역이 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(title="🎮 내 예약 내역", color=discord.Color.purple())
    for r in rows:
        time_only = strip_time(r["reserve_time"])
        status = "✅ 확정" if r["is_waiting"] == 0 else f"⏳ 웨이팅 {r['queue_order']}번"
        embed.add_field(name=f"🕐 {time_only}", value=status, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────
# 봇 시작
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    init_db()
    synced = await tree.sync()
    midnight_reset.start()
    print(f"✅ 봇 온라인: {bot.user} | 서버 커맨드 동기화 완료")
    print(f"sync 결과: {synced}")

    cmds = await tree.fetch_commands(guild=discord.Object(id=GUILD_ID))
    print(f"등록된 커맨드: {[c.name for c in cmds]}")

    print(f"실행 파일 경로: {__file__}")
    print(f"tree 커맨드 수: {len(tree._global_commands)}, {len(tree._guild_commands)}")

# ─────────────────────────────────────────
# 웹 서버 (Health Check + 예약 현황 페이지)
# ─────────────────────────────────────────
async def handle_health(request):
    """GET / → 200 OK (health check용)"""
    return web.Response(text="OK", status=200)


async def handle_status(request):
    """GET /status → 오늘 예약 현황 HTML 페이지"""
    rows = get_all_reservations()
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")

    # 슬롯별 데이터 정리
    slot_map: dict[str, dict] = {s: {"confirmed": [], "waiting": []} for s in TIME_SLOTS}
    for r in rows:
        slot = strip_time(r["reserve_time"])
        if slot not in slot_map:
            continue
        nick = r.get("display_name") or r["user_name"]
        if r["is_waiting"] == 0:
            slot_map[slot]["confirmed"].append(nick)
        else:
            slot_map[slot]["waiting"].append((r["queue_order"], nick))

    # 테이블 행 생성
    table_rows = ""
    for slot in TIME_SLOTS:
        confirmed = slot_map[slot]["confirmed"]
        waiting = sorted(slot_map[slot]["waiting"], key=lambda x: x[0])
        confirmed_str = ", ".join(confirmed) if confirmed else "—"
        waiting_str = " / ".join(f"{o}번 {n}" for o, n in waiting) if waiting else "—"
        full = len(confirmed) >= MAX_PLAYERS
        row_class = "full" if full else ""
        table_rows += f"""
        <tr class="{row_class}">
            <td>{slot}</td>
            <td>{len(confirmed)} / {MAX_PLAYERS}</td>
            <td>{confirmed_str}</td>
            <td>{waiting_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="30">
  <title>Temo Bot - 예약 현황</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background: #2c2f33; color: #dcddde; margin: 0; padding: 24px; }}
    h1   {{ color: #7289da; margin-bottom: 4px; }}
    p.sub {{ color: #72767d; margin-top: 0; font-size: 0.9em; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 16px; }}
    th   {{ background: #7289da; color: #fff; padding: 10px 14px; text-align: left; }}
    td   {{ padding: 9px 14px; border-bottom: 1px solid #40444b; }}
    tr:hover td {{ background: #36393f; }}
    tr.full td  {{ color: #f04747; }}
    .badge {{ display: inline-block; background: #43b581; color: #fff; border-radius: 4px;
              padding: 2px 8px; font-size: 0.78em; margin-left: 6px; }}
  </style>
</head>
<body>
  <h1>🎮 Temo Bot 예약 현황</h1>
  <p class="sub">📅 {today} &nbsp;·&nbsp; 30초마다 자동 갱신</p>
  <table>
    <thead>
      <tr>
        <th>시간</th>
        <th>확정 인원</th>
        <th>확정자</th>
        <th>웨이팅</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html", charset="utf-8")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/status", handle_status)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 웹 서버 시작: http://0.0.0.0:{port}")


# ─────────────────────────────────────────
# 봇 + 웹 서버 동시 실행
# ─────────────────────────────────────────
async def main():
    await start_web_server()
    await bot.start(TOKEN)

asyncio.run(main())