# Descarga los canales publicos de Telegram (t.me/s/...) y escribe noticias.txt
# con fecha y hora exactas (hora Andorra) de cada mensaje de las ultimas 24 h.
import re, html, datetime as dt
import requests
from zoneinfo import ZoneInfo

AND = ZoneInfo("Europe/Andorra")
HORAS = 24          # ventana que se guarda
MAX_PAG = 25        # paginas maximas por canal (20 mensajes cada una)
UA = {"User-Agent": "Mozilla/5.0"}

def canales():
    out = []
    for l in open("canales.txt", encoding="utf-8"):
        l = l.split("#")[0].strip()
        if l:
            out.append(l.replace("https://t.me/s/", "").replace("https://t.me/", "").strip("/@ "))
    return out

def limpiar(t):
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def pagina(ch, before=None):
    url = f"https://t.me/s/{ch}" + (f"?before={before}" if before else "")
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    msgs = []
    for bloque in r.text.split('class="tgme_widget_message_wrap')[1:]:
        m_id = re.search(r'data-post="[^"/]+/(\d+)"', bloque)
        m_t = re.search(r'<time[^>]*datetime="([^"]+)"', bloque)
        m_x = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', bloque, re.S)
        if not (m_id and m_t):
            continue
        msgs.append((int(m_id.group(1)), dt.datetime.fromisoformat(m_t.group(1)), limpiar(m_x.group(1)) if m_x else "[sin texto: foto/video]"))
    return msgs

def main():
    corte = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=HORAS)
    todos, estado = [], []
    for ch in canales():
        n, before, viejo, err = 0, None, None, ""
        try:
            for _ in range(MAX_PAG):
                ms = pagina(ch, before)
                if not ms:
                    break
                for mid, t, x in ms:
                    if t >= corte:
                        todos.append((t, ch, x)); n += 1
                viejo = min(t for _, t, _ in ms)
                before = min(mid for mid, _, _ in ms)
                if viejo < corte:
                    break
        except Exception as e:
            err = f" ERROR {type(e).__name__}"
        v = viejo.astimezone(AND).strftime("%d/%m %H:%M") if viejo else "-"
        estado.append(f"{ch}: {n} mensajes en {HORAS}h, mas antiguo leido {v}{err}")
    todos.sort(key=lambda a: a[0], reverse=True)
    ahora = dt.datetime.now(AND).strftime("%Y-%m-%d %H:%M")
    with open("noticias.txt", "w", encoding="utf-8") as f:
        f.write(f"NOTICIAS TELEGRAM generadas {ahora} (hora Andorra). Ventana {HORAS} h. Mas nuevas arriba.\n")
        f.write("Formato: dd/mm HH:MM (hora Andorra) | canal | texto\n")
        f.write("ESTADO: " + " ; ".join(estado) + "\n\n")
        for t, ch, x in todos:
            f.write(f"{t.astimezone(AND).strftime('%d/%m %H:%M')} | {ch} | {x[:600]}\n")

if __name__ == "__main__":
    main()
