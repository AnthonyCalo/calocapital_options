import os, json
from getpass import getpass
import robin_stocks.robinhood as r

username = "username"
mfa_code = input("MFA code (if prompted on device, press Enter): ")

# Avoid writing tokens to disk
r.login(username, "password", mfa_code=mfa_code or None, store_session=False)

# Fetch watchlist symbols (handles multiple watchlists)
items = r.account.get_all_watchlists()
print(items, "HERE")
symbols = [it["symbol"] for it in items]

print(symbols)
with open("watchlist.json", "w") as f:
    json.dump(symbols, f, indent=2)

r.logout()
