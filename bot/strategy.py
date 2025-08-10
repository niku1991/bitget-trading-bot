from bitget.utils import round_to_increment, calculate_position_size

class TradingStrategy:
    def __init__(self, client, trade_opportunities, risk_per_trade=6.0, leverage=10, dry_run=False, min_ai_score=0.0):
        """
        Initialize the trading strategy
        
        Parameters:
        - client: BitgetClient instance
        - trade_opportunities: List of trade opportunities
        - risk_per_trade: Amount to risk per trade in USD
        - leverage: Trading leverage
        - dry_run: If True, do not place real orders
        - min_ai_score: Minimum AI score (0-1) required to execute a trade
        """
        self.client = client
        self.risk_per_trade = risk_per_trade  # Amount to risk per trade in USD
        self.leverage = leverage
        self.trade_opportunities = trade_opportunities
        self.dry_run = dry_run
        self.min_ai_score = min_ai_score
    
    def apply_ai_scores(self, predictor_fn):
        """
        Apply AI scoring to each trade opportunity in-place.

        predictor_fn should accept (symbol: str, candles: list[dict]) -> float in [0,1].
        """
        for trade in self.trade_opportunities:
            symbol = trade["symbol"]
            try:
                candles = self.client.get_candles(symbol, granularity="15m", limit=200)
            except Exception:
                candles = []
            try:
                score = float(predictor_fn(symbol, candles))
                score = max(0.0, min(1.0, score))
                trade["ai_score"] = score
            except Exception:
                trade["ai_score"] = 0.0

    def execute_trade(self, trade):
        """
        Execute a trade based on our strategy
        
        Parameters:
        - trade: Trade opportunity to execute
        
        Returns:
        - Trade execution result
        """
        symbol = trade["symbol"]
        entry_price = trade["entry"]
        target_price = trade["target"]
        stop_loss = trade["stop_loss"]
        ai_score = float(trade.get("ai_score", 1.0))

        if ai_score < self.min_ai_score:
            return {"status": "skipped", "reason": f"ai_score {ai_score:.2f} below threshold {self.min_ai_score:.2f}", "symbol": symbol}
        
        # Calculate position size
        raw_position_size = calculate_position_size(
            entry_price, 
            stop_loss, 
            self.risk_per_trade, 
            self.leverage
        )
        position_size = round_to_increment(raw_position_size, trade["base_increment"])
        
        print(f"\nExecuting trade for {symbol}:")
        print(f"Entry: {entry_price}, Target: {target_price}, Stop Loss: {stop_loss}")
        print(f"Position Size: {position_size} contracts (${position_size * entry_price})")
        if "ai_score" in trade:
            print(f"AI score: {ai_score:.2f}")
        
        try:
            if self.dry_run:
                print("Dry-run mode: Skipping real order placement.")
                entry_order = {"dry_run": True, "symbol": symbol, "side": "buy", "orderType": "limit", "price": entry_price, "size": position_size}
            else:
                # Set leverage
                self.client.set_leverage(symbol, self.leverage)
                
                # Place limit entry order
                entry_order = self.client.place_order(
                    symbol=symbol,
                    side="buy",
                    order_type="limit",
                    price=entry_price,
                    size=position_size
                )
                print(f"Entry order placed: {entry_order}")
            
            # Calculate partial take profit level (50% of the way to target)
            partial_tp = entry_price + (target_price - entry_price) / 2
            partial_tp = round(partial_tp / trade["tick_size"]) * trade["tick_size"]
            
            # Place partial take profit order (50% of position)
            partial_tp_size = round_to_increment(position_size / 2, trade["base_increment"])
            if self.dry_run:
                tp_order_1 = {"dry_run": True, "type": "tp1", "trigger": partial_tp, "size": partial_tp_size}
            else:
                tp_order_1 = self.client.place_stop_order(
                    symbol=symbol,
                    side="sell",
                    size=partial_tp_size,
                    trigger_price=partial_tp
                )
            print(f"Partial take profit order placed at {partial_tp}: {tp_order_1}")
            
            # Place final take profit order (remaining 50% of position)
            if self.dry_run:
                tp_order_2 = {"dry_run": True, "type": "tp2", "trigger": target_price, "size": partial_tp_size}
            else:
                tp_order_2 = self.client.place_stop_order(
                    symbol=symbol,
                    side="sell",
                    size=partial_tp_size,
                    trigger_price=target_price
                )
            print(f"Final take profit order placed at {target_price}: {tp_order_2}")
            
            # Place stop loss order
            if self.dry_run:
                sl_order = {"dry_run": True, "type": "sl", "trigger": stop_loss, "size": position_size}
            else:
                sl_order = self.client.place_stop_order(
                    symbol=symbol,
                    side="sell",
                    size=position_size,
                    trigger_price=stop_loss
                )
            print(f"Stop loss order placed at {stop_loss}: {sl_order}")
            
            return {
                "status": "success",
                "entry_order": entry_order,
                "partial_tp_order": tp_order_1,
                "final_tp_order": tp_order_2,
                "stop_loss_order": sl_order
            }
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def execute_all_trades(self, filtered_trades=None):
        """
        Execute all trade opportunities
        
        Parameters:
        - filtered_trades: (Optional) Filtered list of trades to execute
        
        Returns:
        - List of trade execution results
        """
        trades_to_execute = filtered_trades if filtered_trades else self.trade_opportunities
        results = []
        
        for trade in trades_to_execute:
            result = self.execute_trade(trade)
            results.append({
                "symbol": trade["symbol"],
                "result": result
            })
        
        return results
    
    def update_trailing_stops(self):
        """
        Update trailing stops for active positions
        """
        positions = self.client.get_positions()
        
        for position in positions['data']:
            symbol = position['symbol']
            size = float(position['total'])
            
            # Skip positions with zero size
            if size <= 0:
                continue
                
            entry_price = float(position['averageOpenPrice'])
            
            # Find corresponding trade opportunity
            trade = next((t for t in self.trade_opportunities if t["symbol"] == symbol), None)
            if trade is None:
                print(f"No trade configuration found for {symbol}, skipping.")
                continue
            
            current_price = self.client.get_market_price(symbol)
            target = trade["target"]
            half_target = entry_price + (target - entry_price) / 2
            
            # If price has reached half-target, move stop loss to entry
            if current_price >= half_target:
                # Calculate new stop loss (breaking even)
                new_stop = entry_price
                
                # Place updated stop order
                try:
                    self.client.place_stop_order(
                        symbol=symbol,
                        side="sell",
                        size=size/2,  # For the remaining half position
                        trigger_price=new_stop
                    )
                    print(f"Updated stop loss for {symbol} to break-even at {new_stop}")
                except Exception as e:
                    print(f"Error updating stop loss: {e}")
