# free_feed_api.py — Free Market Feed for The Sanity Index
# Uses open data sources ONLY (Yahoo, CoinGecko, ECB).
# FIXED: Yahoo 429 (Too Many Requests) by requesting symbols individually.
# FIXED: Route decorator conflict which broke /quote and /indices

import time, httpx
from typing import Dict, Any
from fastapi import FastAPI, Query

API = FastAPI(title="Sanity Free Feed API", version="1.2")

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def now_ts() -> int:
    return int(time.time())

async def get_json(url: str, params: Dict[str, Any] | None = None):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

def ttl_cache(ttl_seconds: int):
    def _decorator(func):
        cache, stamp = {}, {}
        async def _wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            t = time.time()
            if key in cache and (t - stamp[key]) < ttl_seconds:
                return cache[key]
            res = await func(*args, **kwargs)
            cache[key] = res
            stamp[key] = t
            return res
        return _wrapper
    return _decorator

# ---------------------------------------------------------------------
# Yahoo Finance (Delayed ~15 min)
# ---------------------------------------------------------------------

YF_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

@ttl_cache(30)
async def yahoo_quote_single(symbol: str):
    """Fetch a single Yahoo Finance quote safely."""
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
# FIXED /quote endpoint
# ---------------------------------------------------------------------
@API.get("/quote")
async def quote(symbol: str = Query(..., alias="symbols")):
    try:
        result = await yahoo_quote_single(symbol)
        return {"ts": now_ts(), "data": result}
    except Exception as e:
        return {"ts": now_ts(), "error": str(e)}

# ---------------------------------------------------------------------
# FIXED /indices endpoint
# ---------------------------------------------------------------------
@API.get("/indices")
async def indices():
    symbols = ["^GSPC", "^NDX", "^FTSE", "^GDAXI", "^N225", "^HSI"]
    results = {}

    for sym in symbols:
        try:
            data = await yahoo_quote_single(sym)
            results.update(data)
        except Exception as e:
            results[sym] = {"error": str(e)}

    return {"ts": now_ts(), "data": results}

# ---------------------------------------------------------------------
# Crypto (real-time) via CoinGecko
# ---------------------------------------------------------------------

CG_URL = "https://api.coingecko.com/api/v3/simple/price"

@ttl_cache(5)
async def coingecko_prices(ids="bitcoin,ethereum", vs="usd"):
    j = await get_json(CG_URL, params={"ids": ids, "vs_currencies": vs})
    out = {k.upper(): {vs.upper(): v.get(vs)} for k, v in j.items()}
    return {"ts": now_ts(), "data": out}

@API.get("/crypto")
async def crypto(ids: str = "bitcoin,ethereum", vs: str = "usd"):
    return await coingecko_prices(ids, vs)

# ---------------------------------------------------------------------
# FX - ECB via Frankfurter
# ---------------------------------------------------------------------

FX_URL = "https://api.frankfurter.app/latest"

@ttl_cache(3600)
async def fx_pairs(pairs="EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    j = await get_json(FX_URL, params={"base": "USD"})
    rates = j.get("rates", {})

    def resolve(pair: str):
        pair = pair.upper().strip()
        a, b = pair[:3], pair[3:]

        if a == "USD" and b in rates:
            return rates[b]
        if b == "USD" and a in rates:
            v = rates[a]
            return None if not v else 1.0 / v
        if a in rates and b in rates:
            va, vb = rates[a], rates[b]
            return None if not (va and vb) else vb / va
        return None

    out = {p: resolve(p) for p in pairs.split(",")}
    return {"date": j.get("date"), "base": "USD", "data": out}

@API.get("/fx")
async def fx(pairs: str = "EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD"):
    return await fx_pairs(pairs)

# ---------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------
@API.get("/health")
async def health():
    return {"ok": True, "ts": now_ts()}
