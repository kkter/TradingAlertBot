"""
Oversold/Overbought Strategy Module
"""

import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import asyncio
import logging
from config import SYMBOLS_TO_MONITOR, TIMEFRAMES_PARAMS

logger = logging.getLogger(__name__)

class OversoldOverboughtStrategy:
    def __init__(self, notifier=None):
        self.exchange = ccxt.binance()
        self.notifier = notifier
    
    def check_market_status(self, price, rsi, bb_upper, bb_lower, macd, macd_signal):
        """Checks the market status using technical indicators."""
        
        if pd.isna(rsi) or pd.isna(bb_lower) or pd.isna(bb_upper) or pd.isna(macd) or pd.isna(macd_signal) or pd.isna(price):
            return {
                "rsi_status": "Not enough data",
                "bb_status": "Not enough data",
                "macd_status": "Not enough data",
                "overall_status": "Not enough data",
                "has_signal": False,
                "has_combined_signal": False
            }

        # Individual indicator status
        rsi_status = "Neutral"
        if rsi < 30:
            rsi_status = "Oversold"
        elif rsi > 70:
            rsi_status = "Overbought"
        
        bb_status = "Neutral"
        if price <= bb_lower:
            bb_status = "Oversold"
        elif price >= bb_upper:
            bb_status = "Overbought"
        
        macd_status = "Neutral"
        if macd < macd_signal and macd < 0:
            macd_status = "Bearish"  # Oversold tendency
        elif macd > macd_signal and macd > 0:
            macd_status = "Bullish"  # Overbought tendency
        
        # Helper functions to check status
        is_oversold = lambda s: s in ["Oversold", "Bearish"]
        is_overbought = lambda s: s in ["Overbought", "Bullish"]

        # Check for any individual overbought/oversold signal
        has_signal = (
            is_oversold(rsi_status) or is_overbought(rsi_status) or
            is_oversold(bb_status) or is_overbought(bb_status) or
            is_oversold(macd_status) or is_overbought(macd_status)
        )
        
        # Combined status check
        signals = [rsi_status, bb_status, macd_status]
        oversold_count = sum(1 for s in signals if is_oversold(s))
        overbought_count = sum(1 for s in signals if is_overbought(s))
        
        overall_status = "Combined Neutral"
        has_combined_signal = False
        
        if oversold_count >= 2:
            overall_status = "Combined Oversold"
            has_combined_signal = True
        elif overbought_count >= 2:
            overall_status = "Combined Overbought"
            has_combined_signal = True
        
        return {
            "rsi_status": rsi_status,
            "bb_status": bb_status,
            "macd_status": macd_status,
            "overall_status": overall_status,
            "has_signal": has_signal,
            "has_combined_signal": has_combined_signal
        }
    
    async def analyze_symbol(self, symbol, timeframe, params, send_all_signals=False):
        """Analyzes a single symbol."""
        try:
            logger.info(f"Analyzing {symbol} on {timeframe} timeframe...")
            
            ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=params['limit'])
            if not ohlcv:
                logger.warning(f"Could not fetch OHLCV data for {symbol} on {timeframe}.")
                return

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty:
                logger.warning(f"DataFrame for {symbol} on {timeframe} is empty.")
                return

            # Calculate technical indicators
            df['rsi'] = ta.rsi(df['close'], length=params['rsi_period'])
            
            bb_bands = ta.bbands(df['close'], length=params['bb_period'], std=2)
            if bb_bands is None or not all(col in bb_bands.columns for col in [f'BBU_{params["bb_period"]}_2.0', f'BBM_{params["bb_period"]}_2.0', f'BBL_{params["bb_period"]}_2.0']):
                logger.warning(f"Could not calculate Bollinger Bands for {symbol} on {timeframe}.")
                return
            df['bb_upper'] = bb_bands[f'BBU_{params["bb_period"]}_2.0']
            df['bb_middle'] = bb_bands[f'BBM_{params["bb_period"]}_2.0']
            df['bb_lower'] = bb_bands[f'BBL_{params["bb_period"]}_2.0']
            
            macd_data = ta.macd(df['close'], fast=params['macd_fast'], slow=params['macd_slow'], signal=params['macd_signal'])
            if macd_data is None or not all(col in macd_data.columns for col in [f'MACD_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}', f'MACDs_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']):
                logger.warning(f"Could not calculate MACD for {symbol} on {timeframe}.")
                return
            df['macd'] = macd_data[f'MACD_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']
            df['macd_signal'] = macd_data[f'MACDs_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']
            
            if df.empty or df.iloc[-1].isnull().any():
                logger.warning(f"Latest data for {symbol} on {timeframe} contains NaN values or DataFrame is empty.")
                return
            
            latest = df.iloc[-1]
            status = self.check_market_status(
                latest['close'], latest['rsi'], latest['bb_upper'], 
                latest['bb_lower'], latest['macd'], latest['macd_signal']
            )
            
            logger.info(
                f"{symbol} ({timeframe}): Price={latest['close']:.2f}, RSI={latest['rsi']:.2f} ({status['rsi_status']}), "
                f"BB=({latest['bb_lower']:.2f}-{latest['bb_upper']:.2f}) ({status['bb_status']}), "
                f"MACD={latest['macd']:.2f}, Signal={latest['macd_signal']:.2f} ({status['macd_status']}), "
                f"Combined Status={status['overall_status']}"
            )

            # Determine notification based on settings
            should_notify = False
            signal_type_en = ""
            
            if send_all_signals and status['has_signal']:
                should_notify = True
                signal_type_en = "Individual Signal"
            elif status['has_combined_signal']:
                should_notify = True
                signal_type_en = "Combined Signal"
            
            if should_notify and self.notifier:
                emoji = "🚨" if status['has_combined_signal'] else "⚠️"
                message_type_en = status['overall_status'] if status['has_combined_signal'] else "Individual Overbought/Oversold"
                
                base_currency = symbol.split('/')[0]

                message = (
                    f"{emoji} {message_type_en} ({signal_type_en}) {emoji}\n\n"
                    f"Symbol: {base_currency}\n"
                    f"Timeframe: {timeframe}\n"
                    f"Time: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Price: {latest['close']:.2f}\n"
                    f"RSI ({params['rsi_period']}): {latest['rsi']:.2f} ({status['rsi_status']})\n"
                    f"BBands ({params['bb_period']}): Lower {latest['bb_lower']:.2f}, Upper {latest['bb_upper']:.2f} ({status['bb_status']})\n"
                    f"MACD ({params['macd_fast']}-{params['macd_slow']}-{params['macd_signal']}): MACD {latest['macd']:.2f}, Signal {latest['macd_signal']:.2f} ({status['macd_status']})"
                )
                await self.notifier.send_message(message)
                logger.info(f"Notification sent: {symbol} ({timeframe}) - {message_type_en}")

        except ccxt.NetworkError as e:
            logger.error(f"CCXT Network Error ({symbol}, {timeframe}): {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"CCXT Exchange Error ({symbol}, {timeframe}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing {symbol} ({timeframe}): {e}", exc_info=True)
    
    async def run_analysis(self, send_all_signals=False):
        """Runs the complete analysis."""
        logger.info(f"Starting Oversold/Overbought analysis task: {datetime.now()}")
        
        for symbol in SYMBOLS_TO_MONITOR:
            for timeframe, params in TIMEFRAMES_PARAMS.items():
                await self.analyze_symbol(symbol, timeframe, params, send_all_signals)
                await asyncio.sleep(2)  # Short delay between API requests