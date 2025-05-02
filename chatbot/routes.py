# chatbot/routes.py
from flask import Blueprint, json, request, jsonify, session, current_app
import requests
from datetime import datetime
import re
from chatbot.config import nlp_fr, gemini_model
from chatbot.nlp_utils import is_weather_query, extract_city, is_edt_query, is_qcm_query
from chatbot.date_utils import extract_forecast_datetime_str
from chatbot.weather_service import get_weather
from chatbot.edt_service import extract_edt_datetime, normalize_formation
from chatbot.qcm_service import get_random_question, check_answer


# Créez un Blueprint pour le chatbot
chatbot_bp = Blueprint("chatbot_bp", __name__)


@chatbot_bp.route("/chatbot/qcm", methods=["POST"])
def start_qcm():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "").lower()
    if domain not in ("informatique", "mathematiques"):
        return jsonify(
            {
                "response": "Sur quel domaine veux-tu un QCM ? Informatique ou Mathématiques ?"
            }
        )

    q = get_random_question(domain)
    session["qcm"] = {"domain": domain, "id": q["id"]}
    return jsonify({"response": q["question"], "choices": q["choices"]})


@chatbot_bp.route("/chatbot/qcm/answer", methods=["POST"])
def answer_qcm():
    data = request.get_json() or {}
    user_choice = data.get("choice_index")
    qinfo = session.get("qcm")
    if qinfo is None:
        return jsonify({"error": "Aucun QCM en cours"}), 400

    correct = check_answer(qinfo["domain"], qinfo["id"], user_choice)
    # enregistrement historique
    hist = session.setdefault("qcm_history", [])
    hist.append(
        {
            "domain": qinfo["domain"],
            "question_id": qinfo["id"],
            "user_choice": user_choice,
            "correct": correct,
            "timestamp": datetime.now().isoformat(),
        }
    )
    session.pop("qcm")

    if correct:
        return jsonify({"result": "correct", "message": "Bravo ! 🎉"})
    else:
        return jsonify({"result": "wrong", "message": "Dommage… essaie encore !"})


@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")
    if not user_message:
        return jsonify({"error": "Veuillez saisir un message."}), 400

    conversation_history = session.get("conversation_history", "")
    conversation_history += f"\nUser: {user_message}"

    doc = nlp_fr(user_message)

    # 1) Si on attend une réponse QCM dans cette session
    if session.get("qcm"):
        m = re.search(r"(\d+)", user_message)
        if m:
            choice = int(m.group(1))
            # relay via notre endpoint interne
            resp = check_answer(session["qcm"]["domain"], session["qcm"]["id"], choice)
            # on peut réutiliser logic de answer_qcm(), mais ici inline
            session.setdefault("qcm_history", []).append(
                {
                    "domain": session["qcm"]["domain"],
                    "question_id": session["qcm"]["id"],
                    "user_choice": choice,
                    "correct": resp,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            session.pop("qcm")
            text = "Bravo ! 🎉" if resp else "Dommage… essaie encore !"
            return jsonify({"response": text})

        # 2) Détection QCM
        if is_qcm_query(doc):
            txt = user_message.lower()
            if "informatique" in txt:
                domain = "informatique"
            elif "math" in txt:
                domain = "mathematiques"
            else:
                return jsonify(
                    {
                        "response": "Sur quel domaine veux-tu un QCM ? Informatique ou Mathématiques ?"
                    }
                )

            # Génère et stocke la question
            q = get_random_question(domain)
            session["qcm"] = {"domain": domain, "id": q["id"]}

            # Renvoie au format {response, choices}
            return jsonify({"response": q["question"], "choices": q["choices"]})

    if is_weather_query(doc):
        city = extract_city(doc) or session.get("last_city")
        forecast_datetime_str = extract_forecast_datetime_str(user_message)

        if forecast_datetime_str:
            try:
                dt = datetime.strptime(forecast_datetime_str, "%Y-%m-%d %H:%M:%S")
                if (dt - datetime.now()).total_seconds() > 5 * 24 * 3600:
                    msg = "Je ne peux pas te donner la météo au-delà de 5 jours. Tu veux une date plus proche ? 😊"
                    conversation_history += f"\nBot: {msg}"
                    session["conversation_history"] = "\n".join(
                        conversation_history.strip().split("\n")[-10:]
                    )
                    return jsonify({"response": msg})
            except ValueError:
                pass

        if city:
            session["last_city"] = city
            weather_response = get_weather(city, forecast_datetime_str)
            reply = weather_response.get("response", weather_response.get("error"))
            conversation_history += f"\nBot: {reply}"
            session["conversation_history"] = "\n".join(
                conversation_history.strip().split("\n")[-10:]
            )
            return jsonify(weather_response)
        else:
            clarification = "Je n'ai pas pu détecter le nom de la ville. Pourriez-vous préciser s'il vous plaît ?"
            conversation_history += f"\nBot: {clarification}"
            session["conversation_history"] = "\n".join(
                conversation_history.strip().split("\n")[-10:]
            )
            return jsonify({"response": clarification})

    elif is_edt_query(doc):
        date_str, time_str = extract_edt_datetime(user_message)
        formation = normalize_formation(user_message)
        api_url = f"http://127.0.0.1:8000/api/cours?formation={formation}&date={date_str}&heure={time_str}"
        print(f"🌐 URL API appelée : {api_url}")

        if not date_str or not time_str:
            clarification = (
                "Je n'ai pas compris la date ou l'heure. Peux-tu reformuler ?"
            )
            conversation_history += f"\nBot: {clarification}"
            session["conversation_history"] = "\n".join(
                conversation_history.strip().split("\n")[-10:]
            )
            return jsonify({"response": clarification})

        try:
            response = requests.get(api_url)
            edt_data = response.json()
            print(f"📤 Données reçues de l'API : {edt_data}")

            if "cours" in edt_data and "matiere" in edt_data["cours"]:
                matiere = edt_data["cours"]["matiere"]
                salle = edt_data["cours"]["salle"]
                prompt = (
                    f"Un étudiant veut connaître son emploi du temps. "
                    f"Le {date_str} à {time_str}, il a un cours de {matiere} en salle {salle}. "
                    "Réponds simplement et naturellement."
                )
                gemini_response = gemini_model.generate_content(prompt)
                bot_response = (
                    gemini_response.text if gemini_response else "Voici ton cours."
                )
                print(f"💬 Réponse générée par Gemini : {bot_response}")
            else:
                bot_response = "Tu n'as pas cours à ce moment-là 😊"
                print("ℹ️ Aucun cours trouvé pour ce créneau.")
        except Exception as e:
            print(f"❌ Erreur lors de l’appel API EDT : {e}")
            bot_response = "Oups, je n'ai pas pu consulter l'emploi du temps."

        conversation_history += f"\nBot: {bot_response}"
        session["conversation_history"] = "\n".join(
            conversation_history.strip().split("\n")[-10:]
        )
        return jsonify({"response": bot_response})

    # Fallback général
    prompt = (
        f"{conversation_history}\n"
        f"Un étudiant a dit : '{user_message}'. "
        "Réponds de manière naturelle et utile."
    )
    response = gemini_model.generate_content(prompt)
    response_text = (
        response.text if response else "Désolé, je n'ai pas pu générer de réponse."
    )
    conversation_history += f"\nBot: {response_text}"
    session["conversation_history"] = "\n".join(
        conversation_history.strip().split("\n")[-10:]
    )
    return jsonify({"response": response_text})


@chatbot_bp.route("/chatbot/weather", methods=["POST"])
def chatbot_weather():
    data = request.get_json(silent=True) or {}
    city = data.get("city")
    forecast_datetime_str = data.get("datetime")
    if not city and not forecast_datetime_str:
        return jsonify({"error": "Veuillez fournir un nom de ville ou une date."}), 400

    response_data = get_weather(city, forecast_datetime_str)
    return current_app.response_class(
        response=json.dumps(response_data, ensure_ascii=False),
        status=200,
        mimetype="application/json; charset=utf-8",
    )
