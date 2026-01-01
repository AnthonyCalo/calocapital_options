import time
import pandas as pd
import numpy as np
import yfinance as yf

'''
    goals
    what do i want to accomplish:
        I want to see which companies are trading significantly below ps or pe ratios than usual.
        output sorted list specifically higlighting when a company has growing revenue over 10% annually but is trading low
'''


watchlist = [
    "VXX", "DWMC", "GBET", "AI", "GEO", "SOFI", "BWMN","DKNG", "DDOG", "PYPL", "HOOD"
    "JOBY", "FIG", "COGT", "CAT", "ASTS", "RXLB", "IMVZ", "SMCI", "NFLX", "GS",
    "NOW", "META", "GS", "SPOT", "SPY", "MSFT", "MA", "DE", "LMT", "V",
    "TSLA", "CRM", "JPM", "GOOGL", "TDG", "BA", "CRM", "NVDA", "AVGO", "PANW", "SNOW", "GOOG", "XAR", "PM", "NET", "NVDA", "BABA", "MS",
    "AMZN", "DIS", "ED", "WMT", "ROKU", "DOCU", "NKE", "UBER", "QRVO","Z", "KO", "XYZ", "CBOD", "CVS", "KBE", "MO", "OGIG", "BAC", "VZ",
    "JD", "BTI", "AMD", "IBKR"
]




import os, pandas as pd

path = os.path.expanduser("~/simfin_data/us-derived-shareprices-daily.csv")
usecols = ["Ticker", "Date", "Close", "Price to Sales Ratio (ttm)"]

print("Loading dataset once...")
chunks = pd.read_csv(path, sep=";", usecols=usecols, parse_dates=["Date"], chunksize=250_000)
data = pd.concat(chunks)  # all tickers at once (still reasonable if you filter columns)
print("Done loading.")


def detect_ps_anomalies(ticker: str, df: pd.DataFrame) -> dict:
    print(ticker)
    """Compute P/S stats & anomalies for one ticker, using preloaded df."""
    sub = df[df["Ticker"] == ticker].sort_values("Date")
    ps = round(sub["Price to Sales Ratio (ttm)"].dropna().astype(float), 2)
    if ps.empty:
        return {"ticker": ticker, "error": "no data"}

    stats = {
        "ticker": ticker,
        "count": int(ps.count()),
        "mean": ps.mean(),
        "median": ps.median(),
        "std": round(ps.std(), 2),
        "min": round(ps.min(), 2),
        "max": round(ps.max(), 2),
        "range": round(ps.max() - ps.min(), 2),
        "25th_percentile": round(ps.quantile(0.25), 2),
        "75th_percentile": round(ps.quantile(0.75), 2),
        "iqr": round(ps.quantile(0.75) - ps.quantile(0.25), 2),
        "current": round(ps.iloc[-1], 2),
    }

    z = (stats["current"] - stats["mean"]) / stats["std"]
    stats["z_score_current"] = round(z, 2)
    stats["label"] = (
        "undervalued" if z <= -1.5 else
        "overvalued" if z >= 1.5 else
        "normal"
    )
    return stats


if __name__ == '__main__':
    results = [detect_ps_anomalies(t, data) for t in watchlist]
    df_results = pd.DataFrame(results).set_index("ticker")
    print(df_results.sort_values("z_score_current", inplace=True))
    df_results.to_csv("./ps_ratio.csv")
