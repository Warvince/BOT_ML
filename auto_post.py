import requests
import schedule
import time
import random
from datetime import datetime
import os
import socket

# força resolver mais estável (cloud fallback)
socket.setdefaulttimeout(10)

os.environ["PYTHONHTTPSVERIFY"] = "0"

try:
    print(socket.gethostbyname("api.mercadolivre.com"))
except Exception as e:
    print("DNS FALHOU:", e)

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

# 🔧 SESSÃO GLOBAL (ROBUSTEZ + PERFORMANCE)
session = requests.Session()

# Retry automático contra falhas de rede / DNS / API instável
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(
    total=7,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)


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
    "gabinete gamer",
    "processador",
    "periféricos gamer",
    "mouse gamer",
    "teclado gamer",
    "mousepad gamer",
    "fonte de alimentação",
    "controle playstation",
    "controle xbox"
]

# 🐛 CORREÇÃO: era 'set()', agora é dict para armazenar timestamp
POSTADOS = {}


# ========= TOKEN =========
def renovar_token():
    """Renova o access_token usando o refresh_token. Retorna True se sucesso."""
    global ACCESS_TOKEN, REFRESH_TOKEN

    if not REFRESH_TOKEN:
        print("⚠️ REFRESH_TOKEN não configurado. É necessário refazer a autorização OAuth.")
        return False

    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    }

    try:
        resp = session.post(url, data=payload, timeout=15)

        if resp.status_code != 200:
            print(f"❌ Erro ao renovar token ({resp.status_code}):", resp.text)
            return False

        data = resp.json()

        ACCESS_TOKEN = data.get("access_token")
        REFRESH_TOKEN = data.get("refresh_token")

        print("🔄 Token renovado com sucesso!")
        print(f"   Novo Access Token: {ACCESS_TOKEN[:25]}...")
        print(f"   Novo Refresh Token: {REFRESH_TOKEN[:25]}...")
        print("⚠️  IMPORTANTE: Atualize o REFRESH_TOKEN no Railway Dashboard com o valor acima!")

        return True

    except Exception as e:
        print("❌ Falha ao renovar token:", e)
        return False


# ========= OFERTAS =========
def buscar_ofertas():
    """Busca ofertas na API do Mercado Livre."""
    global POSTADOS

    if not ACCESS_TOKEN:
        print("❌ ACCESS_TOKEN vazio. Tentando renovar...")
        if not renovar_token():
            return []

    url = "https://api.mercadolibre.com/sites/MLB/search"

    query = random.choice(PALAVRAS_CHAVE)

    params = {
        "q": query,
        "limit": 20,
        "sort": "price_asc",
        "condition": "new"
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = session.get(url, params=params, headers=headers, timeout=15)

        # 🆕 Se deu 401, tenta renovar o token e refaz a requisição
        if response.status_code == 401:
            print("⚠️ Token expirou (401). Renovando automaticamente...")
            if renovar_token():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                response = session.get(url, params=params, headers=headers, timeout=15)
            else:
                print("❌ Não foi possível renovar o token.")
                return []

        if response.status_code != 200:
            print(f"❌ Erro API ({response.status_code}):", response.text)
            return []

        # proteção contra JSON quebrado
        try:
            data = response.json()
        except Exception:
            print("❌ JSON inválido da API")
            return []

        ofertas = []

        for item in data.get("results", []):

            titulo = item.get("title", "")
            preco = item.get("price") or 0
            link = item.get("permalink")
            vendidos = item.get("sold_quantity", 0)

            if not link:
                continue

            if preco < 80 or preco > 5000:
                continue

            if vendidos < 50:
                continue

            agora = time.time()
            if link in POSTADOS:
                if agora - POSTADOS[link] < 3600:
                    continue

            POSTADOS[link] = agora

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
        resp = session.post(url, data=data, timeout=10)

        if resp.status_code != 200:
            print("❌ Erro Telegram:", resp.text)

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


# ========= INICIALIZAÇÃO E AGENDAMENTO =========
print("🤖 Bot PROFISSIONAL iniciando...")

# 🆕 Renova o token imediatamente ao iniciar (evita 401 no primeiro ciclo)
if not ACCESS_TOKEN:
    print("ℹ️ ACCESS_TOKEN não encontrado nas variáveis. Renovando...")
    renovar_token()
else:
    print("ℹ️ ACCESS_TOKEN encontrado. Verificando validade com renovação preventiva...")
    # Opcional: renovar de qualquer forma para garantir token fresco
    renovar_token()

# Agendamentos
schedule.every(5).minutes.do(postar_ofertas)
schedule.every(5).hours.do(renovar_token)  # token dura 6h, renova a cada 5h

print("✅ Bot rodando. Aguardando próximos ciclos...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print("❌ Loop erro:", e)
        time.sleep(5)
