# app.py
from flask import Flask, render_template
from chatbot.routes import chatbot_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.register_blueprint(chatbot_bp)


@app.route('/')
def index():
    return render_template('chatbotweather.html')


if __name__ == "__main__":
    app.run(debug=False)
