# chatbot/utils.py
from datetime import datetime
from chatbot.config import gemini_model


def get_relative_time_phrase(forecast_datetime):
    now = datetime.now()
    delta = forecast_datetime - now

    if delta.total_seconds() <= 0 or delta.total_seconds() >= 24 * 3600:
        return forecast_datetime.strftime("%A %d %B %Y, %H:%M")

    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"dans {hours} heure{'s' if hours > 1 else ''}"
    else:
        return f"dans {minutes} minute{'s' if minutes > 1 else ''}"


def generate_gemini_response(service_name, data_dict, conversation_context=""):
    print(f"[utils] generate_gemini_response pour service {service_name}")
    print(f"[utils] data_dict : {data_dict}")

    # 1) Cadre et style
    prompt = (
        f"{conversation_context}\n"
        f"Tu es un assistant virtuel pour le service « {service_name} ».\n"
        "Fournis les informations de façon naturelle et engageante.\n\n"
        "N'utilise pas d'émojis. Je t'interdis d'en utiliser\n"
        "Données disponibles :\n"
    )
    # 2) Injection dynamique
    for key, val in data_dict.items():
        prompt += f"- {key} : {val}\n"
    # 3) Contraintes stylistiques
    prompt += (
        "\nN’utilise pas d’émojis.\n"
        "Si une donnée manque, invite l’utilisateur à la préciser.\n"
        "Sois clair, chaleureux et concis."
    )

    # 4) Appel à Gemini
    try:
        resp = gemini_model.generate_content(prompt)
        text = resp.text if resp else None
        print(f"[utils] réponse Gemini brute : {text}")
    except Exception as e:
        print(f"[utils] erreur appel Gemini : {e}")
        text = None

    if not text:
        text = "Désolé, je n'ai pas pu générer de réponse."
    print(f"[utils] réponse finale : {text}")
    return text
