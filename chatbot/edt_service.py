# chatbot/edt_service.py
import re
from datetime import datetime
import dateparser


def normalize_formation(phrase):
    if "m1 ilsen" in phrase.lower():
        return "M1_ILSEN"
    return "M1_IA"


def normalize_time(text):
    """
    Transforme les occurrences orales d'heures en format 'HhMM' :
    ex. '09 heures', '9 heures 5', '09heures10', '9h5' → '9h00', '9h05', '9h10', '9h05'
    """

    def repl(m):
        hh = m.group(1)
        mm = m.group(2) or "00"
        return f"{int(hh)}h{mm.zfill(2)}"

    # on teste 'heures' en priorité avant 'h' pour éviter les restes de 'eures'
    pattern = re.compile(r"(\d{1,2})\s*(?:heures?|h)(?:\s*(\d{1,2}))?")
    return pattern.sub(repl, text)


def extract_edt_datetime(user_message):
    user_message_clean = user_message.lower().replace("’", "'")
    print(f"🧪 Phrase nettoyée : {user_message_clean}")

    if "maintenant" in user_message_clean:
        now = datetime.now()
        print("⏱️ 'Maintenant' détecté → Date actuelle utilisée.")
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

    nettoyee = re.sub(
        r"(ai-je|est-ce que|j'ai|est-ce|cours|formation|quel est le nom du|dis-moi|tu peux me dire si|pour m1 ia|pour m1 ilsen|pour la formation m1 ia|pour m1 ilsen|le|la)",
        "",
        user_message_clean,
    )

    # normalisation des heures orales avant parsing
    nettoyee = normalize_time(nettoyee)
    print(f"🧹 Après normalisation des heures : {nettoyee}")

    print(f"🧹 Phrase nettoyée pour parsing : {nettoyee}")

    dt = dateparser.parse(
        nettoyee,
        settings={
            "PREFER_DATES_FROM": "future",
            "DATE_ORDER": "DMY",
            "RELATIVE_BASE": datetime.now(),
        },
        languages=["fr"],
    )

    if dt:
        print(f"🕵️ Dateparser a extrait : {dt}")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    else:
        print("❌ Échec de la détection par dateparser même après nettoyage.")
        return None, None
