import polars as pl
import numpy as np
from typing import List, Dict, Callable
import time
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import plotly.io as pio
pio.templates.default = "plotly_white"
import talib as ta
from strategies.test import optimize_strategy, simple_moving_average_strategy
#from test import *

class Backtester:
    def __init__(self, data: pl.DataFrame, initial_capital: float = 100000.0):
        """
        Initialize backtester with historical price data and starting capital
        
        Parameters:
        data: Polars DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume']
        initial_capital: Starting portfolio value
        """
        self.data = data.sort('date')
        self.initial_capital = initial_capital
        self.positions = 0
        self.capital = initial_capital
        self.portfolio_values = []
        self.trades = []

    def apply_strategy(self, strategy: Callable[[pl.DataFrame, int, int], List[int]], optimize: bool = False) -> Dict:
        """
        Run backtest using provided strategy function, with optional optimization
        """
        if optimize:
            best_params = optimize_strategy(self.data, lambda data, short_window, long_window: self._run_strategy(data, strategy, short_window, long_window))
            signals = strategy(self.data, short_window=best_params['short_window'], long_window=best_params['long_window'])
        else:
            signals = strategy(self.data)

        # Reset tracking variables
        self.capital = self.initial_capital
        self.positions = 0
        self.shares = 0
        self.portfolio_values = [self.initial_capital]
        self.trades = []

        close_prices = self.data['close'].to_list()

        # Iterate through data points
        for i in range(1, len(self.data)):
            # Get current price data
            current_price = close_prices[i]
            prev_price = close_prices[i-1]

            # Check for trade signal
            if signals[i] != 0 and signals[i] != self.positions:
                if signals[i] == 1:  # Buy signal
                    # Calculate number of shares we can buy with current capital
                    self.shares = self.capital // current_price
                    cost = self.shares * current_price
                    self.capital -= cost

                elif signals[i] == -1:  # Sell signal
                    # Add proceeds from sale to capital
                    proceeds = self.shares * current_price
                    self.capital += proceeds
                    self.shares = 0

                # Record trade
                self.trades.append({
                    'date': self.data['date'][i],
                    'type': 'buy' if signals[i] == 1 else 'sell',
                    'price': current_price,
                    'shares': self.shares if signals[i] == 1 else 0,
                    'capital': self.capital
                })

                # Update positions
                self.positions = signals[i]

            # Calculate total portfolio value (capital + stock value)
            stock_value = self.shares * current_price
            portfolio_value = self.capital + stock_value
            self.portfolio_values.append(portfolio_value)

        # Calculate performance metrics using Polars
        portfolio_series = pl.Series("value", self.portfolio_values)
        returns = portfolio_series.pct_change()

        # Calculate buy and hold returns
        buy_and_hold_return = (close_prices[-1] / close_prices[0] - 1) * 100

        metrics = {
            'total_return': (self.portfolio_values[-1] / self.initial_capital - 1) * 100,
            'annual_return': ((self.portfolio_values[-1] / self.initial_capital) **
                            (252 / len(self.data)) - 1) * 100,
            'sharpe_ratio': np.sqrt(252) * returns.mean() / returns.std(),
            'max_drawdown': self._calculate_max_drawdown(),
            'num_trades': len(self.trades),
            'buy_and_hold_return': buy_and_hold_return
        }

        return metrics

    def _run_strategy(self, data: pl.DataFrame, strategy: Callable[[pl.DataFrame, int, int], List[int]], short_window: int, long_window: int) -> List[int]:
        return strategy(data, short_window, long_window)
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage"""
        portfolio_series = pl.Series("value", self.portfolio_values)
        rolling_max = portfolio_series.cum_max()
        drawdowns = (portfolio_series / rolling_max - 1) * 100
        return drawdowns.min()
    def visualize_results(self) -> None:
        """
        Create interactive visualizations of backtest results using Plotly
        """
        # Create figure with secondary y-axis
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,vertical_spacing=0.05,row_heights=[0.5, 0.3, 0.2],subplot_titles=('Price and Portfolio Value', 
                                         'Strategy Returns','Trading Signals'),specs=[[{"secondary_y": True}],[{"secondary_y": False}],[{"secondary_y": False}]])

        # Plot 1: Price and Portfolio Value
        dates = self.data['date'].to_list()
        
        # Add price line
        fig.add_trace(go.Scatter(x=dates, y=self.data['close'].to_list(),name='Stock Price',line=dict(color='blue')),row=1, col=1)
        
        # Add portfolio value line
        fig.add_trace(go.Scatter(x=dates, y=self.portfolio_values, name='Portfolio Value',line=dict(color='green')),secondary_y=True,row=1, col=1)
        
        # Plot 2: Returns
        portfolio_returns = pl.Series(self.portfolio_values).pct_change().to_list()
        fig.add_trace(go.Scatter(x=dates, y=portfolio_returns, name='Returns',fill='tozeroy',line=dict(color='purple')),row=2, col=1)
        
        # Plot 3: Trading Signals
        for trade in self.trades:
            color = 'green' if trade['type'] == 'buy' else 'red'
            symbol = 'triangle-up' if trade['type'] == 'buy' else 'triangle-down'
            
            fig.add_trace(go.Scatter(x=[trade['date']],y=[trade['price']],mode='markers',name=trade['type'].capitalize(),
                          marker=dict(symbol=symbol,color=color,size=15)),row=1, col=1)

        # Add drawdown
        portfolio_series = pl.Series("value", self.portfolio_values)
        rolling_max = portfolio_series.cum_max()
        drawdown = (portfolio_series / rolling_max - 1) * 100
        
        fig.add_trace(go.Scatter(x=dates,y=drawdown.to_list(),name='Drawdown',fill='tozeroy',line=dict(color='red')),row=3, col=1)

        # Update layout
        fig.update_layout(title='Backtest Results',height=1200, showlegend=True,legend=dict(yanchor="top",y=0.99, xanchor="left",x=0.01))

        # Update y-axes labels
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Returns %", row=2, col=1)
        fig.update_yaxes(title_text="Drawdown %", row=3, col=1)

        # Show figure
        fig.show()
        return fig

    def generate_trade_analysis(self) -> go.Figure:
        """
        Generate detailed trade analysis visualization
        """
        # Calculate trade metrics
        win_trades = [t for t in self.trades if t['type'] == 'buy']
        loss_trades = [t for t in self.trades if t['type'] == 'sell']
        
        # Create figure
        fig = make_subplots(rows=2, cols=2, subplot_titles=('Trade Distribution', 'Trade Timing','Monthly Returns','Cumulative Returns'))
        
        # Plot 1: Trade Distribution
        fig.add_trace(go.Bar(x=['Buy', 'Sell'],y=[len(win_trades), len(loss_trades)], name='Trade Types'),row=1, col=1)
        
        # Plot 2: Trade Timing
        #trade_times = [datetime.strptime(str(t['date']), '%Y-%m-%d').hour 
        #              for t in self.trades]
        #fig.add_trace(go.Histogram(x=trade_times,name='Trade Timing', nbinsx=24),row=1, col=2)
        
        # Plot 3: Monthly Returns
        returns = pl.Series(self.portfolio_values).pct_change()
        monthly_returns = pl.Series(self.portfolio_values).pct_change().to_list()
        fig.add_trace(go.Box(y=monthly_returns,name='Monthly Returns'), row=2, col=1)
        
        # Plot 4: Cumulative Returns
        #cumulative_returns = np.cumprod(1 + pl.Series(self.portfolio_values).pct_change().to_list()) - 1
        returns_array = np.array([x for x in returns.to_list() if x is not None])  # Remove None values
        cumulative_returns = np.cumprod(1 + returns_array) - 1
        dates = self.data['date'].to_list()[1:] 
        fig.add_trace(go.Scatter(x=self.data['date'].to_list(),y=cumulative_returns,name='Cumulative Returns',fill='tozeroy'),row=2, col=2)
        # Update layout
        fig.update_layout(height=800,title_text="Detailed Trade Analysis",showlegend=False)
        return fig
'''
def simple_moving_average_strategy(data: pl.DataFrame, short_window: int = 30, long_window: int = 100) -> List[int]:
    """
    Example strategy using moving average crossover
    Parameters:
    data: Price data DataFrame
    short_window: Short-term moving average period
    long_window: Long-term moving average period
    
    Returns:
    List of position signals
    """
    stk, std = ta.STOCH(data['high'],data['low'],data['close'])
    obv = ta.OBV(data['close'],data['volume'])
    obv_sma = obv.rolling_mean(window_size=6)
    obv=obv.to_list()
    obv_sma=obv_sma.to_list()
    stk=stk.to_list()
    std=std.to_list()
    
    signals = [0] * len(data)
    
    # Calculate moving averages using Polars
    short_ma = data.select([pl.col("close").rolling_mean(window_size=short_window)]).to_series()
    long_ma = data.select([pl.col("close").rolling_mean(window_size=long_window)]).to_series()
    
    # Convert to lists for faster iteration
    short_ma_list = short_ma.to_list()
    long_ma_list = long_ma.to_list()
    
    start= time.time()
    # Generate signals
    for i in range(long_window, len(data)):
        if (short_ma_list[i] > long_ma_list[i] and 
            short_ma_list[i-1] <= long_ma_list[i-1] and stk[i]<50):
            signals[i] = 1  # Buy signal
        elif (short_ma_list[i] < long_ma_list[i] and 
              short_ma_list[i-1] >= long_ma_list[i-1] and obv[i]<obv_sma[i]):
            signals[i] = -1  # Sell signal
    print("For loop time : "+str(time.time()-start))
    return signals
'''
'''
plots,trades, results={},{},{}
for sym in ['HDFCBANK','TCS','SBIN']:
    dates = pl.date_range(start=pl.datetime(2020, 1, 1), end=pl.datetime(2024, 10, 31), interval="1d")
    #data=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
    data=pl.read_csv(f'stockdata.csv')
    data=data.filter(pl.col('symbol')==sym)
    data=data.drop('symbol')
    data=data.rename({'epoch':'date'})
    
    # Initialize backtester
    backtester = Backtester(data)
    
    # Run backtest with moving average strategy and optimization
    results[sym] = backtester.apply_strategy(simple_moving_average_strategy, optimize=True)
    plots[sym] = backtester.visualize_results()
    trades[sym]=backtester.generate_trade_analysis()
    print("Backtest Results:")
    for metric, value in results[sym].items():
        print(sym)
        print(f"{metric}: {value:.2f}")
'''
