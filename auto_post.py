import requests
import schedule
import time
import random
import re
from datetime import datetime
import xml.etree.ElementTree as ET

# ================= CONFIGURAÇÃO =================
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    from dotenv import load_dotenv
    load_dotenv()

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")

# 🔑 LOMADEE API v3
LOMADEE_API_KEY = os.getenv("LOMADEE_API_KEY")  # x-api-key

if not TOKEN_TELEGRAM or not CHAT_ID:
    raise Exception("❌ TOKEN_TELEGRAM ou CHAT_ID não configurados nas variáveis de ambiente")

# ================================================

# 🔥 PALAVRAS-CHAVE PARA BUSCA NA LOMADEE
PALAVRAS_CHAVE = [
    "iphone",
    "smartphone samsung",
    "notebook",
    "fone bluetooth",
    "smart tv",
    "caixa de som",
    "monitor",
    "placa de video",
    "ssd",
    "headset",
    "smartwatch",
    "tablet",
    "playstation",
    "xbox",
    "nintendo switch",
    "gabinete gamer",
    "processador",
    "mouse gamer",
    "teclado gamer",
    "fonte",
]

# 🔥 RSS FEEDS BRASILEIROS (FALLBACK se Lomadee não configurada)
RSS_FEEDS = [
    "https://www.promobit.com.br/rss/",
    "https://gatry.com/rss/",
    "https://www.pelando.com.br/rss",
]

# 🛡️ Controle de duplicatas
POSTADOS = set()

# 💰 Filtros de preço
PRECO_MIN = 10.0
PRECO_MAX = 8000.0

# 🔧 SESSÃO HTTP
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
})

# Rate limit Lomadee: 10 req/min
ULTIMA_REQ_LOMADEE = 0


# ========= FUNÇÕES AUXILIARES =========
def respeitar_rate_limit():
    """Garante intervalo mínimo de 6 segundos entre chamadas Lomadee (10 req/min)."""
    global ULTIMA_REQ_LOMADEE
    agora = time.time()
    tempo_decorrido = agora - ULTIMA_REQ_LOMADEE
    if tempo_decorrido < 6:
        time.sleep(6 - tempo_decorrido)
    ULTIMA_REQ_LOMADEE = time.time()


def extrair_preco(texto):
    """Tenta extrair preço de um texto usando regex."""
    if not texto:
        return None
    padroes = [
        r'R\$\s*([\d\.]+(?:,\d{2})?)',
        r'por\s*R\$\s*([\d\.]+(?:,\d{2})?)',
        r'([\d\.]+(?:,\d{2})?)\s*reais',
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                return float(valor_str)
            except ValueError:
                continue
    return None


def limpar_html(texto):
    """Remove tags HTML básicas."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = texto.replace("&nbsp;", " ").replace("&amp;", "&")
    texto = texto.replace("&lt;", "<").replace("&gt;", ">")
    return texto.strip()


# ========= LOMADEE API v3 =========
def buscar_campaigns_lomadee():
    """Busca campanhas ativas (cupons e ofertas) na Lomadee."""
    if not LOMADEE_API_KEY:
        return []

    url = "https://api.lomadee.com.br/v3/campaigns"
    headers = {"x-api-key": LOMADEE_API_KEY}

    ofertas = []
    try:
        respeitar_rate_limit()
        resp = session.get(url, headers=headers, timeout=20)

        if resp.status_code == 401:
            print("❌ Lomadee API Key inválida. Verifique sua x-api-key.")
            return []
        if resp.status_code == 429:
            print("⚠️ Rate limit atingido na Lomadee. Aguarde...")
            return []
        if resp.status_code != 200:
            print(f"⚠️ Lomadee campaigns retornou {resp.status_code}:", resp.text[:200])
            return []

        data = resp.json()
        campaigns = data.get("data", [])

        for camp in campaigns:
            if camp.get("status") != "active":
                continue

            titulo = camp.get("name", "")
            link = camp.get("trackingUrl") or camp.get("url", "")
            descricao = camp.get("description", "")

            if not link or link in POSTADOS:
                continue

            preco = extrair_preco(descricao) or extrair_preco(titulo)
            if preco and (preco < PRECO_MIN or preco > PRECO_MAX):
                continue

            ofertas.append({
                "titulo": titulo[:100],
                "link": link,
                "preco": preco,
                "descricao": descricao[:200],
                "fonte": "Lomadee Campaign"
            })
            POSTADOS.add(link)

            if len(ofertas) >= 5:
                break

    except Exception as e:
        print(f"❌ Erro Lomadee campaigns: {e}")

    return ofertas


def buscar_produtos_lomadee():
    """Busca produtos na Lomadee por palavras-chave."""
    if not LOMADEE_API_KEY:
        return []

    ofertas = []
    query = random.choice(PALAVRAS_CHAVE)

    url = "https://api.lomadee.com.br/v3/products"
    headers = {"x-api-key": LOMADEE_API_KEY}
    params = {
        "q": query,
        "limit": 10,
        "page": 1
    }

    try:
        respeitar_rate_limit()
        resp = session.get(url, headers=headers, params=params, timeout=20)

        if resp.status_code == 401:
            print("❌ Lomadee API Key inválida. Verifique sua x-api-key.")
            return []
        if resp.status_code == 429:
            print("⚠️ Rate limit atingido na Lomadee. Aguarde...")
            return []
        if resp.status_code != 200:
            print(f"⚠️ Lomadee products retornou {resp.status_code}:", resp.text[:200])
            return []

        data = resp.json()
        produtos = data.get("data", [])

        for prod in produtos:
            titulo = prod.get("name", "")
            link = prod.get("trackingUrl") or prod.get("url", "")
            preco = prod.get("price")
            loja = prod.get("store", "")

            if not link or link in POSTADOS:
                continue

            if preco and (preco < PRECO_MIN or preco > PRECO_MAX):
                continue

            ofertas.append({
                "titulo": titulo[:100],
                "link": link,
                "preco": preco,
                "descricao": f"Loja: {loja}" if loja else "",
                "fonte": "Lomadee Products"
            })
            POSTADOS.add(link)

            if len(ofertas) >= 5:
                break

    except Exception as e:
        print(f"❌ Erro Lomadee products: {e}")

    return ofertas


# ========= RSS FEEDS (FALLBACK) =========
def buscar_ofertas_rss():
    """Busca ofertas nos feeds RSS (fallback se Lomadee falhar)."""
    ofertas = []

    for feed_url in RSS_FEEDS:
        try:
            print(f"📡 Buscando RSS: {feed_url}")
            resp = session.get(feed_url, timeout=20)

            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://purl.org/rss/1.0/}item")
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                titulo_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")

                titulo = limpar_html(titulo_elem.text) if titulo_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                descricao = limpar_html(desc_elem.text) if desc_elem is not None else ""

                if not link or link in POSTADOS:
                    continue

                preco = extrair_preco(titulo) or extrair_preco(descricao)
                if preco and (preco < PRECO_MIN or preco > PRECO_MAX):
                    continue

                fonte = feed_url.split("/")[2].replace("www.", "")
                ofertas.append({
                    "titulo": titulo[:100],
                    "link": link,
                    "preco": preco,
                    "descricao": descricao[:200],
                    "fonte": fonte
                })
                POSTADOS.add(link)

                if len(ofertas) >= 10:
                    break

        except Exception as e:
            print(f"⚠️ Erro RSS {feed_url}: {e}")

    return ofertas


# ========= TELEGRAM =========
def enviar_telegram(mensagem):
    """Envia mensagem para o canal do Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        resp = session.post(url, data=data, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Erro Telegram ({resp.status_code}):", resp.text[:200])
        else:
            print("✅ Mensagem enviada!")
    except Exception as e:
        print(f"❌ Falha Telegram: {e}")


# ========= FORMATAÇÃO =========
def formatar_oferta(oferta):
    """Formata a oferta em mensagem para o Telegram."""
    titulo = oferta["titulo"]
    link = oferta["link"]
    preco = oferta["preco"]
    fonte = oferta["fonte"]

    preco_str = f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if preco else "💰 Confira o preço no site"

    emoji = "🛒"
    if "Lomadee" in fonte:
        emoji = "💎 Lomadee (com comissão)"
    elif "promobit" in fonte:
        emoji = "🔴 Promobit"
    elif "gatry" in fonte:
        emoji = "🟠 Gatry"
    elif "pelando" in fonte:
        emoji = "🟢 Pelando"

    texto = f"""🔥 *PROMOÇÃO ENCONTRADA!*

📦 *{titulo}*

💸 *{preco_str}*

🏪 Fonte: {emoji}

👉 [Ver oferta]({link})

⏰ _{datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
    return texto


# ========= EXECUÇÃO PRINCIPAL =========
def postar_ofertas():
    """Busca ofertas na Lomadee (prioridade) e RSS (fallback)."""
    print(f"\n🤖 [{datetime.now()}] Iniciando busca de ofertas...")

    ofertas = []

    # 🥇 PRIORIDADE 1: Lomadee (com comissão)
    if LOMADEE_API_KEY:
        print("🔑 Buscando na Lomadee API...")
        ofertas += buscar_campaigns_lomadee()
        ofertas += buscar_produtos_lomadee()
    else:
        print("ℹ️ LOMADEE_API_KEY não configurada. Pulando Lomadee.")

    # 🥈 PRIORIDADE 2: RSS feeds (fallback)
    if not ofertas:
        print("📡 Nenhuma oferta Lomadee. Buscando RSS feeds...")
        ofertas += buscar_ofertas_rss()

    if not ofertas:
        print("⚠️ Nenhuma oferta encontrada neste ciclo.")
        return

    print(f"📦 {len(ofertas)} ofertas encontradas. Enviando...")

    for oferta in ofertas:
        mensagem = formatar_oferta(oferta)
        enviar_telegram(mensagem)
        time.sleep(random.uniform(2, 4))

    print(f"✅ Ciclo finalizado. Total no cache: {len(POSTADOS)} ofertas.")


# ========= AGENDAMENTO =========
schedule.every(5).minutes.do(postar_ofertas)

# ========= INICIALIZAÇÃO =========
if __name__ == "__main__":
    print("=" * 55)
    print("🤖 BOT DE OFERTAS - Lomadee + RSS Fallback")
    print("=" * 55)

    if LOMADEE_API_KEY:
        print("🔑 Modo: Lomadee API (com comissão de afiliado)")
        print(f"   API Key: {LOMADEE_API_KEY[:10]}...")
    else:
        print("📡 Modo: RSS Feeds (sem comissão - fallback)")
        print("   Para ganhar comissão, configure LOMADEE_API_KEY")

    print("=" * 55)

    # Primeira execução imediata
    postar_ofertas()

    print("\n⏳ Aguardando próximos ciclos...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Bot encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro no loop principal: {e}")
            time.sleep(5)
