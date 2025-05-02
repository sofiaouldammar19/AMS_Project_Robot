# chatbot/date_utils.py
import re
from datetime import datetime, timedelta
import dateparser


def fallback_parse_date(text):
    now = datetime.now()
    base_date = now
    text = text.lower()

    if "demain" in text:
        base_date = now + timedelta(days=1)
    elif "après-demain" in text:
        base_date = now + timedelta(days=2)
    elif "aujourd’hui" in text or "aujourd'hui" in text:
        base_date = now
    elif "hier" in text:
        base_date = now - timedelta(days=1)
    elif "ce soir" in text:
        base_date = now.replace(hour=20, minute=0)
    elif "ce matin" in text:
        base_date = now.replace(hour=8, minute=0)
    elif "cet après-midi" in text or "après-midi" in text:
        base_date = now.replace(hour=15, minute=0)
    elif "cette nuit" in text:
        base_date = now.replace(hour=23, minute=0)

    time_match = re.search(r"(?:à|vers)?\s*(\d{1,2})[hH:](\d{1,2})?", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        base_date = base_date.replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        print(f"⏱️ Heure détectée : {hour}:{minute:02d}")

    match_relative = re.search(r"dans (\d+)\s*(minute|heures?|jours?)", text)
    if match_relative:
        amount = int(match_relative.group(1))
        unit = match_relative.group(2)
        if "minute" in unit:
            base_date = now + timedelta(minutes=amount)
        elif "heure" in unit:
            base_date = now + timedelta(hours=amount)
        elif "jour" in unit:
            base_date = now + timedelta(days=amount)
        print(f"⏳ Délai relatif détecté : dans {amount} {unit}")

    return base_date


def extract_forecast_datetime_str(user_message):
    print(f"🧪 Phrase météo analysée : {user_message}")

    if "week-end" in user_message.lower() or "weekend" in user_message.lower():
        today = datetime.now()
        saturday = today + timedelta((5 - today.weekday()) % 7)
        user_message += f" {saturday.strftime('%d %B %Y')}"

    dt = dateparser.parse(user_message, settings={
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'DMY'
    }, languages=['fr'])

    if not dt:
        print("⚠️ dateparser a échoué. Tentative avec fallback personnalisé.")
        dt = fallback_parse_date(user_message)

    print(f"🧪 datetime extrait de la phrase météo : {dt}")
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return None
