import polars as pl
import talib as ta
from typing import List
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, cross
from pyecharts.charts import Bar, Candlestick, Kline
from pyecharts import options as opts
import plotly.io as pio

pio.templates.default = "plotly_white"

class MACDStrategy(Strategy):
    fastperiod = 10 
    slowperiod = 150
    signalperiod = 6
    def init(self):
        print(self.data['Close'])
        price = self.data['Close']
        self.macd, self.sig, self.hist =self.I(ta.MACD, np.array([float(i) for i in self.data['Close']]), self.fastperiod, self.slowperiod, self.signalperiod)
    def next(self):
        if cross(self.macd, self.sig):
            if self.position:
                self.position.close()
            else:
                self.buy(size=.9999)
        elif cross(self.sig, self.macd):
            if self.position:
                self.position.close()
            else:
                self.sell()

def main(df):
    bt = Backtest(df, MACDStrategy, cash= 100000,exclusive_orders=True,trade_on_close=False,)
    stats = bt.run()
    return stats

def optimize(df):
    bt = Backtest(df, MACDStrategy, cash= 100000,exclusive_orders=True,trade_on_close=False,)
    stats = bt.optimize(fastperiod=[10,20,30,40,50],slowperiod=range(60,200,5), maximize='Return (Ann.) [%]',method='skopt',return_optimization=True)
    #t1=go.Bar(x=['Buy', 'Sell'],y=[len(win_trades), len(loss_trades)], name='Trade Types')
    # Plot 3: Monthly Returns
    #returns = pl.Series(self.portfolio_values).pct_change()
    #monthly_returns = pl.Series(self.portfolio_values).pct_change().to_list()
    #fig.add_trace(go.Box(y=monthly_returns,name='Monthly Returns'), row=2, col=1)
    #t2=go.Box(y=monthly_returns,name='Monthly Returns')
    # Plot 4: Cumulative Returns
    #cumulative_returns = np.cumprod(1 + pl.Series(self.portfolio_values).pct_change().to_list()) - 1
    #returns_array = np.array([x for x in returns.to_list() if x is not None])  # Remove None values
    #cumulative_returns = np.cumprod(1 + returns_array) - 1
    #dates = self.data['date'].to_list()[1:] 
    #fig.add_trace(go.Scatter(x=self.data['date'].to_list(),y=cumulative_returns,name='Cumulative Returns',fill='tozeroy'),row=3, col=1)
    #t3=go.Scatter(x=self.data['date'].to_list(),y=cumulative_returns,name='Cumulative Returns',fill='tozeroy')
    # Update layout
    #fig.update_layout(height=800,title_text="Detailed Trade Analysis",showlegend=False)
    return stats