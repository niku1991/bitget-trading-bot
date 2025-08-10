import json
import time
import sys
import os
import argparse

from bitget.client import BitgetClient
from bot.strategy import TradingStrategy
from bot.risk_manager import RiskManager
from bot.monitor import MonitoringSystem
from bot import default_event_logger
import sqlite3
import math
from ai.train import train_model
from ai.backtest import backtest_grid
from ai.infer import load_model, predict_score
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class BitgetTradingBot:
    def __init__(self, config_path="config.json", debug=True, dry_run=True, min_ai_score=0.0):
        """
        Initialize the trading bot
        
        Parameters:
        - config_path: Path to configuration file
        - debug: Whether to enable debug output
        - dry_run: If True, do not place real orders
        - min_ai_score: Minimum AI score (0-1) required to execute trades
        """
        # Load configuration
        self.config = self._load_config(config_path)
        self.debug = debug
        self.dry_run = dry_run
        self.min_ai_score = min_ai_score
        
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
        self.db_path = os.path.join(os.getcwd(), "trades.db")
    
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
                
                # Overlay environment variables if present
                env_api_key = os.getenv("BITGET_API_KEY")
                env_api_secret = os.getenv("BITGET_API_SECRET")
                env_passphrase = os.getenv("BITGET_PASSPHRASE")
                if env_api_key:
                    config.setdefault("api_credentials", {})["api_key"] = env_api_key
                if env_api_secret:
                    config.setdefault("api_credentials", {})["api_secret"] = env_api_secret
                if env_passphrase:
                    config.setdefault("api_credentials", {})["passphrase"] = env_passphrase
                
                # Validate credentials - make sure they're not empty
                credentials = config.get("api_credentials", {})
                if not credentials.get("api_key") or not credentials.get("api_secret") or not credentials.get("passphrase"):
                    print("WARNING: API credentials are missing or empty. Please set BITGET_API_KEY/SECRET/PASSPHRASE env vars or update config.json with valid credentials.")
                
                return config
        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Invalid JSON in configuration file: {config_path}")
            sys.exit(1)
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                type TEXT NOT NULL,
                symbol TEXT,
                entry_price REAL,
                current_price REAL,
                size REAL,
                unrealized_pnl REAL,
                duration_hours REAL,
                extra TEXT
            )
            """
        )
        conn.commit()
        conn.close()
    
    def _event_sink(self, event: dict):
        # Log to console
        default_event_logger(event)
        # Persist minimal fields
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO trade_events (ts, type, symbol, entry_price, current_price, size, unrealized_pnl, duration_hours, extra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    float(event.get("ts", time.time())),
                    str(event.get("type")),
                    event.get("symbol"),
                    float(event.get("entry_price")) if event.get("entry_price") is not None else None,
                    float(event.get("current_price")) if event.get("current_price") is not None else None,
                    float(event.get("size")) if event.get("size") is not None else None,
                    float(event.get("unrealized_pnl")) if event.get("unrealized_pnl") is not None else None,
                    float(event.get("duration_hours")) if event.get("duration_hours") is not None else None,
                    json.dumps({k: v for k, v in event.items() if k not in {"ts","type","symbol","entry_price","current_price","size","unrealized_pnl","duration_hours"}})
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: failed to persist event: {e}")
    
    def _naive_predictor(self, symbol: str, candles: list):
        """
        Simple baseline predictor: momentum score based on last N closes and volatility penalty.
        Returns a score in [0,1].
        """
        # Prefer trained model if available
        try:
            if os.path.exists("ai_model.json"):
                model = load_model("ai_model.json")
                return predict_score(model, candles)
        except Exception as e:
            print(f"Model load/predict failed, falling back to naive predictor: {e}")
        if not candles or len(candles) < 20:
            return 0.5
        closes = [c["close"] for c in candles[-50:]]
        # Momentum: slope-like measure
        gains = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
        momentum = gains / (len(closes) - 1)
        # Volatility penalty
        mean = sum(closes) / len(closes)
        var = sum((x - mean) ** 2 for x in closes) / len(closes)
        vol = math.sqrt(var) / mean if mean else 0.0
        score = momentum * max(0.0, 1.0 - min(1.0, vol * 5))
        return max(0.0, min(1.0, score))
     
    def initialize_components(self):
        """
        Initialize trading strategy, risk manager, and monitoring components
        """
        # Initialize components only after successful API connection
        self.strategy = TradingStrategy(self.client, self.trade_opportunities, self.risk_per_trade, self.leverage, dry_run=self.dry_run, min_ai_score=self.min_ai_score)
        self.risk_manager = RiskManager(self.client, self.max_risk_percent, self.max_positions)
        self.monitoring = MonitoringSystem(self.client, on_event_callback=self._event_sink)
    
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
        self._init_db()
        
        # Test connectivity and authentication first
        if not self.verify_connectivity():
            print("Failed to connect to Bitget API. Bot startup aborted.")
            return
            
        if not self.test_authentication():
            print("Authentication failed. Please check your API credentials.")
            return
        
        # Initialize components now that we have verified connectivity
        self.initialize_components()
        
        # Apply AI scoring to trade opportunities
        try:
            self.strategy.apply_ai_scores(self._naive_predictor)
        except Exception as e:
            print(f"AI scoring failed: {e}")
            
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
    parser.add_argument('--live', action='store_true', help='Execute real orders (disables dry-run)')
    parser.add_argument('--min-ai-score', type=float, default=0.0, help='Minimum AI score [0-1] required to execute a trade')
    parser.add_argument('--summary', action='store_true', help='Show quick portfolio summary and exit')
    parser.add_argument('--cancel-all', action='store_true', help='Cancel all pending orders and exit')
    parser.add_argument('--train-model', action='store_true', help='Train AI model from recent candles and save to ai_model.json')
    parser.add_argument('--backtest', action='store_true', help='Run backtest to optimize score threshold and risk sizing')
    parser.add_argument('--bt-symbols', type=str, default='', help='Comma-separated symbols for training/backtesting')
    parser.add_argument('--bt-granularity', type=str, default='15m', help='Candle granularity for backtest')
    parser.add_argument('--bt-window', type=int, default=50, help='Feature window size')
    parser.add_argument('--bt-horizon', type=int, default=12, help='Prediction horizon in bars')
    parser.add_argument('--bt-label-thr', type=float, default=0.5, help='Label threshold percent for positive class')
    parser.add_argument('--bt-score-grid', type=str, default='0.5,0.6,0.7,0.8', help='Comma-separated score thresholds to test')
    parser.add_argument('--bt-risk-grid', type=str, default='2,4,6,8,10', help='Comma-separated risk per trade values to test')
    parser.add_argument('--risk-per-trade', type=float, default=None, help='Override risk per trade (USD) for this run')
    parser.add_argument('--bt-starting-balance', type=float, default=1000.0, help='Starting balance for backtest')
    parser.add_argument('--bt-risk-mode', type=str, default='usd', choices=['usd','pct'], help='Risk per trade mode: usd or pct')
    parser.add_argument('--bt-fee-bps', type=float, default=2.0, help='Fee (basis points) per side on notional')
    parser.add_argument('--bt-slip-bps', type=float, default=1.0, help='Slippage (basis points) each side')
    parser.add_argument('--bt-dd-stop', type=float, default=None, help='Max drawdown stop in percent (test will stop when exceeded)')
    parser.add_argument('--bt-max-trades', type=int, default=None, help='Limit the number of trades during backtest')
    parser.add_argument('--auto-connect', action='store_true', help='Automatically find API endpoint and test authentication, then exit')
    args = parser.parse_args()
    
    # Initialize bot
    bot = BitgetTradingBot(config_path=args.config, debug=args.debug, dry_run=not args.live, min_ai_score=args.min_ai_score)
    if args.risk_per_trade is not None:
        bot.risk_per_trade = float(args.risk_per_trade)
    
    try:
        # Test connectivity if requested
        if args.test_connection:
            success = bot.verify_connectivity()
            sys.exit(0 if success else 1)
            
        # Test authentication if requested
        if args.test_auth:
            success = bot.test_authentication()
            sys.exit(0 if success else 1)

        # Auto connect: verify connectivity and auth in one step
        if args.auto_connect:
            ok = bot.verify_connectivity()
            if not ok:
                sys.exit(1)
            ok = bot.test_authentication()
            sys.exit(0 if ok else 1)

        # Train model
        if args.train_model:
            if not bot.verify_connectivity() or not bot.test_authentication():
                sys.exit(1)
            symbols = [s.strip() for s in (args.bt_symbols or ','.join([t['symbol'] for t in bot.trade_opportunities])).split(',') if s.strip()]
            path = train_model(bot.client, symbols, granularity=args.bt_granularity, window=args.bt_window, horizon=args.bt_horizon, threshold_pct=args.bt_label_thr)
            print(f"Model saved to {path}")
            sys.exit(0)

        # Backtest optimize
        if args.backtest:
            if not bot.verify_connectivity() or not bot.test_authentication():
                sys.exit(1)
            symbols = [s.strip() for s in (args.bt_symbols or ','.join([t['symbol'] for t in bot.trade_opportunities])).split(',') if s.strip()]
            score_grid = [float(x) for x in args.bt_score_grid.split(',') if x]
            risk_grid = [float(x) for x in args.bt_risk_grid.split(',') if x]
            report = backtest_grid(
                bot.client, symbols,
                granularity=args.bt_granularity,
                window=args.bt_window,
                horizon=args.bt_horizon,
                threshold_pct=args.bt_label_thr,
                score_grid=score_grid,
                risk_grid=risk_grid,
                leverage=bot.leverage,
                starting_balance=args.bt_starting_balance,
                risk_mode=args.bt_risk_mode,
                fee_bps=args.bt_fee_bps,
                slippage_bps=args.bt_slip_bps,
                dd_stop_pct=args.bt_dd_stop,
                max_trades=args.bt_max_trades
            )
            best = report['best']
            print("\n=== Backtest Best Config ===")
            print(f"threshold={best['threshold']}, risk_per_trade={best['risk_per_trade']} ({best['risk_mode']})")
            print(f"trades={best['trades']}, win_rate={best['win_rate']:.2f}")
            print(f"total_pnl={best['total_pnl']:.2f}, final_equity={best['final_equity']:.2f}, return_pct={best['return_pct']:.2f}%")
            print(f"max_dd={best['max_drawdown']:.2f}, max_dd_pct={best['max_drawdown_pct']:.2f}%")
            print(f"best_trade={best['best_trade']:.2f}, worst_trade={best['worst_trade']:.2f}, sharpe_like={best['sharpe_like']:.2f}")
            sys.exit(0)

        # Summary action
        if args.summary:
            if not bot.verify_connectivity() or not bot.test_authentication():
                sys.exit(1)
            bal = bot.client.get_account_balance()
            positions = bot.client.get_positions()
            orders = bot.client.get_pending_orders()
            print("\n=== Portfolio Summary ===")
            print(f"Balance: {bal:.2f} USDT")
            print(f"Active positions: {len([p for p in positions.get('data', []) if float(p.get('total', 0))>0])}")
            print(f"Pending orders: {len(orders.get('data', []) or [])}")
            sys.exit(0)

        # Cancel-all action
        if args.cancel_all:
            if not bot.verify_connectivity() or not bot.test_authentication():
                sys.exit(1)
            if bot.dry_run:
                pending = bot.client.get_pending_orders()
                n = len(pending.get('data', []) or [])
                print(f"Dry-run: Would cancel {n} pending orders.")
                sys.exit(0)
            res = bot.client.cancel_all_pending_orders()
            print(f"Canceled {len(res)} orders.")
            sys.exit(0)
        
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
