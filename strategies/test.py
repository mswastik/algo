import polars as pl
import talib as ta
from typing import List

def main(data: pl.DataFrame, short_window: int = 30, long_window: int = 100) -> List[int]:
    """
    Example strategy using moving average crossover
    Parameters:
    data: Price data DataFrame
    short_window: Short-term moving average period
    long_window: Long-term moving average period
    
    Returns:
    List of position signals
    """
    #stk, std = ta.STOCH(data['high'],data['low'],data['close'])
    #obv = ta.OBV(data['close'],data['volume'])
    #obv_sma = obv.rolling_mean(window_size=6)
    #obv=obv.to_list()
    #obv_sma=obv_sma.to_list()
    #stk=stk.to_list()
    #std=std.to_list()
    
    signals = [0] * len(data)
    
    # Calculate moving averages using Polars
    short_ma = data.select([pl.col("close").rolling_mean(window_size=short_window)]).to_series()
    long_ma = data.select([pl.col("close").rolling_mean(window_size=long_window)]).to_series()
    #short_ma = data.select([pl.col("close").ewm_mean(min_periods=short_window,span=short_window)]).to_series()
    #long_ma = data.select([pl.col("close").ewm_mean(min_periods=long_window,span=long_window)]).to_series()
    
    # Convert to lists for faster iteration
    short_ma_list = short_ma.to_list()
    long_ma_list = long_ma.to_list()
    
    # Generate signals
    for i in range(long_window, len(data)):
        if (short_ma_list[i] > long_ma_list[i] and 
            short_ma_list[i-1] <= long_ma_list[i-1]):
            signals[i] = 1  # Buy signal
        elif (short_ma_list[i] < long_ma_list[i] and 
              short_ma_list[i-1] >= long_ma_list[i-1]):
            signals[i] = -1  # Sell signal
    return signals