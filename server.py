from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

@app.route("/")
def home():
    return "API ONLINE 🚀"

@app.route("/oauth")
def oauth():
    code = request.args.get("code")

    if not code:
        return "❌ Sem code"

    try:
        url = "https://api.mercadolibre.com/oauth/token"

        payload = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI
        }

        resp = requests.post(url, data=payload, timeout=10)

        return jsonify(resp.json())

    except Exception as e:
        return f"Erro: {str(e)}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)