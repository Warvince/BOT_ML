import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

TOKEN_FILE = "config.json"


@app.route("/oauth")
def oauth():
    code = request.args.get("code")

    if not code:
        return "❌ Código não recebido"

    url = "https://api.mercadolivre.com/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)

        if resp.status_code != 200:
            return f"❌ Erro ao gerar token: {resp.text}"

        data = resp.json()

        # validação básica
        if "access_token" not in data:
            return "❌ Token inválido recebido"

        # salvar no arquivo
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token")
            }, f)

        return f"""
        <h2>✅ Token gerado com sucesso</h2>
        <p>Agora seu bot já pode rodar automaticamente.</p>
        """

    except Exception as e:
        return f"❌ Erro interno: {str(e)}"


# rota de teste
@app.route("/")
def home():
    return "API rodando 🚀"


if __name__ == "__main__":
    app.run(debug=True)