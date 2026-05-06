import requests
import schedule
import time
import random
import re
from datetime import datetime
import xml.etree.ElementTree as ET
import os

# ================= CONFIGURAÇÃO =================
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    from dotenv import load_dotenv
    load_dotenv()

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
LOMADEE_API_KEY = os.getenv("LOMADEE_API_KEY")

if not TOKEN_TELEGRAM or not CHAT_ID:
    raise Exception("❌ TOKEN_TELEGRAM ou CHAT_ID não configurados nas variáveis de ambiente")

# ================================================

# 🔥 PALAVRAS-CHAVE PARA BUSCA NA LOMADEE
PALAVRAS_CHAVE = [
    "iphone", "smartphone samsung", "notebook", "fone bluetooth", "smart tv",
    "caixa de som", "monitor", "placa de video", "ssd", "headset",
    "smartwatch", "tablet", "playstation", "xbox", "nintendo switch",
    "gabinete gamer", "processador", "mouse gamer", "teclado gamer", "fonte",
]

# 🔥 RSS FEEDS BRASILEIROS (FALLBACK)
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

ULTIMA_REQ_LOMADEE = 0


# ========= FUNÇÕES AUXILIARES =========
def respeitar_rate_limit():
    """Garante intervalo mínimo de 7 segundos entre chamadas Lomadee."""
    global ULTIMA_REQ_LOMADEE
    agora = time.time()
    tempo_decorrido = agora - ULTIMA_REQ_LOMADEE
    if tempo_decorrido < 7:
        time.sleep(7 - tempo_decorrido)
    ULTIMA_REQ_LOMADEE = time.time()


def extrair_preco(texto):
    if not texto:
        return None
    padroes = [
        r'R\$\s*([\d\.]+(?:,\d{2})?)',
        r'por\s*R\$\s*([\d\.]+(?:,\d{2})?)',
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
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = texto.replace("&nbsp;", " ").replace("&amp;", "&")
    return texto.strip()


# ========= LOMADEE API =========
def buscar_lomadee():
    """Busca ofertas na Lomadee API v3."""
    if not LOMADEE_API_KEY:
        print("ℹ️ LOMADEE_API_KEY não configurada.")
        return []

    ofertas = []

    # 🥇 Tenta buscar campanhas/ofertas ativas
    url = "https://api-beta.lomadee.com.br/v3/campaigns"
    headers = {"x-api-key": LOMADEE_API_KEY}

    try:
        respeitar_rate_limit()
        print(f"🔑 Chamando Lomadee: {url}")
        resp = session.get(url, headers=headers, timeout=20)

        print(f"📡 Status Lomadee: {resp.status_code}")

        if resp.status_code == 401:
            print("❌ Lomadee API Key inválida (401).")
            return []
        if resp.status_code == 429:
            print("⚠️ Rate limit Lomadee (429).")
            return []
        if resp.status_code != 200:
            print(f"⚠️ Lomadee retornou {resp.status_code}: {resp.text[:300]}")
            return []

        # Verifica se a resposta é JSON válido
        content_type = resp.headers.get('content-type', '')
        if 'application/json' not in content_type:
            print(f"⚠️ Lomadee retornou content-type: {content_type} (esperava JSON)")
            print(f"   Resposta: {resp.text[:300]}")
            return []

        try:
            data = resp.json()
        except Exception as e:
            print(f"❌ Lomadee retornou JSON inválido: {e}")
            print(f"   Resposta bruta: {resp.text[:300]}")
            return []

        campaigns = data.get("data", [])
        print(f"📦 {len(campaigns)} campanhas encontradas na Lomadee")

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
                "fonte": "Lomadee"
            })
            POSTADOS.add(link)

            if len(ofertas) >= 8:
                break

    except requests.exceptions.Timeout:
        print("❌ Timeout na Lomadee API")
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão com Lomadee API")
    except Exception as e:
        print(f"❌ Erro Lomadee: {e}")

    return ofertas


# ========= RSS FEEDS (FALLBACK) =========
def buscar_ofertas_rss():
    """Busca ofertas nos feeds RSS."""
    ofertas = []

    for feed_url in RSS_FEEDS:
        try:
            print(f"📡 Buscando RSS: {feed_url}")
            resp = session.get(feed_url, timeout=20)

            if resp.status_code != 200:
                print(f"⚠️ RSS {feed_url} retornou {resp.status_code}")
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://purl.org/rss/1.0/}item")
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

            print(f"📄 {len(items)} itens no RSS {feed_url}")

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

        except ET.ParseError as e:
            print(f"❌ XML inválido em {feed_url}: {e}")
        except Exception as e:
            print(f"⚠️ Erro RSS {feed_url}: {e}")

    return ofertas


# ========= TELEGRAM =========
def enviar_telegram(mensagem):
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
    print(f"\n🤖 [{datetime.now()}] Iniciando busca de ofertas...")

    ofertas = []

    # 🥇 PRIORIDADE 1: Lomadee
    if LOMADEE_API_KEY:
        print("🔑 Modo Lomadee ativo. Buscando campanhas...")
        ofertas_lomadee = buscar_lomadee()
        ofertas += ofertas_lomadee

        if not ofertas_lomadee:
            print("⚠️ Lomadee não retornou ofertas. Verifique se a API Key está correta.")
    else:
        print("ℹ️ LOMADEE_API_KEY não configurada. Pulando Lomadee.")

    # 🥈 PRIORIDADE 2: RSS feeds (sempre busca, mesmo que Lomadee tenha retornado algo)
    if len(ofertas) < 3:
        print("📡 Buscando RSS feeds para complementar...")
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
schedule.every(10).minutes.do(postar_ofertas)

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
        print("   Configure LOMADEE_API_KEY para ganhar comissão")

    print("=" * 55)

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
