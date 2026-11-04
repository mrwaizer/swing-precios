import json, time, datetime as dt, requests
from zoneinfo import ZoneInfo

AND = ZoneInfo("Europe/Andorra")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

SYMS = [
 ("S&P 500","^GSPC"),("EE.UU. 2000 (Russell 2000)","^RUT"),("EE.UU. 30 (Dow Jones)","^DJI"),
 ("Alemania 40 (DAX)","^GDAXI"),("Japon 225 (Nikkei)","^N225"),("ASX 200","^AXJO"),
 ("Suiza 20 (SMI)","^SSMI"),("Noruega 25 (OBX)","OBX.OL"),("Italia 40 (FTSE MIB)","FTSEMIB.MI"),
 ("Polonia 20 (WIG20)","WIG20.WA"),("Francia 40 (CAC 40)","^FCHI"),("Europa 50 (Euro Stoxx 50)","^STOXX50E"),
 ("UK 100 (FTSE 100)","^FTSE"),("Austria 20 (ATX)","^ATX"),("Nasdaq 100","^NDX"),
 ("Espana 35 (IBEX 35)","^IBEX"),("Holanda 25 (AEX)","^AEX"),("US MidCap 400","^MID"),
 ("Europe 600 (STOXX 600)","^STOXX"),("VIX","^VIX"),
 ("WTI","CL=F"),("Brent","BZ=F"),("Gas natural EEUU","NG=F"),("Oro","GC=F"),("Plata","SI=F"),
 ("DXY","DX-Y.NYB"),("EUR/USD","EURUSD=X"),("GBP/USD","GBPUSD=X"),("USD/JPY","JPY=X"),
 ("USD/CAD","CAD=X"),("AUD/USD","AUDUSD=X"),("NZD/USD","NZDUSD=X"),("USD/CHF","CHF=X"),
 ("EUR/GBP","EURGBP=X"),("EUR/JPY","EURJPY=X"),("CAD/JPY","CADJPY=X"),
 ("Treasury 2Y (rendimiento)","2YY=F"),("Treasury 10Y (rendimiento)","^TNX"),
]

def get(sym):
    for host in ("query1","query2"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"interval":"15m","range":"5d"}, headers=H, timeout=20)
            if r.status_code == 200:
                return r.json()["chart"]["result"][0]
        except Exception:
            pass
        time.sleep(1)
    return None

now = dt.datetime.now(dt.timezone.utc)
out = {"generado_utc": now.strftime("%Y-%m-%d %H:%M"),
       "generado_andorra": now.astimezone(AND).strftime("%Y-%m-%d %H:%M"), "datos": []}
lines = [f"PRECIOS generados {out['generado_andorra']} (hora Andorra) / {out['generado_utc']} UTC",
         "instrumento | simbolo | ultimo | var% vs cierre previo | var% ultimas ~3h | hora del ultimo dato (Andorra) | antiguedad min | estado"]
for name, sym in SYMS:
    row = {"instrumento": name, "simbolo": sym}
    res = get(sym)
    try:
        ts = res["timestamp"]; cl = res["indicators"]["quote"][0]["close"]
        pts = [(t, c) for t, c in zip(ts, cl) if c is not None]
        t_last, last = pts[-1]
        meta = res["meta"]
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        t3 = [c for t, c in pts if t <= t_last - 3*3600]
        ref3 = t3[-1] if t3 else None
        age = (now.timestamp() - t_last) / 60
        row.update(ultimo=round(last, 4),
                   var_vs_cierre_previo_pct=round((last/prev-1)*100, 2) if prev else None,
                   var_3h_pct=round((last/ref3-1)*100, 2) if ref3 else None,
                   hora_dato_andorra=dt.datetime.fromtimestamp(t_last, AND).strftime("%Y-%m-%d %H:%M"),
                   antiguedad_min=round(age), estado="ok")
    except Exception:
        row.update(estado="SIN DATO")
    out["datos"].append(row)
    lines.append(" | ".join(str(row.get(k, "-")) for k in
        ["instrumento","simbolo","ultimo","var_vs_cierre_previo_pct","var_3h_pct","hora_dato_andorra","antiguedad_min","estado"]))
    time.sleep(0.4)

json.dump(out, open("precios.json","w"), ensure_ascii=False, indent=1)
open("precios.txt","w").write("\n".join(lines) + "\n")
print("\n".join(lines))
