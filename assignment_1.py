import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from stock import Stock

st.set_page_config(page_title="Stock Analysis", layout="wide")
st.title("Stock Analysis App")

# ---------- Sidebar (shared by both tabs) ----------
st.sidebar.header("Settings")
symbol = st.sidebar.text_input("Ticker symbol", "AAPL").upper().strip()
start = st.sidebar.date_input("Start date", dt.date.today() - dt.timedelta(days=365))
end = st.sidebar.date_input("End date", dt.date.today())
ma_window = st.sidebar.slider("Short moving average (days)", 5, 200, 20)
ma_window2 = st.sidebar.slider("Long moving average (days)", 5, 200, 50)


# ---------- Data loading (all data work goes through Stock) ----------
@st.cache_data
def load_stock(symbol, start, end, ma_window):
    """Create a Stock object. Cached so data isn't re-downloaded on every widget change."""
    return Stock(symbol, start=start, end=end, ma_window=ma_window)


def get_dates(data):
    """Return the date values whether Date is the index or a column."""
    return data["Date"] if "Date" in data.columns else data.index


tab1, tab2 = st.tabs(["Single Stock Analysis", "Portfolio Comparison"])

# ---------- Tab 1: Single Stock Analysis ----------
with tab1:
    if st.button("Fetch data"):
        st.session_state["fetched"] = True

    if st.session_state.get("fetched"):
        with st.spinner(f"Downloading {symbol}..."):
            stock = load_stock(symbol, start, end, ma_window)
            # Second moving average: a second Stock object with the long window,
            # so the MA calculation still happens inside the class.
            stock_long = load_stock(symbol, start, end, ma_window2)

        if stock.data is None:
            st.error(stock.message)
        else:
            st.success(stock.message)
            data = stock.data
            dates = get_dates(data)

            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Last close", f"${data['Close'].iloc[-1]:,.2f}",
                      f"{data['change'].iloc[-1]:+.2f} today")
            c2.metric("Cumulative return (log)", f"{data['return'].sum():.2%}")
            c3.metric("Trading days", len(data))

            # Price with moving averages
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=data["Close"], name="Close"))
            fig.add_trace(go.Scatter(x=dates, y=data["MA"], name=f"MA {ma_window}"))
            if stock_long.data is not None:
                fig.add_trace(go.Scatter(x=get_dates(stock_long.data),
                                         y=stock_long.data["MA"],
                                         name=f"MA {ma_window2}"))
            fig.update_layout(title=f"{symbol} Close Price and Moving Averages",
                              xaxis_title="Date", yaxis_title="Price ($)")
            st.plotly_chart(fig, use_container_width=True)

            # Charts from the class
            st.plotly_chart(stock.plot_performance(), use_container_width=True)
            st.plotly_chart(stock.plot_return_dist(), use_container_width=True)

            # Statistics table
            st.subheader("Return statistics")
            st.dataframe(data["return"].describe().to_frame())

# ---------- Tab 2: Portfolio Comparison ----------
with tab2:
    tickers_text = st.text_input("Tickers (comma-separated)", "AAPL, MSFT, GOOG")

    if st.button("Compare"):
        st.session_state["compared"] = True

    if st.session_state.get("compared"):
        tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
        fig = go.Figure()

        for t in tickers:
            with st.spinner(f"Downloading {t}..."):
                s = load_stock(t, start, end, ma_window)

            if s.data is None:
                st.error(f"{t}: {s.message}")
                continue  # skip this ticker, keep going

            # Zero-based cumulative performance: every line starts at exactly 0.0
            cum = s.data["return"].cumsum()
            cum = cum - cum.iloc[0]
            fig.add_trace(go.Scatter(x=get_dates(s.data), y=cum, name=t))

        if fig.data:
            fig.update_layout(title="Zero-Based Cumulative Performance",
                              xaxis_title="Date", yaxis_title="Cumulative log return",
                              legend_title="Ticker")
            st.plotly_chart(fig, use_container_width=True)
