# Stocklist — Nifty 500

Mobile-friendly end-of-day screener built for Tejas's Stocklist criteria. **Initial state: market data not connected.** The interface never presents sample prices as live data.

## Activate real rankings

1. An official NSE Indices `universe.csv` snapshot is included, downloaded from https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv . Cross-check it against your preferred Moneycontrol Nifty 500 universe before activation. CSV headers: `Company Name,Industry,Symbol,ISIN Code`. Use actual ISINs, not guessed symbol mappings. Moneycontrol source: https://www.moneycontrol.com/markets/indian-indices/ . Verify all constituents and date your membership review. The collector accepts 490–510 unique members to accommodate temporary corporate-action constituent changes; it does not assert index membership independently.
2. Create an Angel One SmartAPI API access token, then add it in this repository's **Settings → Secrets and variables → Actions → New repository secret**, named `ANGEL_ACCESS_TOKEN`, and add the API key as `ANGEL_API_KEY`. The access token must be a valid authenticated SmartAPI session JWT. This version does not store account PINs or TOTP secrets or automate login. Follow Angel One requirements for session renewal and runner IP access. Do not put the token in code, JSON, or chat. Standard tokens expire and need renewal. Documentation: https://smartapi.angelone.in/docs and https://github.com/angel-one/smartapi-python . Ensure your data subscription permits your intended display/use. The existing GitHub repository is public, so its saved data is public too.
3. Run **Actions → Refresh Stocklist → Run workflow**. It also runs weekdays at 17:30 IST (GitHub scheduling can be delayed). This is a saved daily snapshot, not streaming prices. Holidays preserve the most recent available session. A failed run preserves the previous snapshot; UI flags old snapshots.
4. Refresh the website. It loads `dist/data.json` from this repository; if unreachable it falls back to its bundled snapshot. Local serving: `python -m http.server 8000 --directory dist`.

## Scoring

Hard gate: 50-day simple moving average **strictly greater** than 200-day SMA. At least 250 daily candles required. New listings without enough history are excluded, with coverage displayed. Corporate-action adjustments depend on the provider; verify unusual signals around splits/bonuses before relying on them.

| Component | Maximum | Implemented rule |
|---|---:|---|
| Golden cross / trend | 20 | 15 for DMA50 > DMA200; 20 if both averages also rose over 5 sessions. Recent 5-session cross identified in details. |
| RSI 14, Wilder | 15 | 15 if rising today after a reading from 25–30 in preceding 5 sessions; otherwise 5 if below 30. |
| MACD 12/26/9 | 20 | Bullish cross in last 5 sessions still intact: 20 if MACD and signal positive, otherwise 15. Above signal without recent cross: 5. |
| OBV | 15 | OBV above its level 5 sessions ago. |
| Bollinger 20/2 | 10 | Close was within 1% of or below lower band in prior 5 sessions; now above lower band, rising, and at/below middle band. |
| Stochastic 14/3 | 10 | K crossed above D in last 5 sessions from an oversold reading below 20; K remains above D. |
| Market/economic | 10 | Four equal 2.5-point checks: sentiment, macro, institutional flows, positive company news. Dated source required for each. |

Weights reproduce the user's original specification. Partial points, crossover lookback, near-band tolerance, and material-improvement threshold are explicit implementation defaults, not previously agreed exact thresholds. Technical sorting is consistently out of 90; full score out of 100 is shown only with all four market checks. Unknown market factors never become fabricated zero/positive evidence or get normalized to 100.

Materially stronger: eligible with technical score up at least 10 points versus previous distinct saved snapshot and at least one improved signal. First scans have no delta. Same-session reruns preserve the original comparison. This is an on-page filter, not an external notification subscription.

Optional `market-context.json` schema:

```json
{
  "ACTUAL_NSE_SYMBOL": {
    "sentiment": {"positive": true, "date": "YYYY-MM-DD", "source": "https://actual-source-url"},
    "macro": {"positive": false, "date": "YYYY-MM-DD", "source": "https://actual-source-url"},
    "flows": {"positive": true, "date": "YYYY-MM-DD", "source": "https://actual-stock-specific-source-url"},
    "news": {"positive": true, "date": "YYYY-MM-DD", "source": "https://actual-source-url"}
  }
}
```

Only source-backed entries matching the candle date qualify. Market-wide FII/DII activity must not be labeled stock-specific accumulation. This version has no automatic news, macro or institutional-data integration and does not apply discretionary sector boosts. Sector filtering is available.

## Validation

`python -m unittest discover -s tests` validates SMA values, RSI flat-market behavior, trend-gate rejection, absence of false reversals in monotonic trends, and invalid/insufficient candle rejection. `node --check dist/app.js` verifies JavaScript syntax. Live API integration remains untested until credentials and a verified universe are configured.

## Hosting

`dist/` is a standalone static site. For GitHub Pages, select **GitHub Actions** in Settings → Pages and run the **Publish GitHub Pages** workflow. The private Sites copy can read daily data from the public repository without republishing the interface. To update its UI, redeploy through Sites.
