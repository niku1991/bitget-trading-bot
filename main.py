import json
import time
import sys
import os
import argparse

from bitget.client import BitgetClient
from bot.strategy import TradingStrategy
from bot.risk_manager import RiskManager
from bot.monitor import MonitoringSystem

class BitgetTradingBot:
    def __init__(self, config_path="config.json", debug=True):
        """
        Initialize the trading bot
        
        Parameters:
        - config_path: Path to configuration file
        - debug: Whether to enable debug output
        """
        # Load configuration
        self.config = self._load_config(config_path)
        self.debug = debug
        
        # Extract configuration parameters
        api_key = self.config["api_credentials"]["api_key"]
        api_secret = self.config["api_credentials"]["api_secret"]
        passphrase = self.config["api_credentials"]["passphrase"]
        
        risk_per_trade = self.config["trading_parameters"]["risk_per_trade"]
        leverage = self.config["trading_parameters"]["leverage"]
        max_risk_percent = self.config["trading_parameters"]["max_risk_percent"]
        max_positions = self.config["trading_parameters"]["max_positions"]
        
        trade_opportunities = self.config["trade_opportunities"]
        
        # Initialize client
        self.client = BitgetClient(api_key, api_secret, passphrase, is_futures=True, debug=debug)
        
        # Set up other components after verifying connectivity
        self.strategy = None
        self.risk_manager = None
        self.monitoring = None
        self.trade_opportunities = trade_opportunities
        self.risk_per_trade = risk_per_trade
        self.leverage = leverage
        self.max_risk_percent = max_risk_percent
        self.max_positions = max_positions
    
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
                config = json.load(f)
                
                # Validate credentials - make sure they're not empty
                credentials = config.get("api_credentials", {})
                if not credentials.get("api_key") or not credentials.get("api_secret") or not credentials.get("passphrase"):
                    print("WARNING: API credentials are missing or empty. Please update config.json with valid credentials.")
                
                return config
        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Invalid JSON in configuration file: {config_path}")
            sys.exit(1)
    
    def initialize_components(self):
        """
        Initialize trading strategy, risk manager, and monitoring components
        """
        # Initialize components only after successful API connection
        self.strategy = TradingStrategy(self.client, self.trade_opportunities, self.risk_per_trade, self.leverage)
        self.risk_manager = RiskManager(self.client, self.max_risk_percent, self.max_positions)
        self.monitoring = MonitoringSystem(self.client)
    
    def verify_connectivity(self):
        """
        Verify connectivity to Bitget API
        
        Returns:
        - True if connected successfully, False otherwise
        """
        print("\n===== Testing Bitget API Connection =====\n")
        
        # First check if we can connect to the API
        if not self.client.ping_api():
            print("Unable to connect to the Bitget API with current base URL.")
            print("Trying to find a working API endpoint...")
            
            # Try to find a working API endpoint
            if not self.client.try_alternate_base_urls():
                print("❌ Could not connect to any Bitget API endpoints.")
                print("Please check your internet connection and verify Bitget services are operational.")
                return False
        
        print(f"✅ Successfully connected to Bitget API endpoint: {self.client.base_url}")
        return True
    
    def test_authentication(self):
        """
        Test authentication with Bitget API
        
        Returns:
        - True if authentication is successful, False otherwise
        """
        print("\n===== Testing Bitget API Authentication =====\n")
        
        # First verify basic connectivity
        if not self.verify_connectivity():
            return False
            
        # Now test authentication
        try:
            # Try to get account balance to verify authentication
            balance = self.client.get_account_balance()
            print(f"✅ Authentication test successful! Account balance: {balance:.6f} USDT")
            return True
        except Exception as e:
            print(f"❌ Authentication test failed: {str(e)}")
            
            # Provide troubleshooting tips
            print("\nTroubleshooting tips:")
            print("1. Check your API key, secret, and passphrase for accuracy")
            print("2. Ensure there's no whitespace in your credentials")
            print("3. Check if your API key has the necessary permissions")
            print("4. If you've enabled IP restrictions, ensure your current IP is allowed")
            print("5. Try creating new API credentials on Bitget")
            return False

    def start(self):
        """
        Start the trading bot
        
        Returns:
        - Trade execution results
        """
        print("\n===== Starting Bitget Trading Bot =====\n")
        
        # Test connectivity and authentication first
        if not self.verify_connectivity():
            print("Failed to connect to Bitget API. Bot startup aborted.")
            return
            
        if not self.test_authentication():
            print("Authentication failed. Please check your API credentials.")
            return
        
        # Initialize components now that we have verified connectivity
        self.initialize_components()
            
        try:
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
        except Exception as e:
            print(f"Error starting bot: {e}")
            return None
    
    def stop(self):
        """
        Stop the trading bot
        """
        print("\nStopping trading bot...")
        if self.monitoring:
            self.monitoring.stop_monitoring()
        print("Trading bot stopped.")

def main():
    """
    Main function to run the trading bot
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Bitget Trading Bot')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--test-auth', action='store_true', help='Test API authentication and exit')
    parser.add_argument('--test-connection', action='store_true', help='Test API connection and exit')
    args = parser.parse_args()
    
    # Initialize bot
    bot = BitgetTradingBot(config_path=args.config, debug=args.debug)
    
    try:
        # Test connectivity if requested
        if args.test_connection:
            success = bot.verify_connectivity()
            sys.exit(0 if success else 1)
            
        # Test authentication if requested
        if args.test_auth:
            success = bot.test_authentication()
            sys.exit(0 if success else 1)
        
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
        sys.exit(1)

if __name__ == "__main__":
    main()
