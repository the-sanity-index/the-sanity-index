# free_feed_api.py — Free Market Feed for The Sanity Index
# Uses stable, free, zero-rate-limit APIs:
# - Binance (crypto, real-time)
# - Financial Modeling Prep (indices, free demo key)
# - Frankfurter (FX via ECB)

import time, httpx
from fastapi import FastAPI, Query

API = FastAPI(title="Sanity Free Feed API", version="2.0")

def now_ts():
    return int(time.time())

async def get_json(url, params=None):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

# -------------------------------------------------------------------------
# CRYPTO — Binance (unlimited)
# -------------------------------------------------------------------------

@API.get("/crypto")
async def crypto():
    urls = {
        "BTC": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "ETH": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
    }
    out = {}
    for sym, url in urls.items():
        try:
            j = await get_json(url)
            out[sym] = float(j["price"])
        except Exception as e:
            out[sym] = {"error": str(e)}
    return {"ts": now_ts(), "data": out}

# -------------------------------------------------------------------------
# INDICES — FMP demo key (zero rate limits)
# -------------------------------------------------------------------------

FMP = "https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=demo"

INDEX_SYMBOLS = {
    "SPX": "%5EGSPC",
    "NDX": "%5ENDX",
    "FTSE": "%5EFTSE",
    "DAX": "%5EGDAXI",
    "N225": "%5EN225",
    "HSI": "%5EHSI"
}

@API.get("/indices")
async def indices():
    out = {}
    for name, symbol in INDEX_SYMBOLS.items():
        url = FMP.format(symbol=symbol)
        try:
            j = await get_json(url)
            if isinstance(j, list) and j:
                out[name] = {
                    "last": j[0]["price"],
                    "change": j[0]["change"],
                    "percent": j[0]["changesPercentage"],
                    "name": j[0]["name"]
                }
            else:
                out[name] = {"error": "No data returned"}
        except Exception as e:
            out[name] = {"error": str(e)}
    return {"ts": now_ts(), "data": out}

# -------------------------------------------------------------------------
# FX — ECB via Frankfurter (daily)
# -------------------------------------------------------------------------

@API.get("/fx")
async def fx():
    j = await get_json("https://api.frankfurter.app/latest", params={"base": "USD"})
    return {"date": j.get("date"), "data": j.get("rates", {})}

# -------------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------------

@API.get("/health")
async def health():
    return {"ok": True, "ts": now_ts()}
