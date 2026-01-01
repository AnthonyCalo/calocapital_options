import pandas as pd
import yfinance as yf 

sym = "AMD"
t = yf.Ticker(sym)

def scan_call_debit_spreads(chain, spot, exp=None,
                            max_debit_pct=0.05,
                            min_roi=1.0,
                            top_n=15):
    """
    Scan call debit spreads for asymmetric upside.

    Inputs:
      chain : yfinance OptionChain
      spot  : underlying price (float)
      exp   : expiration label (optional, just for display)

    Returns:
      pandas DataFrame of top candidates
    """

    calls = chain.calls.copy()
    calls = calls.dropna(subset=["bid", "ask", "strike"])
    calls["mid"] = (calls["bid"] + calls["ask"]) / 2

    rows = []

    for _, long in calls.iterrows():
        shorts = calls[calls["strike"] > long["strike"]]

        for _, short in shorts.iterrows():
            debit = long["mid"] - short["mid"]
            if debit <= 0:
                continue

            width = short["strike"] - long["strike"]
            max_profit = width - debit
            if max_profit <= 0:
                continue

            roi = max_profit / debit
            if roi < min_roi:
                continue

            if debit > max_debit_pct * spot:
                continue

            breakeven = long["strike"] + debit
            pct_to_be = (breakeven / spot - 1) * 100

            rows.append({
                "exp": exp,
                "buyK": long["strike"],
                "sellK": short["strike"],
                "debit": round(debit, 2),
                "maxProfit": round(max_profit, 2),
                "breakeven": round(breakeven, 2),
                "ROI": round(roi, 2),
                "%ToBE": round(pct_to_be, 2),
            })

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values(["ROI", "debit"], ascending=[False, True])
        .head(top_n)
    )

if __name__ == '__main__':
    spot = t.fast_info["lastPrice"]
    exp = t.options[6]
    chain = t.option_chain(exp)

    df = scan_call_debit_spreads(chain, spot, exp)
    print(df.to_string(index=False))

