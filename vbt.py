import marimo

__generated_with = "0.10.5"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    from pyecharts.charts import Bar, Candlestick, Kline
    from pyecharts import options as opts
    from pyecharts.globals import CurrentConfig, NotebookType
    CurrentConfig.NOTEBOOK_TYPE = NotebookType.JUPYTER_LAB
    import vectorbt as vbt
    import os
    import pandas as pd

    df=pd.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
    #df=df.set_index('epoch')
    return (
        Bar,
        Candlestick,
        CurrentConfig,
        Kline,
        NotebookType,
        df,
        mo,
        opts,
        os,
        pd,
        pl,
        vbt,
    )


@app.cell
def _(df):
    df1=df[['epoch','close','symbol']]
    df1=df1.pivot_table(index='epoch',columns='symbol', values='close',aggfunc='last')
    return (df1,)


@app.cell
def _(df, df1, pd, rsi, talib, vbt):
    #rsi=vbt.RSI.run(df1)
    import talib as tl

    def cust_ind(high,low,close,vol):
        macd, sig, hist= tl.MACD(df,fastperiod=10,slowperiod=20,signalperiod=6)
        slowk, slowd=tl.STOCH(high,low,close)
        obv = talib.OBV(df['Close'], df['Volume'])
        macd_cross = (macd > sig) & (macd.shift(1) <= sig.shift(1))
        stoch_buy = (slowk < 20) & (slowd < 20)


    ind=vbt.IndicatorFactory(class_name="Combination",short_name="comb",input_names=['high','low','close','volume'],param_names=['window'],
            output_names='value').from_apply_func(cust_ind)

    res=ind.run(df1)
    w1 = pd.Series([0.20, 0.20, 0.20, 0.20, 0.20], index=df1.columns)
    normdf = df1 / df1.iloc[0] * 100
    portdf=(normdf* w1).sum(axis=1)
    entries= rsi.rsi_crossed_below(30)
    exits= rsi.rsi_crossed_above(70)

    pf=vbt.Portfolio.from_orders(portdf,init_cash=1000,freq='1D')
    pf.plot(template='plotly_white')
    return cust_ind, entries, exits, ind, normdf, pf, portdf, res, tl, w1


@app.cell
def _(pf):
    pf.stats(column=3).to_string()
    return


@app.cell
def _(yf):
    dat = {}
    for symbo in ['AAPL','GOOGL']:
        stock = yf.download(symbo)
        dat[symbo] = stock
    dat
    return dat, stock, symbo


@app.cell
def _(os, pd, vbt, yf):
    import talib
    from pathlib import Path

    class MultiStockBacktester:
        def __init__(self, symbols, start_date, end_date, data_path='stock_data.parquet'):
            self.symbols = symbols
            self.start_date = start_date
            self.end_date = end_date
            self.data_path = data_path
            self.data = {}
            self.signals = {}
            self.results = {}

        def load_or_fetch_data(self, force_download=False):
            if not force_download and os.path.exists(self.data_path):
                print("Loading data from parquet file...")
                combined_df = pd.read_parquet(self.data_path)

                for symbol in self.symbols:
                    self.data[symbol] = combined_df.xs(symbol, level='Symbol')

            else:
                print("Fetching data from Yahoo Finance...")
                combined_data = []

                for symbol in self.symbols:
                    stock = yf.download(symbol, start=self.start_date, end=self.end_date)
                    stock['Symbol'] = symbol
                    combined_data.append(stock)

                combined_df = pd.concat(combined_data, keys=self.symbols, names=['Symbol', 'Date'])
                combined_df.to_parquet(self.data_path)
                print(f"Data saved to {self.data_path}")

                for symbol in self.symbols:
                    self.data[symbol] = combined_df.xs(symbol, level='Symbol')

        def calculate_indicators(self):
            for symbol, df in self.data.items():
                # Ensure data is clean and sorted
                df = df.sort_index()
                df = df.ffill()  # Forward fill missing values

                # Convert to numpy arrays and ensure correct dtype
                close = df['Close'].astype(float).to_numpy()
                high = df['High'].astype(float).to_numpy()
                low = df['Low'].astype(float).to_numpy()
                volume = df['Volume'].astype(float).to_numpy()

                # Calculate indicators with error handling
                try:
                    # MACD (12, 26, 9 are the default periods)
                    macd, macd_signal, _ = talib.MACD(close, 
                                                     fastperiod=12, 
                                                     slowperiod=26, 
                                                     signalperiod=9)

                    # RSI (14 is the default period)
                    rsi = talib.RSI(close, timeperiod=14)

                    # OBV (no parameters needed)
                    obv = talib.OBV(close, volume)

                    # Stochastic (5, 3, 0 are the default periods)
                    slowk, slowd = talib.STOCH(high, 
                                             low, 
                                             close,
                                             fastk_period=5,
                                             slowk_period=3,
                                             slowk_matype=0)

                    # Convert back to pandas Series with proper index
                    self.signals[symbol] = {
                        'macd': pd.Series(macd, index=df.index),
                        'macd_signal': pd.Series(macd_signal, index=df.index),
                        'rsi': pd.Series(rsi, index=df.index),
                        'obv': pd.Series(obv, index=df.index),
                        'slowk': pd.Series(slowk, index=df.index),
                        'slowd': pd.Series(slowd, index=df.index)
                    }

                except Exception as e:
                    print(f"Error calculating indicators for {symbol}: {str(e)}")
                    continue

        def generate_entry_signals(self):
            for symbol in self.symbols:
                if symbol not in self.signals:
                    continue

                signals = self.signals[symbol]

                # Handle NaN values
                macd = signals['macd'].fillna(0)
                macd_signal = signals['macd_signal'].fillna(0)
                rsi = signals['rsi'].fillna(0)
                slowk = signals['slowk'].fillna(0)
                slowd = signals['slowd'].fillna(0)
                obv = signals['obv'].fillna(0)

                # MACD crossover
                macd_cross = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))

                # RSI conditions
                rsi_buy = rsi < 30

                # Stochastic conditions
                stoch_buy = (slowk < 20) & (slowd < 20)

                # OBV trend
                obv_sma = obv.rolling(window=20, min_periods=1).mean()
                obv_trend = obv > obv_sma

                # Combined signal
                entry_signal = macd_cross & rsi_buy & stoch_buy & obv_trend

                # Clean up signal and convert to numpy array
                entry_signal = entry_signal.fillna(False)
                entry_signal = vbt.signals.nb.clean_enex_1d_nb(entry_signal.values)

                self.signals[symbol]['entry'] = entry_signal

        def generate_exit_signals(self):
            for symbol in self.symbols:
                if symbol not in self.signals:
                    continue

                signals = self.signals[symbol]

                # Handle NaN values
                rsi = signals['rsi'].fillna(0)
                slowk = signals['slowk'].fillna(0)
                slowd = signals['slowd'].fillna(0)
                macd = signals['macd'].fillna(0)
                macd_signal = signals['macd_signal'].fillna(0)

                # Exit conditions
                rsi_sell = rsi > 70
                stoch_sell = (slowk > 80) & (slowd > 80)
                macd_cross_below = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))

                # Combined exit signal
                exit_signal = rsi_sell | stoch_sell | macd_cross_below

                # Clean up signal and convert to numpy array
                exit_signal = exit_signal.fillna(False)
                exit_signal = vbt.signals.nb.clean_enex_1d_nb(exit_signal.values)

                self.signals[symbol]['exit'] = exit_signal

        def run_backtest(self, initial_capital=100000, fee_rate=0.001):
            for symbol in self.symbols:
                if symbol not in self.signals:
                    continue

                price = self.data[symbol]['Close']
                entries = self.signals[symbol]['entry']
                exits = self.signals[symbol]['exit']

                portfolio = vbt.Portfolio.from_signals(
                    price,
                    entries,
                    exits,
                    init_cash=initial_capital,
                    fees=fee_rate,
                    freq='1D'
                )

                metrics = {
                    'total_return': portfolio.total_return(),
                    'sharpe_ratio': portfolio.sharpe_ratio(),
                    'max_drawdown': portfolio.max_drawdown(),
                    'win_rate': portfolio.win_rate(),
                    'profit_factor': portfolio.profit_factor(),
                    'num_trades': portfolio.num_trades()
                }

                self.results[symbol] = {
                    'portfolio': portfolio,
                    'metrics': metrics
                }

        def get_summary(self):
            summary = []
            for symbol in self.symbols:
                if symbol in self.results:
                    metrics = self.results[symbol]['metrics']
                    metrics['symbol'] = symbol
                    summary.append(metrics)

            return pd.DataFrame(summary).set_index('symbol')

    def run_example():
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        backtester = MultiStockBacktester(
            symbols=symbols,
            start_date='2020-01-01',
            end_date='2023-12-31',
            data_path='stock_data.parquet'
        )

        # Run analysis
        backtester.load_or_fetch_data(force_download=False)
        backtester.calculate_indicators()
        backtester.generate_entry_signals()
        backtester.generate_exit_signals()
        backtester.run_backtest(initial_capital=100000)

        # Get results
        summary = backtester.get_summary()
        print("\nBacktest Results Summary:")
        print(summary)

        # Plot results for each symbol
        for symbol in symbols:
            if symbol in backtester.results:
                portfolio = backtester.results[symbol]['portfolio']
                portfolio.plot()

    if __name__ == "__main__":
        run_example()
    return MultiStockBacktester, Path, run_example, talib


@app.cell
def _(pd, vbt):
    import yfinance as yf
    import numpy as np

    # Download historical data for multiple assets
    symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN']
    start_date = '2020-01-01'
    end_date = '2024-01-01'

    # Download data using yfinance
    data = pd.DataFrame()
    for symbol in symbols:
        temp = yf.download(symbol, start=start_date, end=end_date)['Adj Close']
        data[symbol] = temp

    # Calculate returns
    returns = data.pct_change()

    # Create equal-weight portfolio weights
    weights = pd.Series([0.25, 0.25, 0.25, 0.25], index=symbols)

    # Create portfolio
    # First normalize prices to starting price of 100
    normalized_data = data / data.iloc[0] * 100

    # Calculate portfolio value
    portfolio_value = (normalized_data * weights).sum(axis=1)

    # Initialize Portfolio with single series
    portfolio = vbt.Portfolio.from_orders(
        close=portfolio_value,
        init_cash=10000,
        freq='1D'
    )

    # Create visualization
    fig = portfolio.plot(
        title='Multi-Asset Portfolio Performance',
        template='plotly_white'
    )

    # Customize layout
    fig.update_layout(
        height=1000,
        width=1200,
        showlegend=True
    )

    # Display performance metrics
    print("\nPortfolio Performance Metrics:")
    print("======================")
    print(f"Total Return: {portfolio.total_return():.2f}")
    print(f"Sharpe Ratio: {portfolio.sharpe_ratio():.2f}")
    print(f"Max Drawdown: {portfolio.max_drawdown():.2f}")
    print(f"Annual Volatility: {portfolio.annualized_volatility():.2f}")

    # To see individual asset performance, we can also plot the normalized prices
    normalized_data.plot(title='Individual Asset Performance (Normalized)', figsize=(12, 6))
    return (
        data,
        end_date,
        fig,
        normalized_data,
        np,
        portfolio,
        portfolio_value,
        returns,
        start_date,
        symbol,
        symbols,
        temp,
        weights,
        yf,
    )


@app.cell
def _(fig):
    fig
    return


@app.cell
def _(data):
    data
    return


@app.cell
def _(pd, vbt, yf):
    #import yfinance as yf
    #import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    #import vectorbt as vbt
    import talib as ta
    #import numpy as np

    # Stocks to download
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]
    start_date = "2020-01-01"
    end_date = "2024-01-01"

    def download_and_save_data(tickers, start_date, end_date, filename="stock_data.parquet"):
        """Downloads stock data and saves it to a parquet file."""
        dfs = []
        for ticker in tickers:
            try:
                df = yf.download(ticker, start=start_date, end=end_date)
                if not df.empty:  # Check if data was downloaded successfully
                    df['Ticker'] = ticker  # Add a ticker column
                    dfs.append(df)
                else:
                    print(f"No data found for {ticker}")
            except Exception as e:
                print(f"Error downloading {ticker}: {e}")

        if dfs: # Check if any data was downloaded
            combined_df = pd.concat(dfs)
            table = pa.Table.from_pandas(combined_df)
            pq.write_table(table, filename)
            print(f"Data saved to {filename}")
        else:
            print("No data was downloaded. Parquet file not created.")

    def backtest_from_parquet(filename="stock_data.parquet"):
        """Reads data from parquet and performs backtesting."""
        table = pq.read_table(filename)
        df = table.to_pandas()
        df = df.set_index(['Ticker', df.index]) # MultiIndex for vectorbt

        # Calculate indicators
        close = df['Close'].unstack(level=0) # Unstack tickers to columns
        macd, macdsignal, macdhist = ta.MACD(close)
        rsi = ta.RSI(close)
        obv = ta.OBV(close, close)
        slowk, slowd = ta.STOCH(close.values, close.values, close.values) # Needs numpy arrays

        # Vectorbt backtesting
        entries = (
            (macd > macdsignal) & (rsi < 70) & (slowk < 80)
        )
        exits = (
            (macd < macdsignal) | (rsi > 30) | (slowk > 20)
        )

        pf = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            freq='1D',
            fees=0.001,
            slippage=0.001,
            init_cash=10000
        )

        print(pf.stats())
        pf.plot().show()

    # Run the functions
    download_and_save_data(tickers, start_date, end_date)
    backtest_from_parquet()
    return (
        backtest_from_parquet,
        download_and_save_data,
        end_date,
        pa,
        pq,
        start_date,
        ta,
        tickers,
    )


if __name__ == "__main__":
    app.run()
