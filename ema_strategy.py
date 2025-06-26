"""
EMA Breakthrough Strategy Module
"""

import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import asyncio
import logging
from config import SYMBOLS_TO_MONITOR, EMA_PERIODS, EMA_TIMEFRAMES, TIMEFRAMES_PARAMS

logger = logging.getLogger(__name__)

class EMAStrategy:
    def __init__(self, notifier=None):
        self.exchange = ccxt.okx()
        self.notifier = notifier
        # Store last price position to detect breakthroughs
        self.last_positions = {}
    
    def check_ema_breakthrough(self, df, ema_periods):
        """Checks for EMA breakthroughs."""
        if len(df) < 2:
            return []
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        breakthroughs = []
        
        for period in ema_periods:
            ema_col = f'ema_{period}'
            if ema_col not in df.columns:
                continue
            
            current_price = current['close']
            previous_price = previous['close']
            current_ema = current[ema_col]
            previous_ema = previous[ema_col]
            
            # Check for upward breakthrough
            if previous_price <= previous_ema and current_price > current_ema:
                breakthroughs.append({
                    'type': 'Upward',
                    'ema_period': period,
                    'price': current_price,
                    'ema_value': current_ema,
                })
            
            # Check for downward breakthrough
            elif previous_price >= previous_ema and current_price < current_ema:
                breakthroughs.append({
                    'type': 'Downward',
                    'ema_period': period,
                    'price': current_price,
                    'ema_value': current_ema,
                })
        
        return breakthroughs
    
    async def analyze_symbol(self, symbol, timeframe):
        """Analyzes EMA for a single symbol."""
        try:
            logger.info(f"Analyzing EMA breakthrough for {symbol} on {timeframe}...")
            
            # Use limit from config
            limit = TIMEFRAMES_PARAMS[timeframe]['limit']
            ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"Could not fetch OHLCV data for {symbol} on {timeframe}.")
                return

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty or len(df) < max(EMA_PERIODS):
                logger.warning(f"Not enough data for {symbol} on {timeframe} to calculate EMA.")
                return

            # Calculate all EMAs
            for period in EMA_PERIODS:
                df[f'ema_{period}'] = ta.ema(df['close'], length=period)
            
            # Check for breakthroughs
            breakthroughs = self.check_ema_breakthrough(df, EMA_PERIODS)
            
            if breakthroughs and self.notifier:
                message_parts = []
                # Define emoji levels based on EMA period importance
                emoji_levels = {21: 1, 55: 2, 100: 3}

                for breakthrough in breakthroughs:
                    base_emoji = '🚀' if breakthrough['type'] == 'Upward' else '📉'
                    # Use .get() for safety, default to 1 emoji
                    emoji_count = emoji_levels.get(breakthrough['ema_period'], 1)
                    emojis = base_emoji * emoji_count
                    
                    # Extract base currency, e.g., 'BTC' from 'BTC/USDT:USDT'
                    base_currency = symbol.split('/')[0]
                    
                    # Format message lines
                    line1 = f"{emojis} {base_currency} {timeframe} {'Breakout' if breakthrough['type'] == 'Upward' else 'Breakdown'} EMA{breakthrough['ema_period']}!"
                    line2 = f"Price: {breakthrough['price']:.2f}, EMA{breakthrough['ema_period']}: {breakthrough['ema_value']:.2f}"
                    
                    message_parts.append(f"{line1}\n{line2}")
 
                if message_parts:
                    # Join all parts with a separator
                    full_message = "\n---\n".join(message_parts)
                    await self.notifier.send_message(full_message)
                    logger.info(f"Sent merged EMA notification for {symbol} ({timeframe})")

        except ccxt.NetworkError as e:
            logger.error(f"CCXT Network Error ({symbol}, {timeframe}): {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"CCXT Exchange Error ({symbol}, {timeframe}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing EMA for {symbol} ({timeframe}): {e}", exc_info=True)
    
    async def run_analysis(self):
        """Runs the complete EMA analysis."""
        logger.info(f"Starting EMA breakthrough analysis task: {datetime.now()}")
        
        for symbol in SYMBOLS_TO_MONITOR:
            for timeframe in EMA_TIMEFRAMES:
                await self.analyze_symbol(symbol, timeframe)
                await asyncio.sleep(1)  # Short delay between API requests to avoid rate limiting
        
        logger.info(f"EMA analysis task finished for this cycle.")