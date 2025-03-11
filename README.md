# Bitget Trading Bot

Automated trading bot for Bitget cryptocurrency exchange based on market analysis. This bot implements a strategy for executing short-term trades with proper risk management and partial profit-taking.

## Features

- **API Integration**: Secure integration with Bitget's API for USDT-M futures trading
- **API Endpoint Auto-Detection**: Automatically finds working Bitget API endpoints
- **Risk Management**: Limits position sizes based on account balance and configurable risk parameters
- **Partial Take-Profit Strategy**: Takes profit at 50% of target and moves stop-loss to break-even
- **Position Monitoring**: Tracks positions and provides alerts, especially as they approach the 24-hour mark
- **Trade Prioritization**: Executes trades based on confidence levels when there are limited position slots
- **Authentication Testing**: Includes tools to verify API credentials before executing trades

## Trade Opportunities

The bot comes pre-configured with the following high-potential trade opportunities:

1. **DOGE/USD (LONG)**: Entry $0.17, Target $0.18, Stop Loss $0.16
2. **AVAX/USD (LONG)**: Entry $17.27, Target $19.03, Stop Loss $16.40
3. **TON/USD (LONG)**: Entry $2.65, Target $2.92, Stop Loss $2.51
4. **SOL/USD (LONG)**: Entry $123.64, Target $136.25, Stop Loss $117.45
5. **ADA/USD (LONG)**: Entry $0.72, Target $0.79, Stop Loss $0.68
6. **BNB/USD (LONG)**: Entry $544.14, Target $599.66, Stop Loss $516.93

## Installation

1. Clone this repository:
```bash
git clone https://github.com/jamsturg/bitget-trading-bot.git
cd bitget-trading-bot
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Configure your Bitget API credentials:
   - Edit the `config.json` file and add your API key, secret, and passphrase
   - Adjust trading parameters if needed

## API Connection Testing

Before running the bot, it's recommended to test the API connection:

```bash
python main.py --test-connection
```

This will attempt to connect to various Bitget API endpoints to find one that works. The bot will automatically try different API base URLs if the default one doesn't work.

## Authentication Testing

After confirming API connectivity, test your API credentials:

```bash
python auth_test.py
```

This script will:
1. Try different Bitget API endpoints to find a working one
2. Verify that your API credentials are working correctly
3. Show your account balance if authentication is successful
4. Provide troubleshooting steps if authentication fails

Common authentication errors include:
- **apikey/password is incorrect** (code 40012): Check your API key and passphrase
- **sign signature error** (code 40009): Check your API secret key
- **Request URL NOT FOUND** (code 40404): The bot will now automatically try different API endpoints

If you encounter authentication issues, try the following:
1. Make sure there's no leading/trailing whitespace in your credentials
2. Create new API credentials on Bitget and update your config.json file
3. Ensure your API key has trading permissions enabled
4. If you've enabled IP restrictions, make sure your current IP is allowed

## Usage

Run the bot in debug mode to see detailed API requests and responses:

```bash
python main.py --debug
```

The bot will:
1. Test API connectivity to find a working endpoint
2. Test your API credentials
3. Connect to Bitget and check account balance
4. Apply risk filters to determine which trades to execute
5. Place entry, take-profit, and stop-loss orders for filtered trades
6. Monitor positions continuously and provide updates
7. Alert you when positions approach the 24-hour time limit

To stop the bot, press `Ctrl+C`.

## Command Line Options

The bot supports several command line options:

```bash
python main.py --help
```

Available options:
- `--config PATH`: Specify an alternative config file path
- `--debug`: Enable detailed API debugging output
- `--test-auth`: Only test authentication and exit
- `--test-connection`: Only test API connectivity and exit

## Risk Management Strategy

The bot implements several risk management features:

- **Maximum Position Count**: Limits the number of concurrent positions (default: 5)
- **Risk Per Trade**: Sets the amount to risk per trade (default: $6.0 at 10x leverage)
- **Maximum Account Risk**: Limits the total percentage of account at risk (default: 2%)
- **Partial Profit-Taking**: Takes 50% profit at halfway to target and moves stop to break-even
- **Position Time Limit**: Alerts when positions approach 24 hours, encouraging proper position management

## Security Considerations

- **API Key Permissions**: Create API keys with trading permissions only, not withdrawal permissions
- **IP Restriction**: Consider restricting API keys to specific IP addresses
- **Start Small**: Begin with small position sizes to verify bot behavior

## Troubleshooting

If you encounter issues:

1. **API Connection Errors**:
   - Use `python main.py --test-connection` to test API connectivity
   - The bot will automatically try different API endpoints if the default one doesn't work
   - Check if your internet connection can access Bitget's API servers

2. **Authentication Errors**:
   - Use `python auth_test.py` to diagnose API credential issues
   - Ensure no whitespace in credentials
   - Try creating new API keys on Bitget

3. **Order Placement Errors**:
   - Verify you have sufficient funds in your account
   - Check that the symbol name is correct (e.g., "DOGEUSDT_UMCBL")
   - Ensure position size is above the minimum for the symbol

4. **Other Issues**:
   - Run with `--debug` flag to see detailed API requests and responses
   - Check Bitget's API documentation for any recent changes

## Modifying Trade Opportunities

Edit the `config.json` file to modify existing trades or add new ones. Each trade requires:

- **symbol**: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
- **entry**: Entry price
- **target**: Target price
- **stop_loss**: Stop loss price
- **confidence**: Confidence level ("High", "Medium-High", "Medium", or "Low")
- **base_increment**: Minimum order size increment
- **tick_size**: Minimum price increment

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

Trading cryptocurrencies involves risk. This software is provided for educational purposes only. Use at your own risk.
