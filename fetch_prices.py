import json, time, sys, io, csv, re, subprocess, datetime as dt, requests
from zoneinfo import ZoneInfo

AND = ZoneInfo("Europe/Andorra")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}

# nombre, simbolo Yahoo, simbolo Stooq
SYMS = [
 ("S&P 500","^GSPC","^spx"),("EE.UU. 2000 (Russell 2000)","^RUT","^rut"),("EE.UU. 30 (Dow Jones)","^DJI","^dji"),
 ("Alemania 40 (DAX)","^GDAXI","^dax"),("Japon 225 (Nikkei)","^N225","^nkx"),("ASX 200","^AXJO","^xjo"),
 ("Suiza 20 (SMI)","^SSMI","^smi"),("Noruega 25 (OBX)","OBX.OL","^obx"),("Italia 40 (FTSE MIB)","FTSEMIB.MI","^fmib"),
 ("Polonia 20 (WIG20)","WIG20.WA","^wig20"),("Francia 40 (CAC 40)","^FCHI","^cac"),("Europa 50 (Euro Stoxx 50)","^STOXX50E","^sx5e"),
 ("UK 100 (FTSE 100)","^FTSE","^ukx"),("Austria 20 (ATX)","^ATX","^atx"),("Nasdaq 100","^NDX","^ndx"),
 ("Espana 35 (IBEX 35)","^IBEX","^ibex"),("Holanda 25 (AEX)","^AEX","^aex"),("US MidCap 400","^MID","^mid"),
 ("Europe 600 (STOXX 600)","^STOXX","^stoxx"),("VIX","^VIX","^vix"),
 ("WTI","CL=F","cl.f"),("Brent","BZ=F","lco.f"),("Gas natural EEUU","NG=F","ng.f"),("Oro","GC=F","gc.f"),("Plata","SI=F","si.f"),
 ("DXY","DX-Y.NYB","dx.f"),("EUR/USD","EURUSD=X","eurusd"),("GBP/USD","GBPUSD=X","gbpusd"),("USD/JPY","JPY=X","usdjpy"),
 ("USD/CAD","CAD=X","usdcad"),("AUD/USD","AUDUSD=X","audusd"),("NZD/USD","NZDUSD=X","nzdusd"),("USD/CHF","CHF=X","usdchf"),
 ("EUR/GBP","EURGBP=X","eurgbp"),("EUR/JPY","EURJPY=X","eurjpy"),("CAD/JPY","CADJPY=X","cadjpy"),
 ("Treasury 2Y (rendimiento)","2YY=F","2usy.b"),("Treasury 10Y (rendimiento)","^TNX","10usy.b"),
]

now = dt.datetime.now(dt.timezone.utc)
probe = []

def p(msg):
    probe.append(msg)

# ---- SONDEO: que fuentes responden desde GitHub ----
try:
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yfinance"], capture_output=True, text=True, timeout=300)
    p(f"pip yfinance rc={r.returncode} {(r.stderr or r.stdout)[-150:].strip()}")
except Exception as e:
    p(f"pip yfinance error {type(e).__name__}")

TESTS = [
 ("stooq quote", "https://stooq.com/q/l/?s=^dax&f=sd2t2ohlcv&h&e=csv"),
 ("stooq diario", "https://stooq.com/q/d/l/?s=^dax&i=d"),
 ("yahoo v7", "https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5EGDAXI"),
 ("cboe spx", "https://cdn.cboe.com/api/global/delayed_quotes/quotes/_SPX.json"),
 ("frankfurter", "https://api.frankfurter.app/latest?from=EUR&to=USD"),
 ("investing dax", "https://es.investing.com/indices/germany-30"),
]
for label, url in TESTS:
    try:
        r = requests.get(url, headers=H, timeout=20)
        extra = ""
        if label == "investing dax":
            m = re.search(r'instrument-price-last[^>]*>([^<]+)<', r.text)
            extra = " precio=" + (m.group(1) if m else "no encontrado")
        p(f"{label}: HTTP {r.status_code} {r.text[:90].strip()!r}{extra}")
    except Exception as e:
        p(f"{label}: ERROR {type(e).__name__}")

# ---- Fuentes de datos ----
ERR = {}

def via_yahoo(sym):
    last = "sin respuesta"
    for host in ("query1", "query2"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"interval": "15m", "range": "5d"}, headers=H, timeout=20)
            if r.status_code == 200:
                res = r.json()["chart"]["result"][0]
                pts = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
                m = res["meta"]
                return pts, (m.get("chartPreviousClose") or m.get("previousClose")), "yahoo"
            last = f"yahoo {r.status_code}"
        except Exception as e:
            last = f"yahoo {type(e).__name__}"
        break
    ERR[sym] = last
    return None

def via_stooq(sy, key):
    try:
        r = requests.get("https://stooq.com/q/l/", params={"s": sy, "f": "sd2t2ohlcv", "h": "", "e": "csv"}, headers=H, timeout=20)
        rows = list(csv.DictReader(io.StringIO(r.text)))
        row = rows[0]
        if row["Close"] in ("N/D", "", None):
            ERR[key] = ERR.get(key, "") + " | stooq N/D"
            return None
        t = dt.datetime.strptime(row["Date"] + " " + row["Time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=AND)
        last = float(row["Close"])
        prev = None
        try:
            d = requests.get("https://stooq.com/q/d/l/", params={"s": sy, "i": "d"}, headers=H, timeout=20)
            dr = list(csv.DictReader(io.StringIO(d.text)))
            if len(dr) >= 2:
                prev = float(dr[-2]["Close"]) if dr[-1]["Date"] == row["Date"] else float(dr[-1]["Close"])
        except Exception:
            pass
        if prev is None:
            prev = float(row["Open"])
        return [(int(t.timestamp()), last)], prev, "stooq"
    except Exception as e:
        ERR[key] = ERR.get(key, "") + f" | stooq {type(e).__name__}"
        return None

def via_yf(sym):
    try:
        import yfinance as yf
        h = yf.Ticker(sym).history(period="5d", interval="15m")
        if h is None or len(h) == 0:
            ERR[sym] = ERR.get(sym, "") + " | yf vacio"
            return None
        pts = [(int(i.timestamp()), float(c)) for i, c in zip(h.index, h["Close"]) if c == c]
        d = yf.Ticker(sym).history(period="5d", interval="1d")
        prev = float(d["Close"].iloc[-2]) if d is not None and len(d) >= 2 else None
        return pts, prev, "yf"
    except Exception as e:
        ERR[sym] = ERR.get(sym, "") + f" | yf {type(e).__name__}"
        return None

out = {"generado_utc": now.strftime("%Y-%m-%d %H:%M"),
       "generado_andorra": now.astimezone(AND).strftime("%Y-%m-%d %H:%M"), "sondeo": probe, "datos": []}
lines = [f"PRECIOS generados {out['generado_andorra']} (hora Andorra) / {out['generado_utc']} UTC",
         "SONDEO: " + " || ".join(probe),
         "instrumento | simbolo | ultimo | var% vs cierre previo | var% ultimas ~3h | hora del ultimo dato (Andorra) | antiguedad min | fuente | estado"]
for name, ysym, ssym in SYMS:
    row = {"instrumento": name, "simbolo": ysym}
    res = via_yahoo(ysym) or via_stooq(ssym, ysym) or via_yf(ysym)
    try:
        pts, prev, src = res
        t_last, last = pts[-1]
        t3 = [c for t, c in pts if t <= t_last - 3 * 3600]
        ref3 = t3[-1] if t3 else None
        age = (now.timestamp() - t_last) / 60
        row.update(ultimo=round(last, 4),
                   var_vs_cierre_previo_pct=round((last / prev - 1) * 100, 2) if prev else None,
                   var_3h_pct=round((last / ref3 - 1) * 100, 2) if ref3 else None,
                   hora_dato_andorra=dt.datetime.fromtimestamp(t_last, AND).strftime("%Y-%m-%d %H:%M"),
                   antiguedad_min=round(age), fuente=src, estado="ok")
    except Exception:
        row.update(fuente="-", estado="SIN DATO: " + ERR.get(ysym, "?"))
    out["datos"].append(row)
    lines.append(" | ".join(str(row.get(k, "-")) for k in
        ["instrumento", "simbolo", "ultimo", "var_vs_cierre_previo_pct", "var_3h_pct", "hora_dato_andorra", "antiguedad_min", "fuente", "estado"]))
    time.sleep(0.5)

json.dump(out, open("precios.json", "w"), ensure_ascii=False, indent=1)
open("precios.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
