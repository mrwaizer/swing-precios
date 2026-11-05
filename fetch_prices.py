import json, time, csv, os, re, datetime as dt, requests
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
