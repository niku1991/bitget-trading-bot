import json
import time
import sys
import os

from bitget.client import BitgetClient
from bot.strategy import TradingStrategy
from bot.risk_manager import RiskManager
from bot.monitor import MonitoringSystem

class BitgetTradingBot:
    def __init__(self, config_path="config.json"):
        """
        Initialize the trading bot
        
        Parameters:
        - config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Extract configuration parameters
        api_key = self.config["api_credentials"]["api_key"]
        api_secret = self.config["api_credentials"]["api_secret"]
        passphrase = self.config["api_credentials"]["passphrase"]
        
        risk_per_trade = self.config["trading_parameters"]["risk_per_trade"]
        leverage = self.config["trading_parameters"]["leverage"]
        max_risk_percent = self.config["trading_parameters"]["max_risk_percent"]
        max_positions = self.config["trading_parameters"]["max_positions"]
        
        trade_opportunities = self.config["trade_opportunities"]
        
        # Initialize components
        self.client = BitgetClient(api_key, api_secret, passphrase, is_futures=True)
        self.strategy = TradingStrategy(self.client, trade_opportunities, risk_per_trade, leverage)
        self.risk_manager = RiskManager(self.client, max_risk_percent, max_positions)
        self.monitoring = MonitoringSystem(self.client)
    
    def _load_config(self, config_path):
        """
        Load configuration from file
        
        Parameters:
        - config_path: Path to configuration file
        
        Returns:
        - Configuration as dict
        """
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Invalid JSON in configuration file: {config_path}")
            sys.exit(1)
    
    def start(self):
        """
        Start the trading bot
        
        Returns:
        - Trade execution results
        """
        print("\n===== Starting Bitget Trading Bot =====\n")
        
        # Get account balance
        balance = self.client.get_account_balance()
        print(f"Account Balance: {balance:.2f} USDT\n")
        
        # Apply risk filters to trades
        filtered_trades = self.risk_manager.apply_risk_filters(self.strategy.trade_opportunities)
        
        if not filtered_trades:
            print("No trades passed risk filters. Bot will not execute any trades.")
            return
        
        print(f"Executing {len(filtered_trades)} trades after risk filtering...\n")
        
        # Execute filtered trades
        results = self.strategy.execute_all_trades(filtered_trades)
        
        # Start monitoring system
        self.monitoring.start_monitoring()
        
        print("\nTrading bot is now running and monitoring positions.")
        return results
    
    def stop(self):
        """
        Stop the trading bot
        """
        print("\nStopping trading bot...")
        self.monitoring.stop_monitoring()
        print("Trading bot stopped.")

def main():
    """
    Main function to run the trading bot
    """
    config_path = "config.json"
    
    # Initialize and start bot
    bot = BitgetTradingBot(config_path)
    
    try:
        # Start bot with risk management
        bot.start()
        
        # Keep main thread alive to allow monitoring
        print("\nPress Ctrl+C to stop the bot...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop bot on Ctrl+C
        bot.stop()
    except Exception as e:
        print(f"Error running bot: {e}")
        bot.stop()

if __name__ == "__main__":
    main()
