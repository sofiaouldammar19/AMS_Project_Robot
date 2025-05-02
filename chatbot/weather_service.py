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
        print(f"🔍 Requête API : {response.status_code}")
        print(f"🔍 Requête API : {response.json()}")
        if response.status_code == 200:
            data = response.json()
            try:
                target_dt = datetime.strptime(
                    forecast_datetime_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                if (target_dt - now).total_seconds() > 5 * 24 * 3600:
                    return {
                        "error": "Désolé, je ne peux pas fournir la météo au-delà de 5 jours. Veux-tu une prévision pour une date plus proche ? 😊"
                    }
            except ValueError:
                return {"error": "Format de date invalide. Utilisez JJ-MM-AAAA HH:MM:SS."}

            forecast_list = data.get("list", [])
            if not forecast_list:
                return {"error": "Les données de prévision ne sont pas disponibles."}

            closest_forecast = min(
                forecast_list,
                key=lambda x: abs(datetime.strptime(
                    x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_dt)
            )
            temperature = closest_forecast["main"]["temp"]
            description = closest_forecast["weather"][0]["description"]
            city_name = data["city"]["name"]
            wind_speed_kmh = round(closest_forecast["wind"]["speed"] * 3.6, 1)
            humidity = closest_forecast["main"]["humidity"]
            chatbot_response = generate_gemini_response(
                city_name, temperature, description, humidity, wind_speed_kmh, target_dt
            )

            print(f"🧪 Réponse du chatbot : {chatbot_response}")
            return {"response": chatbot_response}
        else:
            return {"error": "Ville introuvable ou requête API échouée."}
    else:
        params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "fr"}
        response = requests.get(CURRENT_WEATHER_URL, params=params)
        print("🌍 → Utilisation de l’API météo actuelle")
        print(f"🔍 Ville : {city}")
        print(f"🔍 Requête API : {response.url}")
        print(f"🔍 Requête API : {response.status_code}")
        print(f"🔍 Requête API : {response.json()}")

        if response.status_code == 200:
            data = response.json()
            temperature = data["main"]["temp"]
            description = data["weather"][0]["description"]
            city_name = data["name"]
            wind_speed_kmh = round(data["wind"]["speed"] * 3.6, 1)
            humidity = data["main"]["humidity"]

            chatbot_response = generate_gemini_response(
                city_name, temperature, description, humidity, wind_speed_kmh
            )
            return {"response": chatbot_response}
        else:
            return {"error": "Ville introuvable ou requête API échouée."}
