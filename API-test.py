import yfinance as yf

ticker = yf.Ticker("AAPL")
price = ticker.fast_info["last_price"]
print("Price:", price)

hist = ticker.history(period="5d")
print(hist.tail())

