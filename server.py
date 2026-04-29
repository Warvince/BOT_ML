import os
import requests
from flask import Flask, request

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

    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    resp = requests.post(url, data=payload)
    data = resp.json()

    return data  # mostra token pra você copiar