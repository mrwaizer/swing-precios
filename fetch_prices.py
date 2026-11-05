import json, time, csv, os, datetime as dt, requests
from zoneinfo import ZoneInfo

AND = ZoneInfo("Europe/Andorra")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept": "application/json,text/plain,*/*"}

# nombre, simbolo CNBC, simbolo CBOE (solo EE.UU.)
SYMS = [
 ("S&P 500", ".SPX", "_SPX"), ("EE.UU. 2000 (Russell 2000)", ".RUT", "_RUT"), ("EE.UU. 30 (Dow Jones)", ".DJI", "_DJX"),
 ("Alemania 40 (DAX)", ".GDAXI", None), ("Japon 225 (Nikkei)", ".N225", None), ("ASX 200", ".AXJO", None),
 ("Suiza 20 (SMI)", ".SSMI", None), ("Noruega 25 (OBX)", ".OBX", None), ("Italia 40 (FTSE MIB)", ".FTMIB", None),
 ("Polonia 20 (WIG20)", ".WIG20", None), ("Francia 40 (CAC 40)", ".FCHI", None), ("Europa 50 (Euro Stoxx 50)", ".STOXX50E", None),
 ("UK 100 (FTSE 100)", ".FTSE", None), ("Austria 20 (ATX)", ".ATX", None), ("Nasdaq 100", ".NDX", "_NDX"),
 ("Espana 35 (IBEX 35)", ".IBEX", None), ("Holanda 25 (AEX)", ".AEX", None), ("US MidCap 400", ".MID", None),
 ("Europe 600 (STOXX 600)", ".STOXX", None), ("VIX", ".VIX", "_VIX"),
 ("WTI", "@CL.1", None), ("Brent", "@LCO.1", None), ("Gas natural EEUU", "@NG.1", None), ("Oro", "@GC.1", None), ("Plata", "@SI.1", None),
 ("DXY", ".DXY", None), ("EUR/USD", "EUR=", None), ("GBP/USD", "GBP=", None), ("USD/JPY", "JPY=", None),
 ("USD/CAD", "CAD=", None), ("AUD/USD", "AUD=", None), ("NZD/USD", "NZD=", None), ("USD/CHF", "CHF=", None),
 ("EUR/GBP", "EURGBP=", None), ("EUR/JPY", "EURJPY=", None), ("CAD/JPY", "CADJPY=", None),
 ("Treasury 2Y (rendimiento)", "US2Y", None), ("Treasury 10Y (rendimiento)", "US10Y", None),
 # ---- FUTUROS que funcionan ----
 ("FUT Russell 2000", "@TFS.1", None), ("FUT VIX", "@VX.1", None), ("FUT DXY", "@DX.1", None),
 ("FUT Nikkei", "@NK.1", None), ("FUT FTSE 100", "@FFI.1", None),
 ("FUT S&P 500", "@SP.1", None), ("FUT Nasdaq 100", "@ND.1", None), ("FUT Dow (verificar)", "@DJ.1", None),
]

# simbolos extra para probar: archivo extra.txt, una linea por simbolo: nombre,simbolo
try:
    for ln in open("extra.txt", encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "," in ln:
            n, sy = ln.rsplit(",", 1)
            SYMS.append((n.strip(), sy.strip(), None))
except FileNotFoundError:
    pass

now = dt.datetime.now(dt.timezone.utc)
probe = []

# ---- CNBC: una sola peticion con los 38 ----
cnbc = {}
try:
    syms = "|".join(s[1] for s in SYMS)
    r = requests.get("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol",
                     params={"symbols": syms, "requestMethod": "itv", "noform": "1", "partnerId": "2",
                             "fund": "1", "exthrs": "1", "output": "json"}, headers=H, timeout=30)
    probe.append(f"cnbc HTTP {r.status_code} {len(r.text)} bytes")
    if r.status_code == 200:
        q = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        if isinstance(q, dict):
            q = [q]
        for it in q:
            cnbc[it.get("symbol")] = it
        probe.append(f"cnbc simbolos devueltos {len(cnbc)}")
    else:
        probe.append("cnbc cuerpo: " + r.text[:100])
except Exception as e:
    probe.append(f"cnbc ERROR {type(e).__name__} {str(e)[:80]}")


# ---- SONDEO experimental: historico diario CNBC (solo diagnostico) ----
try:
    _r = requests.get("https://ts-api.cnbc.com/harmony/app/bars/@GC.1/1D/20261001000000/20261231000000/adjusted/EXTENDED.json",
                      headers=H, timeout=20)
    probe.append(f"hist-cnbc HTTP {_r.status_code} {len(_r.text)} bytes {_r.text[:90]!r}")
except Exception as e:
    probe.append(f"hist-cnbc ERROR {type(e).__name__}")

def num(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").replace("+", ""))
    except Exception:
        return None

def parse_time(s):
    if not s:
        return None
    s = str(s)
    for f in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return dt.datetime.strptime(s, f)
        except Exception:
            pass
    return None

def cboe(sym):
    try:
        r = requests.get(f"https://cdn.cboe.com/api/global/delayed_quotes/quotes/{sym}.json", headers=H, timeout=20)
        d = r.json()["data"]
        t = dt.datetime.strptime(r.json()["timestamp"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("America/New_York"))
        return num(d.get("current_price")), num(d.get("price_change_percent")), t
    except Exception:
        return None

lines = [f"PRECIOS generados {now.astimezone(AND).strftime('%Y-%m-%d %H:%M')} (hora Andorra) / {now.strftime('%Y-%m-%d %H:%M')} UTC",
         "SONDEO: " + " || ".join(probe),
         "instrumento | simbolo | ultimo | var% vs cierre previo | hora del dato (cruda/Andorra) | antiguedad min | fuente | estado"]
out = {"generado_utc": now.strftime("%Y-%m-%d %H:%M"), "sondeo": probe, "datos": []}
for name, cs, bs in SYMS:
    row = {"instrumento": name, "simbolo": cs, "estado": "SIN DATO", "fuente": "-"}
    it = cnbc.get(cs)
    if it and num(it.get("last")) is not None:
        t = parse_time(it.get("last_time"))
        row.update(ultimo=num(it.get("last")), var_pct=num(it.get("change_pct")),
                   hora_cruda=str(it.get("last_time")), mercado=it.get("curmktstatus"), fuente="cnbc", estado="ok")
        if t:
            row["hora_andorra"] = t.astimezone(AND).strftime("%Y-%m-%d %H:%M")
            row["antiguedad_min"] = round((now - t.astimezone(dt.timezone.utc)).total_seconds() / 60)
    elif bs:
        c = cboe(bs)
        if c:
            row.update(ultimo=c[0], var_pct=c[1], hora_andorra=c[2].astimezone(AND).strftime("%Y-%m-%d %H:%M"),
                       antiguedad_min=round((now - c[2].astimezone(dt.timezone.utc)).total_seconds() / 60),
                       fuente="cboe", estado="ok")
    out["datos"].append(row)
    lines.append(" | ".join(str(row.get(k, "-")) for k in
        ["instrumento", "simbolo", "ultimo", "var_pct", "hora_andorra", "antiguedad_min", "fuente", "estado"])
        + f" | cruda={row.get('hora_cruda','-')} | mercado={row.get('mercado','-')}")
    time.sleep(0.2)


# ---- HISTORIAL PROPIO: un valor por instrumento y dia (el ultimo visto de ese dia) ----
HF = "historial.csv"
hist = {}
if os.path.exists(HF):
    for rw in csv.reader(open(HF, encoding="utf-8")):
        if len(rw) == 3 and rw[0] != "fecha":
            try:
                hist[(rw[0], rw[1])] = float(rw[2])
            except ValueError:
                pass
for rw in out["datos"]:
    if rw["estado"] == "ok" and rw.get("hora_andorra") and rw.get("ultimo") is not None:
        hist[(rw["hora_andorra"][:10], rw["instrumento"])] = rw["ultimo"]
cut = (now - dt.timedelta(days=400)).strftime("%Y-%m-%d")
hist = {k: v for k, v in hist.items() if k[0] >= cut}
with open(HF, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["fecha", "instrumento", "valor"])
    for (d, n), v in sorted(hist.items()):
        w.writerow([d, n, v])

lines.append("")
lines.append("HISTORIAL (desde el historial propio; cada dia = ultimo valor visto ese dia; los dias de 24h como oro o divisas son aproximados; '-' = aun no hay sesiones suficientes)")
lines.append("instrumento | sesiones en historial | var% vs 1 sesion antes | var% vs 5 sesiones antes | var% vs 20 sesiones antes | max 20 ses | min 20 ses")
for rw in out["datos"]:
    n = rw["instrumento"]
    if n.startswith("FUT"):
        continue
    ser = sorted((d, v) for (d, nn), v in hist.items() if nn == n)
    if rw["estado"] != "ok" or not rw.get("hora_andorra") or not ser:
        lines.append(f"{n} | {len(ser)} | - | - | - | - | -")
        continue
    cur_d, cur = rw["hora_andorra"][:10], rw["ultimo"]
    prev = [v for d, v in ser if d < cur_d]
    def pct(k):
        if len(prev) >= k and prev[-k]:
            return f"{(cur / prev[-k] - 1) * 100:+.2f}"
        return "-"
    win = [v for d, v in ser][-20:]
    lines.append(f"{n} | {len(ser)} | {pct(1)} | {pct(5)} | {pct(20)} | {max(win)} | {min(win)}")

json.dump(out, open("precios.json", "w"), ensure_ascii=False, indent=1)
open("precios.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
