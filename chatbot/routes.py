# chatbot/routes.py
from flask import Blueprint, request, jsonify, session
import requests
from datetime import datetime
import re

from chatbot.config import nlp_fr, gemini_model
from chatbot.nlp_utils import is_weather_query, extract_city, is_edt_query, is_qcm_query
from chatbot.date_utils import extract_forecast_datetime_str
from chatbot.weather_service import get_weather
from chatbot.edt_service import extract_edt_datetime, normalize_formation
from chatbot.qcm_service import get_random_question, check_answer
from chatbot.utils import generate_gemini_response

chatbot_bp = Blueprint("chatbot_bp", __name__)


@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot():
    print("[routes] chatbot() appelé")
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")
    print(f"[routes] message utilisateur : {user_message!r}")
    if not user_message:
        print("[routes] erreur : message vide")
        return jsonify({"error": "Veuillez saisir un message."}), 400

    conversation_history = session.get("conversation_history", "")
    conversation_history += f"\nUser: {user_message}"
    print(f"[routes] history mise à jour : {conversation_history}")

    doc = nlp_fr(user_message)
    print(f"[routes] doc NLP : {[(ent.text, ent.label_) for ent in doc.ents]}")

    # QCM en cours ?
    if session.get("qcm"):
        print("[routes] session QCM détectée")
        # 1) On tente d’abord de capturer "option N" (ignorer la casse, les apostrophes…)
        m = re.search(r"option\s*(?:n°\s*)?['’]?\s*(\d+)", user_message, re.IGNORECASE)

        # 2) Si ça ne matche pas, on regarde s'il y a un chiffre tout seul
        if not m:
            m = re.search(r"\b(\d+)\b", user_message)
        if m:
            choice = int(m.group(1))
            print(f"[routes] réponse QCM détectée : choix={choice}")
            qinfo = session.pop("qcm")
            correct = check_answer(qinfo["domain"], qinfo["id"], choice)

            # stocke dans l'historique QCM
            session.setdefault("qcm_history", []).append(
                {
                    "domain": qinfo["domain"],
                    "question_id": qinfo["id"],
                    "user_choice": choice,
                    "correct": correct,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if correct:
                feedback = "Bravo ! Vous avez réussi."
            else:
                # on récupère la question complète pour afficher la bonne réponse
                # sur la même question d’ID donné
                # on pourrait avoir une fonction get_question_by_id()
                from chatbot.qcm_service import _qcm_data

                # _qcm_data[domain] est la liste de dict chargée au démarrage
                questions = _qcm_data[qinfo["domain"]]
                # on cherche la question correspondante
                q = next(q for q in questions if q["id"] == qinfo["id"])
                bonne_choix = q["choices"][q["answer_index"]]
                feedback = (
                    "Dommage… essaie encore ! "
                    f"La bonne réponse était : « {bonne_choix} »."
                )

            print(f"[routes] QCM feedback direct : {feedback}")
            return jsonify({"response": feedback})

    # Début QCM si mot-clé
    if is_qcm_query(doc):
        print("[routes] détection QCM démarrage")
        txt = user_message.lower()
        if "informatique" in txt:
            domain = "informatique"
        elif "math" in txt:
            domain = "mathématiques"
        else:
            return jsonify(
                {
                    "response": "Sur quel domaine veux-tu un QCM ? Informatique ou Mathématiques ?"
                }
            )
        # on génère la question et on la stocke en session
        q = get_random_question(domain)
        print(f"[routes] question générée : {q}")
        session["qcm"] = {"domain": domain, "id": q["id"]}
        # on renvoie la question + les choix au format uniforme
        return jsonify({"response": q["question"], "choices": q["choices"]})

    # Météo
    if is_weather_query(doc):
        print("[routes] détection météo")
        city = extract_city(doc) or session.get("last_city")
        forecast_datetime_str = extract_forecast_datetime_str(user_message)
        print(f"[routes] city={city}, datetime={forecast_datetime_str}")
        # ... garde le reste inchangé jusqu'à l'appel à get_weather() ...
        if not city:
            clarification = "Je n'ai pas pu détecter la ville. Peux-tu préciser ?"
            print(f"[routes] clarification météo : {clarification}")
            return jsonify({"response": clarification})
        session["last_city"] = city
        weather_res = get_weather(city, forecast_datetime_str)
        print(f"[routes] résultat API météo : {weather_res}")
        if "error" in weather_res:
            bot_response = weather_res["error"]
        else:
            data_dict = {
                "ville": city,
                "moment": forecast_datetime_str or "maintenant",
                "résumé": weather_res["response"],
            }
            print(f"[routes] data_dict météo : {data_dict}")
            bot_response = generate_gemini_response(
                "météo", data_dict, conversation_history
            )
            print(f"[routes] réponse Gemini météo : {bot_response}")

        conversation_history += f"\nBot: {bot_response}"
        session["conversation_history"] = "\n".join(
            conversation_history.strip().split("\n")[-1]
        )
        return jsonify({"response": bot_response})

    # Emploi du temps
    # 4) Emploi du temps
    if is_edt_query(doc):
        print("[routes] détection emploi du temps")
        # Extraction + validation
        date_str, time_str = extract_edt_datetime(user_message)
        formation = normalize_formation(user_message)

        # si on n’a pas tout ce qu’il faut → on clarifie
        if not date_str or not time_str or not formation:
            return jsonify(
                {
                    "response": "Je n’ai pas compris la date, l’heure ou la formation.\n"
                    "Par exemple : “Ai-je cours le 16 mai 2025 à 14h30 pour Master 1 IA ?”"
                }
            )

        # Appel API externe & normalisation
        api_url = (
            f"http://127.0.0.1:8000/api/cours?"
            f"formation={formation}&date={date_str}&heure={time_str}"
        )
        print(f"[routes] appel API EDT : {api_url}")
        # On essaie d'appeler l'API, et on gère les erreurs
        try:
            resp = requests.get(api_url, timeout=5)
            edt_data = resp.json()

            # Normaliser en liste
            cours_raw = edt_data.get("cours")
            if isinstance(cours_raw, dict):
                cours_list = [cours_raw]
            else:
                cours_list = cours_raw or []

            if not cours_list:
                bot_response = "Tu n'as pas cours à ce moment-là."
            else:
                # Construire data_dict + appel Gemini
                cours_str = "\n".join(
                    f"{c['matiere']} (salle {c['salle']})" for c in cours_list
                )
                data_dict = {
                    "formation": formation,
                    "date": date_str,
                    "heure": time_str,
                    "cours": cours_str,
                }
                bot_response = generate_gemini_response(
                    service_name="emploi du temps",
                    data_dict=data_dict,
                    conversation_context=conversation_history,
                )
        except Exception as e:
            print(f"[routes] erreur API EDT: {e}")
            bot_response = "Oups, je n'ai pas pu consulter l'emploi du temps."

        return jsonify({"response": bot_response})

    # 5) ===> Fallback général <===
    print("[routes] fallback général")
    prompt = (
        f"{conversation_history}\n"
        f"Un étudiant a dit : '{user_message}'. "
        "Réponds de manière naturelle et utile."
    )
    response = gemini_model.generate_content(prompt)
    bot_response = (
        response.text if response else "Désolé, je n'ai pas pu générer de réponse."
    )
    return jsonify({"response": bot_response})
