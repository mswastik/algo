import talib as tl
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import numpy as np
import pandas as pd
#dd=pd.DataFrame()

def ta_MACD(df):
    ""
    return tl.MACD(df,fastperiod=10,slowperiod=20,signalperiod=6)

class MACD(Strategy):
    def init(self):
        price = self.data['Close']
        self.macd, self.sig, self.hist =self.I(ta_MACD, df1['Close'])
        #self.sma2 = tl.SMA(df['Close'],timeperiod=60)
        a.dd=pd.DataFrame({'macd':self.macd,'sig':self.sig,'hist':self.hist})
    def next(self):
        if crossover(self.macd, self.sig):
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
df1=fd.filter(pl.col('symbol')==sym.value).filter(pl.col('epoch')>=dt.date(2021,9,9)).drop('symbol').sort('epoch',descending=False)
df1=df1.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
df1=df1.to_pandas()
df1.set_index('epoch',inplace=True)
bt = Backtest(df1, MACD,cash= 100000,exclusive_orders=True)
stats = bt.run()
bt.plot(plot_return=False,)