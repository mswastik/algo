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
    macd, sig, hist = ta.MACD(data['close'],fastperiod=30,slowperiod=100,signalperiod=6,)
    macd=macd.to_list()
    sig=sig.to_list()
    
    signals = [0] * len(data)
    
    
    # Generate signals
    for i in range(long_window, len(data)):
        if (macd[i] > sig[i] and 
            macd[i-1] < sig[i-1]):
            signals[i+1] = 1  # Buy signal
        elif (macd[i] < sig[i] and 
              macd[i-1] > sig[i-1]):
            signals[i+1] = -1  # Sell signal
    return signals