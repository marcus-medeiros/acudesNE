import requests
from datetime import datetime
import time
import threading
from flask import Flask
import os

# 🔹 TOKEN (coloque no Render como variável de ambiente)
TOKEN = "8101772535:AAEp4qLZf2zvM0TNPcMiEi7qwsf_ym1tsrg"
URL_TELEGRAM = f"https://api.telegram.org/bot{TOKEN}"

# 🔹 API ANA
URL_ANA = "https://www.ana.gov.br/sar/restportal/api/retornaMedicoes"

# 🔹 FAVORITOS
FAV_PB = ["FARINHA","MÃE D'ÁGUA","CUREMA", "JATOBÁ I"]
FAV_RN = ["ARMANDO RIBEIRO", "OITICICA", "UMARÍ"]

# 🔹 FLASK
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 Bot rodando!"


# =========================
# 🔹 MENU
# =========================
def get_menu():
    return {
        "keyboard": [
            ["📊 AÇUDES PB", "📊 AÇUDES RN"],
            ["⭐ PB FAVORITOS", "⭐ RN FAVORITOS"],
            ["📍 AÇUDES", "⭐ FAVORITOS"]
        ],
        "resize_keyboard": True
    }


# =========================
# 🔹 UTIL
# =========================
def dividir_mensagem(texto, limite=4000):
    partes = []
    while len(texto) > limite:
        partes.append(texto[:limite])
        texto = texto[limite:]
    partes.append(texto)
    return partes


# =========================
# 🔹 FUNÇÃO GERAL
# =========================
def get_acudes(uf, filtro=None):
    data_atual = datetime.now().strftime("%a %b %d %Y %H:%M:%S GMT-0300 (Horário Padrão de Brasília)")

    params = {
        "data": data_atual,
        "siglaUf": uf,
        "tipoSistema": 1
    }

    try:
        response = requests.get(URL_ANA, params=params, timeout=10)
        dados = response.json()
    except Exception as e:
        return [f"Erro {uf}: {e}"]

    resultado = []
    favoritos = FAV_PB if uf == "PB" else FAV_RN

    for d in dados:
        nome = d.get("reservatorio") or ""

        if filtro == "fav":
            if not any(f in nome.upper() for f in favoritos):
                continue

        cidade = (d.get("municipio") or "Sem cidade").title()
        volume = d.get("volume") or "-"
        percentual = d.get("volumeUtil") or "-"
        data = d.get("data") or "-"

        linha = f"{nome} ({cidade}): {volume} hm³ ({percentual}%) - {data}"
        resultado.append(linha)

    return resultado


# =========================
# 🔹 TELEGRAM
# =========================
def get_updates(offset=None):
    url = f"{URL_TELEGRAM}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    return requests.get(url, params=params, timeout=15).json()


def send_message(chat_id, text, keyboard=None):
    url = f"{URL_TELEGRAM}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    requests.post(url, json=data, timeout=10)


def enviar_resposta(chat_id, resposta):
    menu = get_menu()

    if isinstance(resposta, list):
        for msg in resposta:
            partes = dividir_mensagem(msg)
            for p in partes:
                send_message(chat_id, p, menu)
    else:
        partes = dividir_mensagem(resposta)
        for p in partes:
            send_message(chat_id, p, menu)


# =========================
# 🔹 COMANDOS / MENU
# =========================
def executar_comando(texto):
    comando = texto.upper()

    if comando in ["📊 AÇUDES PB", "/ACUDESPB"]:
        pb = "\n".join(get_acudes("PB"))
        return f"📊 AÇUDES PB\n\n{pb}"

    elif comando in ["📊 AÇUDES RN", "/ACUDESRN"]:
        rn = "\n".join(get_acudes("RN"))
        return f"📊 AÇUDES RN\n\n{rn}"

    elif comando in ["⭐ PB FAVORITOS", "/ACUDESPB FAV"]:
        pb = "\n".join(get_acudes("PB", "fav"))
        return f"⭐ AÇUDES PB (FAVORITOS)\n\n{pb}"

    elif comando in ["⭐ RN FAVORITOS", "/ACUDESRNFAV"]:
        rn = "\n".join(get_acudes("RN", "fav"))
        return f"⭐ AÇUDES RN (FAVORITOS)\n\n{rn}"

    elif comando in ["📍 TODOS", "/ACUDES"]:
        pb = "\n".join(get_acudes("PB"))
        rn = "\n".join(get_acudes("RN"))
        return [
            f"📊 AÇUDES PB\n\n{pb}",
            f"📊 AÇUDES RN\n\n{rn}"
        ]

    elif comando in ["⭐ FAVORITOS", "/ACUDESFAV"]:
        pb = "\n".join(get_acudes("PB", "fav"))
        rn = "\n".join(get_acudes("RN", "fav"))
        return [
            f"⭐ AÇUDES PB (FAVORITOS)\n\n{pb}",
            f"⭐ AÇUDES RN (FAVORITOS)\n\n{rn}"
        ]

    else:
        return "👆 Use o menu abaixo para escolher uma opção"


# =========================
# 🔹 LOOP DO BOT
# =========================
def rodar_bot():
    update_id = None
    print("🤖 Bot rodando...")

    while True:
        try:
            updates = get_updates(update_id)

            if not updates.get("ok"):
                time.sleep(1)
                continue

            for item in updates.get("result", []):
                update_id = item["update_id"] + 1

                if "message" not in item:
                    continue

                message = item["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                print("Mensagem:", text)

                resposta = executar_comando(text)
                enviar_resposta(chat_id, resposta)

            time.sleep(0.5)

        except Exception as e:
            print("Erro:", e)
            time.sleep(2)


# =========================
# 🔹 START
# =========================
if __name__ == "__main__":
    t = threading.Thread(target=rodar_bot)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
