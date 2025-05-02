# app.py
from flask import Flask
from chatbot.routes import chatbot_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# On enregistre toutes les routes du blueprint telles quelles
# (/chatbot, /chatbot/weather, /chatbot/qcm, /chatbot/qcm/answer, etc.)
app.register_blueprint(chatbot_bp)

if __name__ == "__main__":
    # On écoute toutes les interfaces pour que Pepper/NAO ou Chorégraphe
    # puissent joindre ce serveur depuis le réseau.
    app.run(host="0.0.0.0", port=5000, debug=False)
    # On peut aussi mettre debug=True pour le développement, mais pas en production.
