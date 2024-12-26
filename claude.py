from fyers_api.websocket import websocket
from fyers_api import fyersModel
import vectorbt as vbt
import pandas as pd
import numpy as np
import asyncio
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

class FyersRealTimeTrading:
    def __init__(self, config_path: str = 'fyers_config.json'):
        """Initialize Fyers trading system"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.fyers = self._initialize_fyers()
        self.ws = None
        self.data_buffer = {}
        self.active_positions = {}
        self.orders = {}
        
    def _load_config(self, config_path: str) -> dict:
        """Load Fyers configuration"""
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                required_fields = ['client_id', 'access_token', 'symbols', 'risk_per_trade']
                if not all(field in config for field in required_fields):
                    raise ValueError("Missing required configuration fields")
                return config
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            raise
    
    def _initialize_fyers(self) -> fyersModel.FyersModel:
        """Initialize Fyers API connection"""
        try:
            fyers = fyersModel.FyersModel(
                client_id=self.config['client_id'],
                token=self.config['access_token'],
                log_path="logs"
            )
            self.logger.info("Fyers API initialized successfully")
            return fyers
        except Exception as e:
            self.logger.error(f"Error initializing Fyers API: {str(e)}")
            raise

    async def connect_websocket(self):
        """Establish websocket connection"""
        try:
            self.ws = websocket.FyersSocket(
                access_token=f"{self.config['client_id']}:{self.config['access_token']}",
                log_path="logs",
                websocket_client_instance=None
            )
            
            # Define callback for data handling
            def on_message(message):
                self._process_market_data(message)
            
            self.ws.on_message = on_message
            await self.ws.connect()
            
            # Subscribe to symbols
            symbols = [{"symbol": symbol, "dataType": "symbolData"} 
                      for symbol in self.config['symbols']]
            await self.ws.subscribe(symbols=symbols)
            
            self.logger.info("WebSocket connection established")
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
            raise

    def _process_market_data(self, message: dict):
        """Process incoming market data"""
        try:
            symbol = message['symbol']
            
            # Update data buffer
            if symbol not in self.data_buffer:
                self.data_buffer[symbol] = []
            
            self.data_buffer[symbol].append({
                'timestamp': message['timestamp'],
                'price': message['ltp'],
                'volume': message['volume']
            })
            
            # Keep only recent data
            self.data_buffer[symbol] = self.data_buffer[symbol][-1000:]
            
            # Run strategy check
            self._check_signals(symbol)
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")

    def _check_signals(self, symbol: str):
        """Check for trading signals"""
        try:
            # Convert buffer to DataFrame
            df = pd.DataFrame(self.data_buffer[symbol])
            df.set_index('timestamp', inplace=True)
            
            # Run strategy (example using dual MA crossover)
            fast_ma = vbt.MA.run(df['price'], window=self.config['fast_ma'])
            slow_ma = vbt.MA.run(df['price'], window=self.config['slow_ma'])
            
            # Generate signals
            if len(df) > self.config['slow_ma']:
                if fast_ma.ma_crossed_above(slow_ma)[-1]:
                    self._place_order(symbol, 'BUY')
                elif fast_ma.ma_crossed_below(slow_ma)[-1]:
                    self._place_order(symbol, 'SELL')
                    
        except Exception as e:
            self.logger.error(f"Error checking signals: {str(e)}")

    def _calculate_position_size(self, symbol: str, price: float) -> int:
        """Calculate position size based on risk management"""
        try:
            account_value = float(self.fyers.get_funds()['fund_limit'][0]['equityAmount'])
            risk_amount = account_value * self.config['risk_per_trade']
            position_size = int(risk_amount / price)
            return position_size
        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            return 0

    async def _place_order(self, symbol: str, side: str):
        """Place order with Fyers"""
        try:
            current_price = self.data_buffer[symbol][-1]['price']
            position_size = self._calculate_position_size(symbol, current_price)
            
            if position_size == 0:
                self.logger.warning("Position size calculation returned 0")
                return
            
            # Check if we already have a position
            if symbol in self.active_positions:
                if self.active_positions[symbol]['side'] != side:
                    # Close existing position
                    await self._close_position(symbol)
                else:
                    return  # Already in desired position
            
            # Calculate stop loss and target
            stop_loss = current_price * (0.98 if side == 'BUY' else 1.02)
            target = current_price * (1.03 if side == 'BUY' else 0.97)
            
            # Place main order
            order_params = {
                "symbol": symbol,
                "qty": position_size,
                "type": 2,  # Market order
                "side": 1 if side == 'BUY' else -1,
                "productType": "INTRADAY",
                "stopLoss": stop_loss,
                "target": target
            }
            
            response = self.fyers.place_order(order_params)
            
            if response['s'] == 'ok':
                order_id = response['id']
                self.orders[order_id] = {
                    'symbol': symbol,
                    'side': side,
                    'size': position_size,
                    'price': current_price,
                    'stop_loss': stop_loss,
                    'target': target
                }
                
                self.active_positions[symbol] = {
                    'side': side,
                    'size': position_size,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'target': target
                }
                
                self.logger.info(f"Order placed successfully: {order_id}")
            else:
                self.logger.error(f"Order placement failed: {response}")
                
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")

    async def _close_position(self, symbol: str):
        """Close existing position"""
        try:
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                
                order_params = {
                    "symbol": symbol,
                    "qty": position['size'],
                    "type": 2,  # Market order
                    "side": -1 if position['side'] == 'BUY' else 1,
                    "productType": "INTRADAY"
                }
                
                response = self.fyers.place_order(order_params)
                
                if response['s'] == 'ok':
                    del self.active_positions[symbol]
                    self.logger.info(f"Position closed for {symbol}")
                else:
                    self.logger.error(f"Position closure failed: {response}")
                    
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")

    async def _monitor_positions(self):
        """Monitor active positions for stop loss and target"""
        while True:
            try:
                for symbol, position in self.active_positions.items():
                    current_price = self.data_buffer[symbol][-1]['price']
                    
                    # Check stop loss
                    if (position['side'] == 'BUY' and current_price <= position['stop_loss']) or \
                       (position['side'] == 'SELL' and current_price >= position['stop_loss']):
                        await self._close_position(symbol)
                        self.logger.info(f"Stop loss triggered for {symbol}")
                    
                    # Check target
                    elif (position['side'] == 'BUY' and current_price >= position['target']) or \
                         (position['side'] == 'SELL' and current_price <= position['target']):
                        await self._close_position(symbol)
                        self.logger.info(f"Target reached for {symbol}")
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {str(e)}")
                await asyncio.sleep(1)

    async def start_trading(self):
        """Start real-time trading"""
        try:
            # Connect to websocket
            await self.connect_websocket()
            
            # Start position monitoring
            monitor_task = asyncio.create_task(self._monitor_positions())
            
            # Keep the main loop running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in trading loop: {str(e)}")
        finally:
            if self.ws:
                await self.ws.close()

# Example usage
if __name__ == "__main__":
    # Create configuration file (fyers_config.json)
    config = {
        "client_id": "your_client_id",
        "access_token": "your_access_token",
        "symbols": ["NSE:NIFTY-INDEX", "NSE:BANKNIFTY-INDEX"],
        "risk_per_trade": 0.02,
        "fast_ma": 20,
        "slow_ma": 50
    }
    
    # Initialize and start trading
    async def main():
        trader = FyersRealTimeTrading()
        await trader.start_trading()
    
    asyncio.run(main())