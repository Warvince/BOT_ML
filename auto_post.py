import requests
import schedule
import time
from datetime import datetime
import os

# carrega .env apenas local (Railway já injeta vars)
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    from dotenv import load_dotenv
    load_dotenv()

# ================= CONFIG =================
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# validações
if not TOKEN_TELEGRAM or not CHAT_ID:
    raise Exception("❌ TOKEN_TELEGRAM ou CHAT_ID não configurados")

if not ACCESS_TOKEN:
    print("⚠️ ACCESS_TOKEN não configurado ainda")

# ==========================================


# ========= TOKEN =========
def renovar_token():
    global ACCESS_TOKEN, REFRESH_TOKEN

    if not REFRESH_TOKEN:
        print("⚠️ REFRESH_TOKEN não configurado")
        return

    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)

        if resp.status_code != 200:
            print("❌ Erro ao renovar token:", resp.text)
            return

        data = resp.json()

        ACCESS_TOKEN = data.get("access_token")
        REFRESH_TOKEN = data.get("refresh_token")

        print("🔄 Token renovado com sucesso")

        # IMPORTANTE: no Railway você precisa atualizar manualmente depois
        print("⚠️ Atualize ACCESS_TOKEN e REFRESH_TOKEN no Railway!")

    except Exception as e:
        print("❌ Falha ao renovar token:", e)


# ========= LINK =========
def gerar_link(link):
    return link  # preparado pra afiliado no futuro


# ========= OFERTAS =========
def buscar_ofertas():
    if not ACCESS_TOKEN:
        print("❌ Sem ACCESS_TOKEN")
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
            print("❌ JSON inválido")
            return []

        ofertas = []

        for item in data.get("results", [])[:3]:
            titulo = item.get("title", "Sem título")
            preco = item.get("price") or 0
            link = item.get("permalink")

            if not link:
                continue

            texto = f"""🔥 OFERTA ENCONTRADA

📦 {titulo[:80]}
💰 R$ {float(preco):.2f}

👉 {gerar_link(link)}
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
            print("❌ Erro Telegram:", resp.text)

    except Exception as e:
        print("❌ Falha Telegram:", e)


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

print("🤖 Bot rodando no Railway...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print("❌ Erro no loop:", e)
        time.sleep(5)