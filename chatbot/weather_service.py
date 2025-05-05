# chatbot/weather_service.py
import requests
from datetime import datetime
from chatbot.config import API_KEY, CURRENT_WEATHER_URL, FORECAST_URL
from chatbot.utils import generate_gemini_response


def get_weather(city, forecast_datetime_str=None):
    if forecast_datetime_str:
        params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "fr"}
        response = requests.get(FORECAST_URL, params=params)
        print("📊 → Utilisation de l’API prévisionnelle")
        print(f"🔍 Ville : {city}")
        print(f"🔍 Requête API : {response.url}")
        print(f"🔍 Statut API : {response.status_code}")
        print(f"🔍 Payload API : {response.json()}")

        if response.status_code != 200:
            return {"error": "Ville introuvable ou requête API échouée."}

        data = response.json()
        try:
            target_dt = datetime.strptime(forecast_datetime_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if (target_dt - now).total_seconds() > 5 * 24 * 3600:
                return {
                    "error": "Désolé, je ne peux pas fournir la météo au-delà de 5 jours. Veux-tu une date plus proche ?"
                }
        except ValueError:
            return {"error": "Format de date invalide. Utilise JJ-MM-AAAA HH:MM:SS."}

        forecast_list = data.get("list", [])
        if not forecast_list:
            return {"error": "Les données de prévision ne sont pas disponibles."}

        closest = min(
            forecast_list,
            key=lambda x: abs(
                datetime.strptime(x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_dt
            ),
        )
        temperature = closest["main"]["temp"]
        description = closest["weather"][0]["description"]
        city_name = data["city"]["name"]
        wind_speed_kmh = round(closest["wind"]["speed"] * 3.6, 1)
        humidity = closest["main"]["humidity"]

        # --- Construction du dictionnaire générique ---
        data_dict = {
            "ville": city_name,
            "moment": forecast_datetime_str,
            "température": f"{temperature} °C",
            "humidité": f"{humidity} %",
            "vent": f"{wind_speed_kmh} km/h",
            "conditions": description,
        }
        print(f"[weather_service] data_dict prévisionnel : {data_dict}")

        # --- Appel unifié à Gemini ---
        chatbot_response = generate_gemini_response("météo", data_dict)
        print(f"🧪 Réponse Gemini (forecast) : {chatbot_response}")
        return {"response": chatbot_response}

    else:
        params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "fr"}
        response = requests.get(CURRENT_WEATHER_URL, params=params)
        print("🌍 → Utilisation de l’API météo actuelle")
        print(f"🔍 Ville : {city}")
        print(f"🔍 Requête API : {response.url}")
        print(f"🔍 Statut API : {response.status_code}")
        print(f"🔍 Payload API : {response.json()}")

        if response.status_code != 200:
            return {"error": "Ville introuvable ou requête API échouée."}

        data = response.json()
        temperature = data["main"]["temp"]
        description = data["weather"][0]["description"]
        city_name = data["name"]
        wind_speed_kmh = round(data["wind"]["speed"] * 3.6, 1)
        humidity = data["main"]["humidity"]

        # --- Construction du dictionnaire générique ---
        data_dict = {
            "ville": city_name,
            "moment": "maintenant",
            "température": f"{temperature} °C",
            "humidité": f"{humidity} %",
            "vent": f"{wind_speed_kmh} km/h",
            "conditions": description,
        }
        print(f"[weather_service] data_dict actuel : {data_dict}")

        # --- Appel unifié à Gemini ---
        chatbot_response = generate_gemini_response("météo", data_dict)
        print(f"🧪 Réponse Gemini (current) : {chatbot_response}")
        return {"response": chatbot_response}
