import json
import os
import re
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
URL = "https://puppet-minsk.by/afisha"
STATE_FILE = "seen_january.json"

IGNORE_TITLES = {
    "Волшебное путешествие",
    "За снежной королевой",
    "Умная собачка Соня",
    # "Морозко",
}


def send_telegram(text: str):
    api_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(api_url, json=payload, timeout=15)
    resp.raise_for_status()


def load_seen() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(items: set):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(items)), f, ensure_ascii=False, indent=2)


def parse_january_events() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(URL, headers=headers, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    lines = [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]

    events = []
    date_pattern = re.compile(r"^\d{1,2}\s+Января,\s+[А-Яа-я]{2}$")
    time_pattern = re.compile(r"^\d{2}:\d{2}$")

    i = 0
    while i < len(lines) - 2:
        if date_pattern.match(lines[i]) and time_pattern.match(lines[i + 1]):
            date_str = lines[i]
            time_str = lines[i + 1]
            title = lines[i + 2]
            event_id = f"{date_str} | {time_str} | {title}"
            events.append({
                "id": event_id,
                "date": date_str,
                "time": time_str,
                "title": title,
            })
            i += 3
        else:
            i += 1

    return events


def check_updates():
    seen = load_seen()
    events = parse_january_events()

    new_events = []
    for ev in events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            if ev["title"] not in IGNORE_TITLES:
                new_events.append(ev)

    save_seen(seen)

    if new_events:
        lines = ["🎭 <b>Новые спектакли на январь в Театре кукол!</b>\n"]
        for ev in new_events:
            lines.append(f"• <b>{ev['title']}</b> — {ev['date']} в {ev['time']}")
        lines.append(f"\n🔗 <a href='{URL}'>Перейти к покупке билетов</a>")

        send_telegram("\n".join(lines))
        print(f"Отправлено уведомление о {len(new_events)} новых событиях.")
    else:
        print("Новых постановок на январь пока нет.")


if __name__ == "__main__":
    check_updates()
