import time
import threading

class MonitoringSystem:
    def __init__(self, client, check_interval=60, on_event_callback=None):
        """
        Initialize the monitoring system
        
        Parameters:
        - client: BitgetClient instance
        - check_interval: Interval between checks in seconds
        - on_event_callback: Optional function(event_dict) for logging/learning
        """
        self.client = client
        self.check_interval = check_interval  # Seconds between checks
        self.active_trades = {}
        self.running = False
        self.monitor_thread = None
        self.on_event_callback = on_event_callback
    
    def start_monitoring(self):
        """
        Start monitoring active positions
        """
        self.running = True
        self._monitor_thread()
        print("Monitoring system started.")
    
    def stop_monitoring(self):
        """
        Stop monitoring
        """
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        print("Monitoring system stopped.")
    
    def _monitor_thread(self):
        """
        Monitor positions and orders
        """
        def run():
            while self.running:
                try:
                    self.check_positions()
                    self.check_orders()
                except Exception as e:
                    print(f"Error in monitoring: {e}")
                time.sleep(self.check_interval)
        
        self.monitor_thread = threading.Thread(target=run)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def check_positions(self):
        """
        Check current positions and update tracking
        """
        positions = self.client.get_positions()
        
        for position in positions['data']:
            symbol = position['symbol']
            size = float(position['total'])
            if size > 0:
                entry_price = float(position['averageOpenPrice'])
                unrealized_pnl = float(position['unrealizedPL'])
                
                # Update active trades
                if symbol not in self.active_trades:
                    self.active_trades[symbol] = {
                        "entry_price": entry_price,
                        "size": size,
                        "entry_time": time.time()
                    }
                    if self.on_event_callback:
                        self.on_event_callback({
                            "type": "position_open",
                            "symbol": symbol,
                            "entry_price": entry_price,
                            "size": size,
                            "ts": time.time()
                        })
                
                # Calculate current metrics
                duration = time.time() - self.active_trades[symbol]["entry_time"]
                duration_hours = duration / 3600
                
                # Get current price
                current_price = self.client.get_market_price(symbol)
                price_change_pct = (current_price - entry_price) / entry_price * 100
                
                # Generate alert if position is close to 24 hours
                if 23 < duration_hours < 24:
                    print(f"\n⚠️ ALERT: Position {symbol} approaching 24-hour time limit")
                    print(f"Current P&L: {unrealized_pnl:.2f} USDT ({price_change_pct:.2f}%)")
                    print(f"Consider closing position soon or evaluating for extension\n")
                
                # Log position status every hour
                if duration_hours > 0 and duration_hours % 1 < 0.016:  # ~1 minute window each hour
                    print(f"\nPosition update for {symbol}:")
                    print(f"Duration: {duration_hours:.2f} hours")
                    print(f"Entry: {entry_price}, Current: {current_price}")
                    print(f"P&L: {unrealized_pnl:.2f} USDT ({price_change_pct:.2f}%)\n")
                    if self.on_event_callback:
                        self.on_event_callback({
                            "type": "position_update",
                            "symbol": symbol,
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "unrealized_pnl": unrealized_pnl,
                            "duration_hours": duration_hours,
                            "ts": time.time()
                        })
            
            elif symbol in self.active_trades:
                # Position closed
                print(f"\nPosition closed for {symbol}\n")
                if self.on_event_callback:
                    self.on_event_callback({
                        "type": "position_closed",
                        "symbol": symbol,
                        "entry_price": self.active_trades[symbol]["entry_price"],
                        "size": self.active_trades[symbol]["size"],
                        "ts": time.time()
                    })
                del self.active_trades[symbol]
    
    def check_orders(self):
        """
        Check pending orders
        """
        orders = self.client.get_pending_orders()
        
        # Log pending orders
        if orders['data']:
            print("\nPending orders:")
            for order in orders['data']:
                symbol = order['symbol']
                price = float(order['price']) if order['price'] else "Market"
                size = float(order['size'])
                side = order['side']
                order_type = order['orderType']
                
                print(f"{symbol}: {side} {size} @ {price} ({order_type})")
            print()
         
        # Emit events
        if self.on_event_callback and orders['data']:
            for order in orders['data']:
                try:
                    self.on_event_callback({
                        "type": "order_pending",
                        "symbol": order.get('symbol'),
                        "side": order.get('side'),
                        "price": order.get('price'),
                        "size": order.get('size'),
                        "order_type": order.get('orderType'),
                        "ts": time.time()
                    })
                except Exception:
                    pass
