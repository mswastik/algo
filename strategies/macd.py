import talib as tl
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import numpy as np
import pandas as pd
import polars as pl
#dd=pd.DataFrame()

def ta_MACD(df):
    return tl.MACD(df,fastperiod=10,slowperiod=20,signalperiod=6)

def ta_OBV(close,vol):
    return tl.OBV(close,vol)

def ta_stoch(high,low,close):
    return tl.STOCH(high,low,close)

class MACD(Strategy):
    def init(self):
        high = np.array([float(x) for x in self.data['High']])
        low = np.array([float(x) for x in self.data['Low']])
        close = np.array([float(x) for x in self.data['Close']])
        vol = np.array([float(x) for x in self.data['Volume']])
        self.macd, self.sig, self.hist =self.I(ta_MACD, close)
        #self.sma2 = tl.SMA(df['Close'],timeperiod=60)
        self.obv = self.I(ta_OBV,close,vol)
        self.stoch = self.I(ta_stoch,high,low,close)
        #a.dd=pd.DataFrame({'macd':self.macd,'sig':self.sig,'hist':self.hist})
    def next(self):
        if crossover(self.macd, self.sig) and self.stoch<30:
            self.buy()
        elif crossover(self.sig, self.macd):
            try:
                #print(self.closed_trades[-1].entry_price)
                pinc=(self.data.Close[-1]-self.closed_trades[-1].entry_price)/self.closed_trades[-1].entry_price
                if pinc>.25:
                    #self.sell()
                    self.position.close()
            except:
                pass
def main(df):
    desc=""
    #df1=fd.filter(pl.col('symbol')==sym.value).filter(pl.col('epoch')>=dt.date(2021,9,9)).drop('symbol').sort('epoch',descending=False)
    df=df.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    df=df.to_pandas()
    df=df.sort_values('epoch',ascending=True)
    df.set_index('epoch',inplace=True)
    bt = Backtest(df, MACD, cash= 100000,exclusive_orders=True)
    stats = bt.run()
    #bt.plot(plot_return=False,open_browser=False)
    return bt,stats