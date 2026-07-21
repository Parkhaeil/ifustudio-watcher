"""
이퓨스튜디오 7-8월 예약 자리 모니터.
available 배열에 뭐가 들어오면 디스코드로 알림.
"""
import os
import json
import time
import requests
from datetime import date, timedelta

# ===== 설정 =====
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]  # GitHub Secrets에서 주입
TARGET_MONTHS = [(2026, 7), (2026, 8)]  # 7월, 8월 모니터링
STATE_FILE = "state.json"  # 직전에 알림 보낸 슬롯 기록 (중복 알림 방지)

# 특정 날짜만 노리고 싶으면 여기에 적기. 비워두면 7-8월 전체.
# 예: TARGET_DATES = ["2026-07-15", "2026-08-22"]
TARGET_DATES = []

API_URL = "https://www.ifustudio.kr/booking/get_prod_list.cm"
HEADERS = {
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.ifustudio.kr",
    "referer": "https://www.ifustudio.kr/38",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "accept": "application/json, text/plain, */*",
}


def month_dates(year, month):
    """해당 월의 모든 날짜 (YYYY-MM-DD 문자열) 반환."""
    d = date(year, month, 1)
    out = []
    while d.month == month:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def fetch_day(day_str):
    """하루치 슬롯 정보 가져오기."""
    try:
        r = requests.post(
            API_URL,
            headers=HEADERS,
            data={"start_date": day_str, "end_date": day_str},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[!] {day_str} 조회 실패: {e}")
        return None


def load_state():
    """직전 알림 상태 로드."""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_discord(message):
    """디스코드 웹훅 알림."""
    try:
        r = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        r.raise_for_status()
        print(f"[+] 알림 전송 성공")
    except Exception as e:
        print(f"[!] 알림 전송 실패: {e}")


def main():
    if TARGET_DATES:
        dates_to_check = TARGET_DATES
    else:
        dates_to_check = []
        for year, month in TARGET_MONTHS:
            dates_to_check.extend(month_dates(year, month))

    prev_state = load_state()
    new_state = {}
    new_openings = []  # (날짜, 시간이름) 튜플 리스트

    for day in dates_to_check:
        data = fetch_day(day)
        if not data:
            # 조회 실패 시 직전 상태 유지 (잘못된 알림 방지)
            new_state[day] = prev_state.get(day, [])
            continue

        available = data.get("available", [])
        # 슬롯 식별자 (code 사용 - 시간대마다 고유)
        current_codes = sorted([slot["code"] for slot in available])
        new_state[day] = current_codes

        # 직전에 없던 슬롯이 생긴 경우 = 새로 열린 자리
        prev_codes = set(prev_state.get(day, []))
        for slot in available:
            if slot["code"] not in prev_codes:
                new_openings.append((day, slot["name"]))

        # 사이트에 부담 안 주려고 약간 텀
        time.sleep(0.3)

    # 새로 열린 자리 있으면 알림
    if new_openings:
        lines = ["🐳 **이퓨스튜디오 7-8월 예약 자리 열림!**\n"]
        # 날짜별로 묶기
        by_date = {}
        for day, name in new_openings:
            by_date.setdefault(day, []).append(name)
        for day in sorted(by_date.keys()):
            lines.append(f"**{day}**")
            for name in by_date[day]:
                lines.append(f"  • {name}")
        lines.append("\nhttps://www.ifustudio.kr/26")
        send_discord("\n".join(lines))
    else:
        print(f"[ ] 변동 없음 ({len(dates_to_check)}일 체크)")

    save_state(new_state)


if __name__ == "__main__":
    main()
