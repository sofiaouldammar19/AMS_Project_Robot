# chatbot/qcm_service.py
import os
import json
import random

# Charge les fichiers JSON au démarrage
BASE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'data', 'qcm'))
_PATHS = {
    "informatique": os.path.join(BASE_DIR, "qcm_informatique.json"),
    "mathématiques": os.path.join(BASE_DIR, "qcm_math.json"),
}

_qcm_data = {}
for domain, path in _PATHS.items():
    with open(path, encoding="utf-8") as f:
        _qcm_data[domain] = json.load(f)


def get_random_question(domain):
    """Renvoie un dict {id, question, choices} pour un domaine donné."""
    # Normalisation simple du domaine
    domain = "mathématiques" if domain.lower().startswith("math") else "informatique"
    questions = _qcm_data.get(domain, [])
    q = random.choice(questions)
    return {
        "id": q["id"],
        "question": q["question"],
        "choices": q["choices"],
    }


def check_answer(domain, question_id, user_choice):
    """Retourne True si user_choice == answer_index, sinon False."""
    domain = "mathématiques" if domain.lower().startswith("math") else "informatique"
    questions = _qcm_data.get(domain, [])
    for q in questions:
        if q["id"] == question_id:
            return q["answer_index"] == user_choice
    return False
