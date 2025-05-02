from fastapi import FastAPI, Query, HTTPException
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()

DB_PATH = r"data/EDT/EDT.db"

FORMATIONS_DISPONIBLES = ["M1_IA", "M1_ILSEN"]

# 🕒 Convertir UTC en heure locale (exemple : UTC+1)


def convertir_utc_en_locale(datetime_str):
    # Les timestamps sont déjà en heure locale
    dt = datetime.fromisoformat(datetime_str)
    return dt.strftime("%Y-%m-%d %H:%M")


def get_cours_actuel(formation: str, date_str: str, heure_str: str):
    """
    Recherche dans la base le cours en cours à une date et heure données pour une formation donnée.
    """
    table_name = f"EDT_{formation}"  # Ex: "EDT_M1_IA"
    heure_recherchee = datetime.strptime(
        f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Vérifier si la table existe avant de faire une requête
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=400, detail="Formation non trouvée dans la base de données.")

    #  Requête SQL pour récupérer les cours du jour
    cursor.execute(f"""
        SELECT matiere, salle, start_time, end_time FROM {table_name}
        WHERE DATE(start_time) = ?
    """, (date_str,))

    for matiere, salle, start_time, end_time in cursor.fetchall():
        #  Conversion des heures UTC → heure locale
        debut_cours = datetime.strptime(
            convertir_utc_en_locale(start_time), "%Y-%m-%d %H:%M")
        fin_cours = datetime.strptime(
            convertir_utc_en_locale(end_time), "%Y-%m-%d %H:%M")

        # Vérifie si l'heure recherchée est entre le début et la fin du cours
        if debut_cours <= heure_recherchee < fin_cours:
            conn.close()
            return {"matiere": matiere, "salle": salle}

    conn.close()
    return {"message": "Aucun cours en cours à cette heure."}


@app.get("/api/cours")
def quel_cours(
    formation: str = Query(...),
    date: str = Query(..., pattern=r"\d{4}-\d{2}-\d{2}"),
    heure: str = Query(..., pattern=r"\d{2}:\d{2}")
):
    print(
        f"🧪 Requête reçue : formation={formation}, date={date}, heure={heure}")
    try:
        cours = get_cours_actuel(formation, date, heure)
        return {
            "formation": formation,
            "date": date,
            "heure": heure,
            "cours": cours
        }
    except Exception as e:
        # affiche le vrai type d'erreur
        print(f"❌ Erreur dans get_cours_actuel : {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
