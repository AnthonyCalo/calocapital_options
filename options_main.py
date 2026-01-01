import yfinance as yf

sym = "AMD"
t = yf.Ticker(sym)

exps = t.options
if not exps:
    raise RuntimeError("No expirations returned")
    # for ex in exps:
    #     print(ex)
exp = exps[-1]   # nearest; change this to pick a LEAP, e.g. exps[-1]

chain = t.option_chain(exp)

# Calculate breakeven prices for calls and puts
calls = chain.calls[['contractSymbol', 'strike', 'ask']]
puts = chain.puts[['contractSymbol', 'strike', 'ask']]

calls['breakeven'] = calls['strike'] + calls['ask']
puts['breakeven'] = calls['strike'] - puts['ask']

print("\nCALLS (breakeven, head 15)")
print(calls[['contractSymbol', 'strike', 'ask', 'breakeven']].head(15).to_string(index=False))

print("\nPUTS (breakeven, head 15)")
print(puts[['contractSymbol', 'strike', 'ask', 'breakeven']].head(15).to_string(index=False))

# print(type(chain))
# print(chain)
# breakpoint()
# calls = chain.calls[['contractSymbol','strike','bid','ask','lastPrice','impliedVolatility','volume','openInterest']]
# puts  = chain.puts [['contractSymbol','strike','bid','ask','lastPrice','impliedVolatility','volume','openInterest']]

# print("\nCALLS (head)")
# print(calls.head(15).to_string(index=False))

# print("\nPUTS (head)")
# print(puts.head(15).to_string(index=False))
