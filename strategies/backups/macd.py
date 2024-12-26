import talib as tl
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import numpy as np
import pandas as pd
import polars as pl
import optuna

#dd=pd.DataFrame()

def ta_MACD(df, fastperiod=10, slowperiod=20, signalperiod=6):
    return tl.MACD(df, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)

def ta_OBV(close, vol):
    return tl.OBV(close, vol)

def ta_stoch(high, low, close):
    return tl.STOCH(high, low, close)

class MACD(Strategy):
    short_window = 10
    long_window = 20

    def init(self):
        high = np.array([float(x) for x in self.data['High']])
        low = np.array([float(x) for x in self.data['Low']])
        close = np.array([float(x) for x in self.data['Close']])
        vol = np.array([float(x) for x in self.data['Volume']])
        self.macd, self.sig, self.hist = self.I(ta_MACD, close, fastperiod=self.short_window, slowperiod=self.long_window)
        self.obv = self.I(ta_OBV, close, vol)
        self.stoch = self.I(ta_stoch, high, low, close)

    def next(self):
        if crossover(self.macd, self.sig) and self.stoch < 30:
            self.buy()
        elif crossover(self.sig, self.macd):
            try:
                pinc = (self.data.Close[-1] - self.closed_trades[-1].entry_price) / self.closed_trades[-1].entry_price
                if pinc > .25:
                    self.position.close()
            except IndexError:
                pass

def optimize_strategy(df):
    def objective(trial):
        short_window = trial.suggest_int('short_window', 5, 50)
        long_window = trial.suggest_int('long_window', 20, 100)
        
        df_copy = df.copy()
        bt = Backtest(df_copy, MACD, cash=100000, exclusive_orders=True, commission=.002)
        try:
            stats = bt.run()
            return stats['Return [%]']
        except Exception as e:
            print(f"Trial failed with exception: {e}")
            return -float('inf')  # Return negative infinity for failed trials

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=10)
    if study.trials and study.best_trial:
        best_params = study.best_params
        print(f"Best parameters: {best_params}")
        return best_params
    else:
        return None

def apply_strategy(df, short_window=None, long_window=None):
    df = df.rename({'open': "Open", 'high': 'High', 'low': 'Low', 'close': "Close", 'volume': 'Volume'})
    df = df.to_pandas()
    df = df.sort_values('epoch', ascending=True)
    df.set_index('epoch', inplace=True)
    
    # Use optimized parameters if provided, otherwise use default
    if short_window and long_window:
        MACD.short_window = short_window
        MACD.long_window = long_window
    
    bt = Backtest(df, MACD, cash=100000, exclusive_orders=True, commission=.002)
    stats = bt.run()
    return stats

def main(df):
    return apply_strategy(df)
'''
if __name__ == '__main__':
    # Example usage with a sample DataFrame (replace with your actual data)
    data = {'epoch': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']),
            'open': [100, 102, 105, 103, 106],
            'high': [103, 106, 107, 105, 108],
            'low': [99, 101, 104, 102, 105],
            'close': [102, 105, 103, 106, 107],
            'volume': [1000, 1200, 1100, 1300, 1400]}
    sample_df = pl.DataFrame(data)
    
    # Run optimization
    best_params = optimize_strategy(sample_df)
    
    # Run backtest with optimized parameters
    bt_optimized, stats_optimized = apply_strategy(sample_df, **best_params)
    print("Backtest with optimized parameters:")
    print(stats_optimized)

    # Run backtest with default parameters
    bt_default, stats_default = apply_strategy(sample_df)
    print("Backtest with default parameters:")
    print(stats_default)
'''