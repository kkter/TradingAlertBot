"""
配置文件 - 统一管理交易对和参数
"""

# 监控的交易对
SYMBOLS_TO_MONITOR = [
    'BTC/USDT:USDT', 'ETH/USDT:USDT', 'XMR/USDT:USDT', 'AAVE/USDT:USDT','HYPE/USDT:USDT', 
    'SUI/USDT:USDT', 'SOL/USDT:USDT', 'FARTCOIN/USDT:USDT', 'VIRTUAL/USDT:USDT',
    'KAITO/USDT:USDT', 'BNB/USDT:USDT', 'UNI/USDT:USDT'
]

# 时间周期参数
TIMEFRAMES_PARAMS = {
    '4h': {'limit': 200, 'rsi_period': 14, 'bb_period': 20, 'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9},
    '1d': {'limit': 200, 'rsi_period': 20, 'bb_period': 30, 'macd_fast': 15, 'macd_slow': 30, 'macd_signal': 9},
    '1w': {'limit': 300, 'rsi_period': 30, 'bb_period': 50, 'macd_fast': 20, 'macd_slow': 40, 'macd_signal': 9}
}

# EMA参数
EMA_PERIODS = [21, 55, 100]
EMA_TIMEFRAMES = ['4h', '1d', '1w']
