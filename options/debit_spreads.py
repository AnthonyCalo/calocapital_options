import sys
import pandas as pd
import yfinance as yf


class DebitSpreadAnalyzer:
    """Analyzes and ranks call debit spreads for options trading.
    Pricing strategy overviews. This is Debit Call spreads
    | Strategy           | Direction | Cash Flow | Risk Type       |
    | ------------------ | --------- | --------- | --------------- |
    | Call debit spread  | Bullish   | Pay       | Defined, small  |
    | Put debit spread   | Bearish   | Pay       | Defined, small  |
    | Call credit spread | Bearish   | Receive   | Defined, larger |
    | Put credit spread  | Bullish   | Receive   | Defined, larger |

    
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.spot_price = None
    
    def get_spot_price(self) -> float:
        """Get current spot price of the underlying asset."""
        if self.spot_price is not None:
            return self.spot_price
            
        # Try fast_info first, fall back to info
        try:
            spot = self.ticker.fast_info.get("lastPrice")
            if spot:
                self.spot_price = float(spot)
                return self.spot_price
        except Exception:
            pass
        
        self.spot_price = float(self.ticker.info["regularMarketPrice"])
        return self.spot_price
    
    def get_available_expirations(self) -> list:
        """Get list of available expiration dates."""
        exps = self.ticker.options
        if not exps:
            raise RuntimeError("No expiration dates available")
        return list(exps)
    
    def get_option_chain(self, expiration: str):
        """Get option chain for specific expiration date."""
        return self.ticker.option_chain(expiration)
    
    def build_call_debit_spreads(self, chain, expiration: str) -> pd.DataFrame:
        """
        Generate all possible call debit spreads with core metrics.
        Creates every possible call debit spread for that expiry:
        pick a lower strike call to buy
        pair it with every higher strike call to sell
        compute the spread’s risk/return numbers
        Output = a big table where each row is one trade idea.
        """
        calls = self._prepare_calls_data(chain.calls)
        spreads = []
        
        for _, long_call in calls.iterrows():
            short_calls = calls[calls["strike"] > long_call["strike"]]
            
            for _, short_call in short_calls.iterrows():
                spread = self._calculate_spread_metrics(long_call, short_call, expiration)
                if spread:  # Only add valid spreads
                    spreads.append(spread)
        
        return pd.DataFrame(spreads)
    
    def _prepare_calls_data(self, calls_df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare calls data for analysis."""
        calls = calls_df.copy()
        calls = calls.dropna(subset=["bid", "ask", "strike", "contractSymbol"])
        calls["mid"] = (calls["bid"] + calls["ask"]) / 2
        return calls
    
    def _calculate_spread_metrics(self, long_call, short_call, expiration: str) -> dict:
        """Calculate metrics for a single debit spread."""
        debit = float(long_call["mid"] - short_call["mid"])
        if debit <= 0:
            return None
        
        width = float(short_call["strike"] - long_call["strike"])
        max_profit = width - debit
        if max_profit <= 0:
            return None
        
        breakeven = float(long_call["strike"] + debit)
        pct_to_breakeven = (breakeven / self.get_spot_price() - 1) * 100
        
        return {
            "exp": expiration,
            "buy_call": long_call["contractSymbol"],
            "sell_call": short_call["contractSymbol"],
            "buyK": float(long_call["strike"]),
            "sellK": float(short_call["strike"]),
            "buy_mid": float(long_call["mid"]),
            "sell_mid": float(short_call["mid"]),
            "debit": debit,
            "max_loss_$": debit * 100,
            "max_profit_$": max_profit * 100,
            "breakeven": breakeven,
            "%ToBE": pct_to_breakeven,
            "ROI_x": max_profit / debit,
        }
    
    def rank_spreads(self, spreads_df: pd.DataFrame, 
                    max_pct_to_be: float = 25.0,
                    max_loss_usd: float = 250.0,
                    min_max_profit_usd: float = 300.0,
                    k_pct_penalty: float = 0.08,
                    top_n: int = 20) -> pd.DataFrame:
        """Filter, score, and rank spreads by attractiveness."""
        if spreads_df.empty:
            return spreads_df
        
        filtered = self._apply_filters(spreads_df, max_pct_to_be, max_loss_usd, min_max_profit_usd)
        if filtered.empty:
            return filtered
        
        scored = self._calculate_scores(filtered, k_pct_penalty)
        ranked = self._sort_and_format(scored, top_n)
        
        return ranked
    
    def _apply_filters(self, df: pd.DataFrame, max_pct_to_be: float, 
                      max_loss_usd: float, min_max_profit_usd: float) -> pd.DataFrame:
        """Apply filtering criteria to spreads."""
        filtered = df.copy()
        filtered = filtered[filtered["%ToBE"] <= max_pct_to_be]
        filtered = filtered[filtered["max_loss_$"] <= max_loss_usd]
        filtered = filtered[filtered["max_profit_$"] >= min_max_profit_usd]
        return filtered
    
    def _calculate_scores(self, df: pd.DataFrame, k_pct_penalty: float) -> pd.DataFrame:
        """Calculate attractiveness score for each spread."""
        df = df.copy()
        df["score"] = (df["max_profit_$"] / df["max_loss_$"]) - k_pct_penalty * df["%ToBE"]
        df["summary"] = df.apply(self._create_summary, axis=1)
        return df
    
    def _create_summary(self, row) -> str:
        """Create human-readable summary for a spread."""
        return (
            f"Buy {int(row['buyK'])}C / Sell {int(row['sellK'])}C | "
            f"Pay ${row['max_loss_$']:.0f} to make up to ${row['max_profit_$']:.0f} | "
            f"BE {row['breakeven']:.2f} (need {row['%ToBE']:+.1f}%)"
        )
    
    def _sort_and_format(self, df: pd.DataFrame, top_n: int) -> pd.DataFrame:
        """Sort spreads by score and format output."""
        df = df.sort_values(["score", "max_loss_$"], ascending=[False, True])
        
        display_columns = [
            "exp", "buy_call", "sell_call", "buyK", "sellK", "buy_mid", "sell_mid",
            "max_loss_$", "max_profit_$", "breakeven", "%ToBE", "ROI_x", "score", "summary"
        ]
        
        rounding_rules = {
            "buy_mid": 3, "sell_mid": 3, "max_loss_$": 2, "max_profit_$": 2,
            "breakeven": 2, "%ToBE": 2, "ROI_x": 2, "score": 3
        }
        
        return df[display_columns].head(top_n).round(rounding_rules)


class UserInterface:
    """Handles user interaction for spread analysis."""
    
    @staticmethod
    def choose_expiration(expirations: list) -> str:
        """Interactive expiration date selection."""
        while True:
            print("\nWhat expiry date are you looking at?\n")
            for i, exp in enumerate(expirations, 1):
                print(f"{i}. {exp}")
            
            choice = input("\nEnter number: ").strip()
            
            if not choice.isdigit():
                print("Please enter an integer.")
                continue
            
            idx = int(choice)
            if 1 <= idx <= len(expirations):
                return expirations[idx - 1]
            
            print(f"Please enter a number between 1 and {len(expirations)}.")
    
    @staticmethod
    def ask_max_pct_to_be(default: float = 15.0) -> float:
        """Interactive input for maximum percentage to breakeven."""
        while True:
            val = input(f"\nMax % move to breakeven? (default {default}%): ").strip()
            
            if val == "":
                return default
            
            try:
                v = float(val)
                if v <= 0:
                    raise ValueError
                return v
            except ValueError:
                print("Enter a positive number (e.g. 10, 15, 20)")


def main():
    """Main execution function."""
    symbol = "UBER"
    analyzer = DebitSpreadAnalyzer(symbol)
    ui = UserInterface()
    
    # Get available expirations and let user choose
    expirations = analyzer.get_available_expirations()
    selected_expiration = ui.choose_expiration(expirations)
    max_pct_to_be = ui.ask_max_pct_to_be(default=15.0)
    
    # Get data and analyze spreads
    chain = analyzer.get_option_chain(selected_expiration)
    spot = analyzer.get_spot_price()
    
    print(f"\nSelected: {symbol} {selected_expiration} | Spot: {spot:.2f}\n")
    
    # Build and rank spreads
    all_spreads = analyzer.build_call_debit_spreads(chain, selected_expiration)
    top_spreads = analyzer.rank_spreads(
        all_spreads,
        max_pct_to_be=max_pct_to_be,
        max_loss_usd=200,
        min_max_profit_usd=200,
        k_pct_penalty=0.08,
        top_n=15
    )
    
    # Display results
    if top_spreads.empty:
        print("No spreads matched your filters. Try loosening max_pct_to_be / max_loss_usd.")
        sys.exit(0)
    
    print(top_spreads.to_string(index=False))


if __name__ == "__main__":
    main()
