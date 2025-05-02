# chatbot/nlp_utils.py
def is_weather_query(doc):
    keywords = {"météo", "température", "prédiction",
                "pluie", "ensoleillé", "neige", "vent"}
    return any(token.text.lower() in keywords for token in doc)


def extract_city(doc):
    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            return ent.text
    return None


def is_edt_query(doc):
    keywords = {"emploi du temps", "cours",
                "planning", "matière", "salle", "horaire"}
    return any(kw in doc.text.lower() for kw in keywords)


def is_qcm_query(doc):
    kws = {"qcm", "quiz", "questionnaire", "choix multiples"}
    return any(kw in doc.text.lower() for kw in kws)
