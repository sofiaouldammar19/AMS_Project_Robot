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


def generate_gemini_response(
    city,
    temperature,
    description,
    humidity=None,
    wind_speed=None,
    forecast_datetime=None,
    conversation_context="",
):
    if forecast_datetime:
        time_phrase = get_relative_time_phrase(forecast_datetime)
        print(f"🧪 Phrase relative : {time_phrase}")
        prompt = (
            f"{conversation_context}\n"
            f"Un utilisateur demande la météo à {city} {time_phrase}.\n"
            "Voici les données :\n"
            f"- Température : {temperature} °C\n"
            f"- Humidité : {humidity}%\n"
            f"- Vitesse du vent : {wind_speed} km/h\n"
            f"- Conditions : {description}.\n\n"
            "Ne mets aucun émoji dans ta réponse.\n"
            "Réponds de manière naturelle et engageante."
        )
    else:
        prompt = (
            f"{conversation_context}\n"
            f"Un utilisateur demande la météo à {city}.\n"
            "Voici les données :\n"
            f"- Température : {temperature} °C\n"
            f"- Humidité : {humidity}%\n"
            f"- Vitesse du vent : {wind_speed} km/h\n"
            f"- Conditions : {description}.\n\n"
            "Ne mets aucun émoji dans ta réponse.\n"
            "Réponds de manière naturelle et engageante."
        )
    response = gemini_model.generate_content(prompt)
    return response.text if response else "Désolé, je n'ai pas pu générer de réponse."
