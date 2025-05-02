import sqlite3
import re
import os
import requests
from datetime import datetime

DOSSIER_FIXE = r"EDT"
FICHIER_DB = os.path.join(DOSSIER_FIXE, "EDT.db")

FORMATIONS = {
    "M1_IA": "https://edt-api.univ-avignon.fr/api/exportAgenda/tdoption/def50200dde742437ee6b863b62efe1bb0bf0b3474879290120f68bcaf0da6fcf69aaf41d5d87621ed966dff0e32f30290833f2c56b5910c7c0ca3dbc7a11a5814477c1eddce6ff9d70a97c8376b5eecb2042bc613d4d2c21aeb544224af",
    "M1_ILSEN": "https://edt-api.univ-avignon.fr/api/exportAgenda/tdoption/def5020023780b2da4564212cd0f63e8d1eaf1325505ac2cbccd7ba4d6895fdfaf7a9f422eaa3c43127d1fa25bbfc683631d4c9582ce3bb36833b100556d9beaca05178696a1d094bd6b339bfd22d5a4a961c11327bd2b7fd3c2d34836262f51fa9a5933d445da5a9e9a29ff7f4bb012172c7d1c985d84f375b49a0b4abd112aba260c4ba1",
}

#  Fonction pour télécharger un fichier .ics


def download_ics(url, filepath):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filepath, "wb") as file:
            file.write(response.content)
        print(f"✅ Fichier {filepath} téléchargé avec succès !")
    else:
        print(f"❌ Erreur lors du téléchargement du fichier {filepath}")


#  Fonction pour parser un fichier .ics et extraire les événements
def parse_ics(ics_content):
    events = []
    event_pattern = re.compile(r"""
        BEGIN:VEVENT.*?
        DTSTART:(.*?)\n.*?
        DTEND:(.*?)\n.*?
        SUMMARY;LANGUAGE=fr:(.*?)\n.*?
        LOCATION;LANGUAGE=fr:(.*?)\n.*?
        DESCRIPTION;LANGUAGE=fr:(.*?)\n.*?
        END:VEVENT
    """, re.DOTALL | re.VERBOSE)

    for match in event_pattern.finditer(ics_content):
        dtstart = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ")
        dtend = datetime.strptime(match.group(2), "%Y%m%dT%H%M%SZ")
        summary = match.group(3).strip()
        location = match.group(4).strip()

        # Nettoyage de la description
        description = match.group(5).strip().replace("\\n", " ")

        # Extraction des champs
        matiere_match = re.search(
            r"Mati[eè]re ?: (.+?)(?:Enseignant|Type|TD|$)", description)
        enseignant_match = re.search(
            r"Enseignant[s]? ?: (.*?)(?:/|$)", description)
        type_match = re.search(r"Type ?: (.*?)(?:<|$)", description)
        td_match = re.search(r"TD ?: (.+?)$", description)

        matiere = matiere_match.group(1).strip() if matiere_match else ""
        enseignant = enseignant_match.group(1).strip().replace(
            "\\,", ",") if enseignant_match else ""
        type_cours = type_match.group(1).strip() if type_match else ""
        groupes = td_match.group(1).strip() if td_match else ""

        events.append((dtstart, dtend, matiere, enseignant,
                      location, type_cours, groupes))

    return events


#  Fonction pour enregistrer les événements dans la base SQLite
def save_to_sqlite(events, db_path, formation):
    table_name = f"EDT_{formation}"  # Ex: EDT_M1_IA, EDT_M1_ILSEN
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    #  Créer une table spécifique à la formation si elle n'existe pas
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            matiere TEXT,
            enseignant TEXT,
            salle TEXT,
            type TEXT,
            groupes TEXT
        )
    ''')

    #  Insérer les événements dans la bonne table
    cur.executemany(f'''
        INSERT INTO {table_name} (start_time, end_time, matiere, enseignant, salle, type, groupes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(e[0].isoformat(), e[1].isoformat(), e[2], e[3], e[4], e[5], e[6]) for e in events])

    conn.commit()
    conn.close()


#  Fonction pour sauvegarder les événements dans un fichier texte
def save_to_txt(events, txt_path):
    with open(txt_path, "w", encoding="utf-8") as file:
        for event in events:
            file.write(f"📅 Début: {event[0]}\n")
            file.write(f"⏳ Fin: {event[1]}\n")
            file.write(f"📖 Matière: {event[2]}\n")
            file.write(f"👨‍🏫 Enseignant(s): {event[3]}\n")
            file.write(f"📍 Lieu: {event[4]}\n")
            file.write(f"📌 Type: {event[5]}\n")
            file.write(f"👥 Groupes: {event[6]}\n")
            file.write("-" * 40 + "\n")
    print(f"📂 Données sauvegardées dans : {txt_path}")


#  Fonction principale pour récupérer et stocker l'emploi du temps d'une formation
def importer_edt(formation):
    if formation not in FORMATIONS:
        print(f"❌ Formation '{formation}' inconnue !")
        return

    url_ics = FORMATIONS[formation]
    fichier_ics = os.path.join(DOSSIER_FIXE, f"EDT_{formation}.ics")
    fichier_txt = os.path.join(DOSSIER_FIXE, f"EDT_{formation}.txt")

    #  Télécharger le fichier .ics
    download_ics(url_ics, fichier_ics)

    #  Vérifier si le fichier a bien été téléchargé
    if not os.path.exists(fichier_ics):
        print(f"❌ Erreur : Le fichier {fichier_ics} n'existe pas.")
        return

    #  Lire et parser le fichier .ics
    with open(fichier_ics, "r", encoding="utf-8") as file:
        ics_data = file.read()

    events = parse_ics(ics_data)

    #  Enregistrer les données dans la base SQLite
    save_to_sqlite(events, FICHIER_DB, formation)

    print(
        f"✅ Données de {formation} importées avec succès dans SQLite ({FICHIER_DB}) !")


#  Importer tous les emplois du temps définis
if __name__ == "__main__":
    for formation in FORMATIONS.keys():
        importer_edt(formation)
