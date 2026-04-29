import requests
import schedule
import time
import random
from datetime import datetime
import os

# ================= CONFIG =================
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    from dotenv import load_dotenv
    load_dotenv()

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

if not TOKEN_TELEGRAM or not CHAT_ID:
    raise Exception("❌ TOKEN_TELEGRAM ou CHAT_ID não configurados")

# ==========================================

# 🔥 PALAVRAS QUE VENDEM
PALAVRAS_CHAVE = [
    "iphone",
    "smartphone samsung",
    "notebook",
    "fone bluetooth",
    "smart tv",
    "caixa de som jbl",
    "monitor gamer",
    "placa de vídeo",
    "ssd",
    "headset gamer",
    "placa mãe",
    "memória ram",
    "smartwatch",
    "webcam",
    "tablet",
    "playstation",
    "xbox",
    "nintendo switch",
    "watercooler",
    "gabinete gamer"
    "processador",
    "periféricos gamer",
    "mouse gamer",
    "teclado gamer",
    "mousepad gamer",
    "fonte de alimentação",
    "controle playstation",
    "controle xbox"
]

# evitar repetição
POSTADOS = set()


# ========= TOKEN =========
def renovar_token():
    global ACCESS_TOKEN, REFRESH_TOKEN

    if not REFRESH_TOKEN:
        print("⚠️ Sem refresh token")
        return

    url = "https://api.mercadolivre.com/oauth/token"

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

        print("🔄 Token renovado")

    except Exception as e:
        print("❌ Falha token:", e)


# ========= OFERTAS =========
def buscar_ofertas():
    global POSTADOS

    if not ACCESS_TOKEN:
        print("❌ Sem ACCESS_TOKEN")
        return []

    url = "https://api.mercadolivre.com/sites/MLB/search"

    query = random.choice(PALAVRAS_CHAVE)

    params = {
        "q": query,
        "limit": 20,
        "sort": "price_asc",
        "condition": "new"
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print("❌ Erro API:", response.text)
            return []

        data = response.json()

        ofertas = []

        for item in data.get("results", []):

            titulo = item.get("title", "")
            preco = item.get("price") or 0
            link = item.get("permalink")
            vendidos = item.get("sold_quantity", 0)

            # 🔥 FILTROS INTELIGENTES
            if not link:
                continue

            if preco < 80 or preco > 5000:
                continue

            if vendidos < 50:
                continue

            if link in POSTADOS:
                continue

            POSTADOS.add(link)

            # 💰 simulação de desconto
            preco_antigo = preco * random.uniform(1.15, 1.35)

            texto = f"""🔥 PROMOÇÃO RELÂMPAGO!

📦 {titulo[:70]}

💰 De: ~R$ {preco_antigo:.2f}~
💸 Por: R$ {preco:.2f}

⚠️ +{vendidos} vendidos | Alta procura!

👉 {link}
"""

            ofertas.append(texto)

            if len(ofertas) >= 3:
                break

        return ofertas

    except Exception as e:
        print("❌ Erro ofertas:", e)
        return []


# ========= TELEGRAM =========
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensagem
    }

    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("❌ Telegram erro:", e)


# ========= EXECUÇÃO =========
def postar_ofertas():
    print(f"\n[{datetime.now()}] Buscando ofertas...")

    ofertas = buscar_ofertas()

    if not ofertas:
        print("⚠️ Nenhuma oferta boa encontrada")
        return

    for oferta in ofertas:
        enviar_telegram(oferta)
        time.sleep(2)


# ========= AGENDAMENTO =========
schedule.every().day.at("09:00").do(postar_ofertas)
schedule.every().day.at("09:30").do(postar_ofertas)
schedule.every().day.at("10:00").do(postar_ofertas)
schedule.every().day.at("10:30").do(postar_ofertas)
schedule.every().day.at("11:00").do(postar_ofertas)
schedule.every().day.at("11:30").do(postar_ofertas)
schedule.every().day.at("12:00").do(postar_ofertas)
schedule.every().day.at("12:30").do(postar_ofertas)
schedule.every().day.at("13:00").do(postar_ofertas)
schedule.every().day.at("13:30").do(postar_ofertas)
schedule.every().day.at("14:00").do(postar_ofertas)
schedule.every().day.at("14:30").do(postar_ofertas)
schedule.every().day.at("15:00").do(postar_ofertas)
schedule.every().day.at("15:30").do(postar_ofertas)
schedule.every().day.at("16:00").do(postar_ofertas)
schedule.every().day.at("16:30").do(postar_ofertas)
schedule.every().day.at("17:00").do(postar_ofertas)
schedule.every().day.at("17:15").do(postar_ofertas)
schedule.every().day.at("17:20").do(postar_ofertas)
schedule.every().day.at("17:30").do(postar_ofertas)
schedule.every().day.at("17:50").do(postar_ofertas)
schedule.every().day.at("18:00").do(postar_ofertas)
schedule.every().day.at("18:20").do(postar_ofertas)
schedule.every().day.at("18:25").do(postar_ofertas)
schedule.every().day.at("18:30").do(postar_ofertas)
schedule.every().day.at("18:35").do(postar_ofertas)
schedule.every().day.at("18:40").do(postar_ofertas)
schedule.every().day.at("18:45").do(postar_ofertas)
schedule.every().day.at("18:50").do(postar_ofertas)
schedule.every().day.at("18:55").do(postar_ofertas)
schedule.every().day.at("19:00").do(postar_ofertas)
schedule.every().day.at("19:30").do(postar_ofertas)
schedule.every().day.at("20:00").do(postar_ofertas)
schedule.every().day.at("20:30").do(postar_ofertas)
schedule.every().day.at("21:00").do(postar_ofertas)

schedule.every(5).hours.do(renovar_token)

print("🤖 Bot PROFISSIONAL rodando...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print("❌ Loop erro:", e)
        time.sleep(5)