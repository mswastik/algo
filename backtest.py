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
from strategies.macd import main

import optuna

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
        best_params=''
        if optimize:
            best_params = self.optimize_strategy()
            signals = strategy(self.data, short_window=best_params['short_window'], long_window=best_params['long_window'])
        else:
            signals = strategy(self.data)

        # Reset tracking variables
        self.capital = self.initial_capital
        self.positions = 0
        self.shares = 0
        self.short_shares = 0
        self.portfolio_values = [self.initial_capital]
        self.trades = []
        self.equity = []

        close_prices = self.data['close'].to_list()
        open_prices = self.data['open'].to_list()
        
        # Iterate through data points
        for i in range(0, len(self.data)):
            # Get current price data
            current_price = close_prices[i]
            prev_price = close_prices[i-1]
            open_price = open_prices[i]

            # Check for trade signal
            if signals[i] != 0 and signals[i] != self.positions:
                if signals[i] == 1:  # Buy signal
                    # Calculate number of shares we can buy with current capital
                    #self.shares = self.capital // current_price #By default backtesting.py considers trades 
                                                                #in opening of next candle so changed logic to below
                    #cost = self.shares * current_price
                    self.shares = self.capital // open_price
                    cost = self.shares * open_price
                    self.capital -= cost
                    
                elif signals[i] == -1:  # Sell signal
                    if self.shares > 0:
                        # Close long position
                        #proceeds = self.shares * current_price
                        proceeds = self.shares * open_price
                        self.capital += proceeds
                        print(proceeds, current_price, open_price)
                        self.shares = 0
                    else:
                        # Initiate short position
                        self.short_shares = self.capital // current_price
                        proceeds = self.short_shares * current_price
                        self.capital += proceeds
                #print(self.capital)
                    
                # Record trade
                self.trades.append({
                    'date': self.data['date'][i],
                    'type': 'buy' if signals[i] == 1 else 'sell',
                    'price': open_price,
                    'shares': self.shares if signals[i] == 1 else self.short_shares,
                    'capital': self.capital,
                    'profit_loss': 0,
                    'cum_profit': 0
                })
                if len(self.trades) > 1:
                    prev_trade = self.trades[-2]
                    if prev_trade['type'] == 'buy' and signals[i] == -1:
                        self.trades[-1]['profit_loss'] = (open_price - prev_trade['price']) * prev_trade['shares']
                        self.trades[-1]['cum_profit'] = sum([i['profit_loss'] for i in self.trades])
                    elif prev_trade['type'] == 'sell' and signals[i] == 1:
                        self.trades[-1]['profit_loss'] = (prev_trade['price'] - open_price) * prev_trade['shares']
                        #sself.equity.append(self.capital+self.trades[i]['profit_loss'])
                        self.trades[-1]['cum_profit'] = sum([i['profit_loss'] for i in self.trades])
                # Update positions
                self.positions = signals[i]

            # Calculate total portfolio value (capital + stock value)
            stock_value = self.shares * current_price
            short_value = self.short_shares * current_price
            portfolio_value = self.capital + stock_value - short_value
            self.portfolio_values.append(portfolio_value)
        print(self.equity)
        # Calculate performance metrics using Polars
        portfolio_series = pl.Series("value", self.portfolio_values)
        returns = portfolio_series.pct_change()

        # Calculate total profit/loss from trades
        total_profit_loss = sum(trade['profit_loss'] for trade in self.trades)
        trdf=pl.DataFrame(self.trades)
        print(trdf.to_pandas().to_string())
        self.data=self.data.join(trdf,on='date',how='left')
        print(self.data['profit_loss'].sum())
        # Calculate total return based on profit/loss
        total_return = (total_profit_loss / self.initial_capital) * 100
        #total_return = (equity[-1]-equity[0])/equity[0]*100
        # Calculate performance metrics using Polars
        portfolio_series = pl.Series("value", self.portfolio_values)
        returns = portfolio_series.pct_change()

        # Calculate buy and hold returns
        buy_and_hold_return = (close_prices[-1] / close_prices[0] - 1) * 100

        metrics = {
            'Total Return': (self.portfolio_values[-1] / self.initial_capital - 1) * 100,
            'Total Return test': total_return,
            'Annual Return': ((self.portfolio_values[-1] / self.initial_capital) **
                            (252 / len(self.data)) - 1) * 100,
            'Sharpe Ratio': np.sqrt(252) * returns.mean() / returns.std(),
            'Max Drawdown': self._calculate_max_drawdown(),
            'Num Trades': len(self.trades),
            'Buy&Hold Return': buy_and_hold_return,
            'Best Params': best_params
        }

        return metrics, self.visualize_results()

    #def _run_strategy(self, data: pl.DataFrame, strategy: Callable[[pl.DataFrame, int, int], List[int]], short_window: int, long_window: int) -> List[int]:
    #    return strategy(data, short_window, long_window)

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
        fig = make_subplots(rows=3, cols=2, shared_xaxes=True,vertical_spacing=0.05,horizontal_spacing=.07,row_heights=[0.5, 0.3, 0.2],column_widths=[.65,.35],
                        subplot_titles=('Price and Portfolio Value','Strategy Returns','Trading Signals','Trade Types','Monthly Returns','Cumulative Returns'),
                         specs=[[{"secondary_y": True},{"secondary_y": False}],[{"secondary_y": False},{"secondary_y": False}],[{"secondary_y": False},{"secondary_y": False}]])

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
                          marker=dict(symbol=symbol,color=color,size=15),showlegend=False),row=1, col=1)
        # Add drawdown
        portfolio_series = pl.Series("value", self.portfolio_values)
        rolling_max = portfolio_series.cum_max()
        drawdown = (portfolio_series / rolling_max - 1) * 100
        fig.add_trace(go.Scatter(x=dates,y=drawdown.to_list(),name='Drawdown',fill='tozeroy',line=dict(color='red')),row=3, col=1)
        t1,t2,t3=self.generate_trade_analysis()
        fig.add_trace(t1,row=1,col=2)
        fig.add_trace(t2,row=2,col=2)
        fig.add_trace(t3,row=3,col=2)
        # Update layout
        fig.update_layout(height=800,width=1600, showlegend=True,legend=dict(yanchor="top",y=1.1, xanchor="left",x=0.01,
                        bgcolor='rgba(255,255,255,0)',orientation="h"))
        # Update y-axes labels
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Returns %", row=2, col=1)
        fig.update_yaxes(title_text="Drawdown %", row=3, col=1)
        return fig.to_html(full_html=False)

    def generate_trade_analysis(self) -> go.Figure:
        """
        Generate detailed trade analysis visualization
        """
        # Calculate trade metrics
        win_trades = [t for t in self.trades if t['type'] == 'buy']
        loss_trades = [t for t in self.trades if t['type'] == 'sell']
        # Create figure
        #fig = make_subplots(rows=3, cols=1, subplot_titles=('Trade Distribution', 'Trade Timing','Monthly Returns','Cumulative Returns'))
        # Plot 1: Trade Distribution
        #fig.add_trace(go.Bar(x=['Buy', 'Sell'],y=[len(win_trades), len(loss_trades)], name='Trade Types'),row=1, col=1)
        t1=go.Bar(x=['Buy', 'Sell'],y=[len(win_trades), len(loss_trades)], name='Trade Types')
        # Plot 3: Monthly Returns
        returns = pl.Series(self.portfolio_values).pct_change()
        monthly_returns = pl.Series(self.portfolio_values).pct_change().to_list()
        #fig.add_trace(go.Box(y=monthly_returns,name='Monthly Returns'), row=2, col=1)
        t2=go.Box(y=monthly_returns,name='Monthly Returns')
        # Plot 4: Cumulative Returns
        #cumulative_returns = np.cumprod(1 + pl.Series(self.portfolio_values).pct_change().to_list()) - 1
        returns_array = np.array([x for x in returns.to_list() if x is not None])  # Remove None values
        cumulative_returns = np.cumprod(1 + returns_array) - 1
        dates = self.data['date'].to_list()[1:] 
        #fig.add_trace(go.Scatter(x=self.data['date'].to_list(),y=cumulative_returns,name='Cumulative Returns',fill='tozeroy'),row=3, col=1)
        t3=go.Scatter(x=self.data['date'].to_list(),y=cumulative_returns,name='Cumulative Returns',fill='tozeroy')
        # Update layout
        #fig.update_layout(height=800,title_text="Detailed Trade Analysis",showlegend=False)
        return t1,t2,t3
    def returns_strategy(self,data: pl.DataFrame, short_window: int=30, long_window: int=200) -> float:
        """
        Applies the simple moving average strategy and calculates the total return.

        Parameters:
        data: Price data DataFrame
        short_window: Short-term moving average period
        long_window: Long-term moving average period
        
        Returns:
        Total return
        """
        data=self.data
        signals = main(data, short_window, long_window)
        
        # Calculate total return
        initial_capital = 100000.0
        capital = initial_capital
        positions = 0
        shares = 0
        close_prices = data['close'].to_list()
        open_prices = data['open'].to_list()

        for i in range(1, len(data)):
            current_price = close_prices[i]
            open_price = open_prices[i]
            if signals[i] != 0 and signals[i] != positions:
                if signals[i] == 1:
                    shares = capital // open_price
                    cost = shares * current_price
                    capital -= cost
                elif signals[i] == -1:
                    proceeds = shares * current_price
                    capital += proceeds
                    shares = 0
                positions = signals[i]
        
        stock_value = shares * close_prices[-1]
        portfolio_value = capital + stock_value
        total_return = (portfolio_value / initial_capital - 1) * 100
        return total_return

    def optimize_strategy(self, n_trials: int = 30) -> dict:
        """
        Optimizes the simple moving average strategy using Optuna.

        Parameters:
        data: Price data DataFrame
        n_trials: Number of optimization trials

        Returns:
        Dictionary of optimized parameters
        """
        data=self.data
        def objective(trial):
            short_window = trial.suggest_int('short_window', 10, 50)
            long_window = trial.suggest_int('long_window', 50, 200)
            #total_return = obf(data, short_window=short_window, long_window=long_window)
            return self.returns_strategy(data,short_window=short_window, long_window=long_window)
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, n_jobs=-1)
        return study.best_params

    def calculate_annual_return(signals, data):
        # Calculate annual return based on signals and data
        # This is a simplified example and actual implementation may vary
        
        annual_return = 0
        for i in range(len(signals)):
            if signals[i] == 1:
                annual_return += data['close'][i]
            elif signals[i] == -1:
                annual_return -= data['close'][i]
        return annual_return
