import polars as pl
import talib as ta
from typing import List
import optuna
import time

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

def apply_strategy(data: pl.DataFrame, short_window: int = 30, long_window: int = 100) -> float:
    """
    Applies the simple moving average strategy and calculates the annual return.

    Parameters:
    data: Price data DataFrame
    short_window: Short-term moving average period
    long_window: Long-term moving average period
    
    Returns:
    Annual return
    """
    signals = simple_moving_average_strategy(data, short_window, long_window)
    annual_return = calculate_annual_return(signals, data)
    return signals

def optimize_strategy(data: pl.DataFrame, n_trials: int = 10) -> dict:
    """
    Optimizes the simple moving average strategy using Optuna.

    Parameters:
    data: Price data DataFrame
    n_trials: Number of optimization trials

    Returns:
    Dictionary of optimized parameters
    """
    def objective(trial):
        short_window = trial.suggest_int('short_window', 10, 50)
        long_window = trial.suggest_int('long_window', 50, 200)
        annual_return = apply_strategy(data, short_window=short_window, long_window=long_window)
        return annual_return

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)
    
    return study.best_params
