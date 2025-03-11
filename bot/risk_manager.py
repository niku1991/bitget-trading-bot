class RiskManager:
    def __init__(self, client, max_risk_percent=2.0, max_positions=5):
        """
        Initialize the risk manager
        
        Parameters:
        - client: BitgetClient instance
        - max_risk_percent: Maximum percentage of account to risk
        - max_positions: Maximum number of concurrent positions
        """
        self.client = client
        self.max_risk_percent = max_risk_percent  # Maximum % of account to risk
        self.max_positions = max_positions  # Maximum concurrent positions
    
    def calculate_max_risk_amount(self):
        """
        Calculate maximum amount to risk based on account balance
        
        Returns:
        - Maximum risk amount in USD
        """
        balance = self.client.get_account_balance()
        max_risk = balance * (self.max_risk_percent / 100)
        return max_risk
    
    def count_active_positions(self):
        """
        Count number of currently active positions
        
        Returns:
        - Number of active positions
        """
        positions = self.client.get_positions()
        active_count = sum(1 for pos in positions['data'] if float(pos['total']) > 0)
        return active_count
    
    def can_take_new_position(self, risk_amount):
        """
        Check if a new position can be taken
        
        Parameters:
        - risk_amount: Amount to risk in USD
        
        Returns:
        - Whether a new position can be taken
        """
        # Check if max positions reached
        if self.count_active_positions() >= self.max_positions:
            print("Maximum number of positions reached")
            return False
        
        # Check if risk amount exceeds max risk
        max_risk = self.calculate_max_risk_amount()
        if risk_amount > max_risk:
            print(f"Risk amount ${risk_amount} exceeds maximum allowed ${max_risk}")
            return False
        
        return True
    
    def apply_risk_filters(self, trade_opportunities):
        """
        Apply risk filters to trade opportunities
        
        Parameters:
        - trade_opportunities: List of trade opportunities
        
        Returns:
        - Filtered list of trade opportunities
        """
        filtered_trades = []
        active_positions = self.count_active_positions()
        available_slots = self.max_positions - active_positions
        
        if available_slots <= 0:
            print("No available position slots. Skipping all trades.")
            return []
        
        # Sort trades by confidence
        confidence_scores = {
            "High": 3,
            "Medium-High": 2,
            "Medium": 1,
            "Low": 0
        }
        
        sorted_trades = sorted(
            trade_opportunities, 
            key=lambda x: confidence_scores.get(x["confidence"], 0),
            reverse=True
        )
        
        max_risk = self.calculate_max_risk_amount()
        total_risk = 0
        
        for trade in sorted_trades:
            risk_amount = abs(trade["entry"] - trade["stop_loss"]) / trade["entry"] * 6.0  # $6 per trade
            
            if total_risk + risk_amount <= max_risk and len(filtered_trades) < available_slots:
                filtered_trades.append(trade)
                total_risk += risk_amount
            else:
                print(f"Skipping trade for {trade['symbol']} due to risk constraints")
        
        return filtered_trades
