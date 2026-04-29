import requests
import schedule
import time
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ================= CONFIG =================
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_FILE = "config.json"

# validação básica
if not TOKEN_TELEGRAM or not CHAT_ID:
    raise Exception("❌ TOKEN_TELEGRAM ou CHAT_ID não configurados no .env")

# ==========================================


# ========= TOKEN =========
def carregar_token():
    if not os.path.exists(TOKEN_FILE):
        print("❌ config.json não encontrado")
        return None

    try:
        with open(TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("access_token")
    except Exception as e:
        print("❌ Erro ao ler token:", e)
        return None


def renovar_token():
    if not os.path.exists(TOKEN_FILE):
        print("⚠️ Token não encontrado para renovar")
        return

    try:
        with open(TOKEN_FILE) as f:
            data = json.load(f)

        if "refresh_token" not in data:
            print("❌ refresh_token não encontrado")
            return

        url = "https://api.mercadolibre.com/oauth/token"

        payload = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": data["refresh_token"]
        }

        resp = requests.post(url, data=payload, timeout=10)

        if resp.status_code != 200:
            print("❌ Erro ao renovar token:", resp.text)
            return

        novo = resp.json()

        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": novo.get("access_token"),
                "refresh_token": novo.get("refresh_token")
            }, f)

        print("🔄 Token renovado com sucesso")

    except Exception as e:
        print("❌ Falha ao renovar token:", e)


# ========= LINK (PREPARADO PRA AFILIADO FUTURO) =========
def gerar_link(link):
    # futuramente você pode integrar afiliado real aqui
    return link


# ========= OFERTAS =========
def buscar_ofertas():
    ACCESS_TOKEN = carregar_token()

    if not ACCESS_TOKEN:
        return []

    url = "https://api.mercadolibre.com/sites/MLB/search"

    params = {
        "q": "promoção",
        "limit": 10,
        "sort": "price_asc"
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print("❌ Erro na API:", response.text)
            return []

        try:
            data = response.json()
        except:
            print("❌ Resposta inválida da API")
            return []

        ofertas = []

        for item in data.get("results", [])[:3]:
            titulo = item.get("title", "Sem título")
            preco = item.get("price") or 0
            link = item.get("permalink")

            if not link:
                continue

            link_final = gerar_link(link)

            texto = f"""🔥 OFERTA ENCONTRADA

📦 {titulo[:80]}
💰 R$ {float(preco):.2f}

👉 {link_final}
"""
            ofertas.append(texto)

        return ofertas

    except Exception as e:
        print("❌ Erro ao buscar ofertas:", e)
        return []


# ========= TELEGRAM =========
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensagem
    }

    try:
        resp = requests.post(url, data=data, timeout=10)

        if resp.status_code != 200:
            print("❌ Erro ao enviar mensagem:", resp.text)

    except Exception as e:
        print("❌ Falha no Telegram:", e)


# ========= EXECUÇÃO =========
def postar_ofertas():
    print(f"\n[{datetime.now()}] Buscando ofertas...")

    ofertas = buscar_ofertas()

    if not ofertas:
        print("⚠️ Nenhuma oferta encontrada")
        return

    for oferta in ofertas:
        enviar_telegram(oferta)
        time.sleep(2)


# ========= AGENDAMENTO =========
schedule.every(30).minutes.do(postar_ofertas)
schedule.every(5).hours.do(renovar_token)

print("🤖 Bot rodando automaticamente...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print("❌ Erro no loop principal:", e)
        time.sleep(5)