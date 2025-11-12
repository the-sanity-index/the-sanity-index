# free_feed_api.py
# A free-tier Market Feed Aggregator for The Sanity Index
# Uses only open data sources (no paid keys)

import time, httpx
from typing import Dict, Any
from fastapi import FastAPI, Query

API = FastAPI(title="Sanity Free Feed API", version="0.1")

# ---------------------------------------------------------------------
def now_ts() -> int:
    return int(time.time())

async def get_json(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

def ttl_cache(ttl_seconds: int):
    def _decorator(func):
        cache, stamp = {}, {}
        async def _wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items()))); t = time.time()
            if key in cache and (t-stamp[key])<ttl_seconds:
                return cache[key]
            res = await func(*args, **kwargs)
            cache[key], stamp[key] = res, t
            return res
        return _wrapper
    return _decorator

# ---------------------------------------------------------------------
# Yahoo Finance (~15 min delayed)
YF_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

@ttl_cache(60)
async def yahoo_quotes(symbols: str):
    j = await get_json(YF_URL, params={"symbols": symbols})
    results = j.get("quoteResponse", {}).get("result", [])
    out = {}
    for r in results:
        sym = r.get("symbol")
        out[sym] = {
            "symbol": sym,
            "name": r.get("shortName") or r.get("longName"),
            "last": r.get("regularMarketPrice"),
            "change": r.get("regularMarketChange"),
            "percent": r.get("regularMarketChangePercent"),
            "currency": r.get("currency"),
            "exchange": r.get("fullExchangeName"),
            "delayed": True
        }
    return {"ts": now_ts(), "data": out}

# ---------------------------------------------------------------------
# CoinGecko (crypto realtime)
CG_URL = "https://api.coingecko.com/api/v3/simple/price"

@ttl_cache(5)
async def coingecko_prices(ids: str = "bitcoin,ethereum", vs: str = "usd"):
    j = await get_json(CG_URL, params={"ids": ids, "vs_currencies": vs})
    out = {k.upper(): {vs.upper(): v.get(vs)} for k, v in j.items()}
    return {"ts": now_ts(), "data": out}

# ---------------------------------------------------------------------
# Frankfurter (ECB FX daily)
FX_URL = "https://api.frankfurter.app/latest"

@ttl_cache(3600)
async def fx_pairs(pairs: str = "EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    j = await get_json(FX_URL, params={"base": "USD"})
    rates = j.get("rates", {})
    def resolve(pair):
        pair = pair.upper().strip(); a,b = pair[:3], pair[3:]
        if a=="USD" and b in rates: return rates[b]
        if b=="USD" and a in rates: v=rates[a]; return None if not v else 1.0/v
        if a in rates and b in rates:
            vb,va = rates[b], rates[a]
            return None if not(vb and va) else vb/va
        return None
    out = {p: resolve(p) for p in pairs.split(",")}
    return {"date": j.get("date"), "base": "USD", "data": out}

# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@API.get("/health")
async def health(): return {"ok": True, "ts": now_ts()}

@API.get("/indices")
async def indices():
    syms = "^GSPC,^NDX,^FTSE,^GDAXI,^N225,^HSI"
    return await yahoo_quotes(syms)

@API.get("/commodities")
async def commodities():
    syms = "CL=F,BZ=F,GC=F,SI=F"
    return await yahoo_quotes(syms)

@API.get("/crypto")
async def crypto(ids: str = "bitcoin,ethereum", vs: str = "usd"):
    return await coingecko_prices(ids, vs)

@API.get("/fx")
async def fx(pairs: str = "EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    return await fx_pairs(pairs)
