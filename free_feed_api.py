# free_feed_api.py — Free Market Feed for The Sanity Index
# Fixed /quote and /indices endpoints — no decorator conflicts

import time, httpx
from typing import Dict, Any
from fastapi import FastAPI, Query

API = FastAPI(title="Sanity Free Feed API", version="1.3")

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def now_ts():
    return int(time.time())

async def get_json(url: str, params=None):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

def ttl_cache(ttl_seconds: int):
    def wrap(func):
        cache, stamp = {}, {}
        async def inner(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            t = time.time()
            if key in cache and (t - stamp[key]) < ttl_seconds:
                return cache[key]
            result = await func(*args, **kwargs)
            cache[key] = result
            stamp[key] = t
            return result
        return inner
    return wrap

# ---------------------------------------------------------------------
# Yahoo Finance (Delayed 15m) — Single-symbol fetch
# ---------------------------------------------------------------------

YF_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

@ttl_cache(30)
async def yahoo_quote_single(symbol: str):
    j = await get_json(YF_URL, params={"symbols": symbol})
    results = j.get("quoteResponse", {}).get("result", [])
    if not results:
        return {symbol: {"error": "No data returned"}}

    r = results[0]
    return {
        symbol: {
            "symbol": symbol,
            "name": r.get("shortName") or r.get("longName"),
            "last": r.get("regularMarketPrice"),
            "change": r.get("regularMarketChange"),
            "percent": r.get("regularMarketChangePercent"),
            "currency": r.get("currency"),
            "exchange": r.get("fullExchangeName"),
            "delayed": True,
        }
    }

# ---------------------------------------------------------------------
# /quote — FIXED
# ---------------------------------------------------------------------
@API.get("/quote")
async def quote(symbol: str = Query(..., alias="symbols")):
    try:
        result = await yahoo_quote_single(symbol)
        return {"ts": now_ts(), "data": result}
    except Exception as e:
        return {"ts": now_ts(), "error": str(e)}

# ---------------------------------------------------------------------
# /indices — FIXED
# ---------------------------------------------------------------------
@API.get("/indices")
async def indices():
    symbols = ["^GSPC", "^NDX", "^FTSE", "^GDAXI", "^N225", "^HSI"]
    results = {}

    for sym in symbols:
        try:
            res = await yahoo_quote_single(sym)
            results.update(res)
        except Exception as e:
            results[sym] = {"error": str(e)}

    return {"ts": now_ts(), "data": results}

# ---------------------------------------------------------------------
# Crypto via CoinGecko
# ---------------------------------------------------------------------

CG_URL = "https://api.coingecko.com/api/v3/simple/price"

@ttl_cache(5)
async def coingecko_prices(ids="bitcoin,ethereum", vs="usd"):
    j = await get_json(CG_URL, params={"ids": ids, "vs_currencies": vs})
    return {"ts": now_ts(), "data": {k.upper(): {vs.upper(): v.get(vs)} for k, v in j.items()}}

@API.get("/crypto")
async def crypto(ids: str = "bitcoin,ethereum", vs: str = "usd"):
    return await coingecko_prices(ids, vs)

# ---------------------------------------------------------------------
# FX via Frankfurter / ECB
# ---------------------------------------------------------------------

FX_URL = "https://api.frankfurter.app/latest"

@ttl_cache(3600)
async def fx_pairs(pairs="EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    j = await get_json(FX_URL, params={"base": "USD"})
    rates = j.get("rates", {})

    def resolve(pair):
        pair = pair.upper()
        a, b = pair[:3], pair[3:]
        if a == "USD" and b in rates:
            return rates[b]
        if b == "USD" and a in rates:
            v = rates[a]
            return None if not v else 1.0/v
        if a in rates and b in rates:
            if rates[a] and rates[b]:
                return rates[b] / rates[a]
        return None

    return {"date": j.get("date"), "base": "USD", "data": {p: resolve(p) for p in pairs.split(",")}}

@API.get("/fx")
async def fx(pairs: str = "EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    return await fx_pairs(pairs)

# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------
@API.get("/health")
async def health():
    return {"ok": True, "ts": now_ts()}
