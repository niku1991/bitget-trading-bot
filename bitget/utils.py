def round_to_increment(value, increment):
    """
    Round a value to the nearest increment
    
    Parameters:
    - value: Value to round
    - increment: Increment to round to
    
    Returns:
    - Rounded value
    """
    return round(value / increment) * increment

def format_price(price, tick_size):
    """
    Format a price according to the symbol's tick size
    
    Parameters:
    - price: Price to format
    - tick_size: Minimum price increment
    
    Returns:
    - Formatted price as string
    """
    return str(round_to_increment(price, tick_size))

def format_size(size, base_increment):
    """
    Format a size according to the symbol's base increment
    
    Parameters:
    - size: Size to format
    - base_increment: Minimum size increment
    
    Returns:
    - Formatted size as string
    """
    return str(round_to_increment(size, base_increment))

def calculate_position_size(entry_price, stop_loss, risk_amount, leverage):
    """
    Calculate position size based on risk parameters
    
    Parameters:
    - entry_price: Entry price
    - stop_loss: Stop loss price
    - risk_amount: Amount to risk in USD
    - leverage: Trading leverage
    
    Returns:
    - Position size in contracts
    """
    price_risk = abs(entry_price - stop_loss)
    risk_percentage = price_risk / entry_price
    
    # Calculate position size in contracts
    position_size_usd = risk_amount * leverage
    position_size_contracts = position_size_usd / entry_price
    
    return position_size_contracts

def timestamp_to_date(timestamp):
    """
    Convert timestamp to human-readable date
    
    Parameters:
    - timestamp: Unix timestamp in seconds
    
    Returns:
    - Human-readable date string
    """
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
