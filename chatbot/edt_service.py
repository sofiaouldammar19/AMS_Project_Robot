# chatbot/edt_service.py
import re
from datetime import datetime
import dateparser
import unicodedata


def normalize_formation(phrase):
    """
    On accepte :
      - 'M1 IA', 'Master 1 IA'
      - 'M1 ILSEN', 'Master 1 ILSEN'
      - 'M1 scène' (phonétiquement ILSEN)
    et on renvoie exactement 'M1_IA' ou 'M1_ILSEN'.
    """
    # passe tout en minuscule et supprime les accents
    p = phrase.lower()
    p_nof = unicodedata.normalize("NFD", p)
    p_nof = "".join(ch for ch in p_nof if unicodedata.category(ch) != "Mn")
    # maintenant p_nof contient 'scene' au lieu de 'scène'

    # ILSEN ou scène
    if (
        re.search(r"\bm1[\s_-]*ilsen\b", p_nof)
        or "master 1 ilsen" in p_nof
        or "scene" in p_nof
    ):
        return "M1_ILSEN"

    # M1 IA
    if re.search(r"\bm1[\s_-]*ia\b", p_nof) or "master 1 ia" in p_nof:
        return "M1_IA"

    return None


def normalize_time(text):
    """
    Transforme les occurrences orales d'heures en format 'HhMM' :
    ex. '09 heures', '9 heures 5', '09heures10', '9h5' → '9h00', '9h05', '9h10', '9h05'
    """

    def repl(m):
        hh = m.group(1)
        mm = m.group(2) or "00"
        return f"{int(hh)}h{mm.zfill(2)}"

    pattern = re.compile(r"(\d{1,2})\s*(?:heures?|h)(?:\s*(\d{1,2}))?")
    return pattern.sub(repl, text)


def extract_edt_datetime(user_message):
    user_message_clean = user_message.lower().replace("’", "'")
    print(f"🧪 Phrase brute : {user_message_clean!r}")

    # on enlève les mots-clefs et la ponctuation parasite
    to_remove = [
        r"ai-je",
        r"est-ce que",
        r"j'ai",
        r"est-ce",
        r"cours",
        r"formation",
        r"quel est le nom du",
        r"dis-moi",
        r"tu peux me dire si",
        r"pour m1 ia",
        r"pour master 1 ia",
        r"pour m1 ilsen",
        r"pour master 1 ilsen",
        r"maia",
        r"scène",
        r"scene",
        r"le",
        r"la",
        r"\?",
        r"\.",
    ]
    pattern = re.compile(r"\b(" + "|".join(to_remove) + r")\b")
    nettoyee = pattern.sub("", user_message_clean)
    print(f"🧹 Après suppression mots-clefs & ponctuation : {nettoyee!r}")

    # normalisation des heures
    nettoyee = normalize_time(nettoyee)
    print(f"⏰ Après normalize_time : {nettoyee!r}")

    # 3) on écrase les espaces multiples
    nettoyee = re.sub(r"\s+", " ", nettoyee).strip()
    print(f"🔍 Avant coupure 'pour': {nettoyee!r}")

    # 4) on coupe tout ce qui suit 'pour'
    nettoyee = re.sub(r"\bpour\b.*", "", nettoyee).strip()
    print(f"✂️ Après coupure 'pour': {nettoyee!r}")

    # appel à dateparser
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
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        print(f"✅ Dateparser a extrait : {date_str} {time_str}")
        return date_str, time_str

    print("❌ Échec de dateparser malgré nettoyage.")
    return None, None
