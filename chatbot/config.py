# chatbot/config.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
import spacy

# Chargement des variables d'environnement
load_dotenv()

# Clés API
API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_WEATHER_KEY = os.getenv("GEMINI_API_WEATHER_KEY")

# Endpoints météo
CURRENT_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

# Configuration Gemini
genai.configure(api_key=GEMINI_API_WEATHER_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite")

# Chargement du modèle spaCy français
nlp_fr = spacy.load("fr_core_news_sm")
