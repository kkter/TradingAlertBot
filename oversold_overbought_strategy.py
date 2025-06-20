"""
超买超卖策略模块
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
        """检查市场状态"""
        rsi_status = ""
        bb_status = ""
        macd_status = ""
        
        if pd.isna(rsi) or pd.isna(bb_lower) or pd.isna(bb_upper) or pd.isna(macd) or pd.isna(macd_signal) or pd.isna(price):
            return {
                "rsi_status": "数据不足",
                "bb_status": "数据不足",
                "macd_status": "数据不足",
                "overall_status": "数据不足",
                "has_signal": False,
                "has_combined_signal": False
            }

        # 个别指标状态
        if rsi < 30:
            rsi_status = "超卖 (Oversold)"
        elif rsi > 70:
            rsi_status = "超买 (Overbought)"
        else:
            rsi_status = "中性 (Neutral)"
        
        if price <= bb_lower:
            bb_status = "超卖 (Oversold)"
        elif price >= bb_upper:
            bb_status = "超买 (Overbought)"
        else:
            bb_status = "中性 (Neutral)"
        
        if macd < macd_signal and macd < 0:
            macd_status = "超卖倾向 (Bearish)"
        elif macd > macd_signal and macd > 0:
            macd_status = "超买倾向 (Bullish)"
        else:
            macd_status = "中性 (Neutral)"
        
        # 检查是否有任何超买/超卖信号
        has_signal = (
            "超买" in rsi_status or "超卖" in rsi_status or
            "超买" in bb_status or "超卖" in bb_status or
            "超买倾向" in macd_status or "超卖倾向" in macd_status
        )
        
        # 综合状态判断
        signals = [rsi_status, bb_status, macd_status]
        oversold_count = signals.count("超卖 (Oversold)") + signals.count("超卖倾向 (Bearish)")
        overbought_count = signals.count("超买 (Overbought)") + signals.count("超买倾向 (Bullish)")
        
        overall_status = "综合中性 (Neutral)"
        has_combined_signal = False
        
        if oversold_count >= 2:
            overall_status = "综合超卖 (Oversold)"
            has_combined_signal = True
        elif overbought_count >= 2:
            overall_status = "综合超买 (Overbought)"
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
        """分析单个交易对"""
        try:
            logger.info(f"正在分析 {symbol} 的 {timeframe} 时间框架...")
            
            ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=params['limit'])
            if not ohlcv:
                logger.warning(f"未能获取 {symbol} 在 {timeframe} 的 OHLCV 数据。")
                return

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty:
                logger.warning(f"{symbol} 在 {timeframe} 的 DataFrame 为空。")
                return

            # 计算技术指标
            df['rsi'] = ta.rsi(df['close'], length=params['rsi_period'])
            
            bb_bands = ta.bbands(df['close'], length=params['bb_period'], std=2)
            if bb_bands is None or not all(col in bb_bands.columns for col in [f'BBU_{params["bb_period"]}_2.0', f'BBM_{params["bb_period"]}_2.0', f'BBL_{params["bb_period"]}_2.0']):
                logger.warning(f"无法为 {symbol} 在 {timeframe} 计算布林带。")
                return
            df['bb_upper'] = bb_bands[f'BBU_{params["bb_period"]}_2.0']
            df['bb_middle'] = bb_bands[f'BBM_{params["bb_period"]}_2.0']
            df['bb_lower'] = bb_bands[f'BBL_{params["bb_period"]}_2.0']
            
            macd_data = ta.macd(df['close'], fast=params['macd_fast'], slow=params['macd_slow'], signal=params['macd_signal'])
            if macd_data is None or not all(col in macd_data.columns for col in [f'MACD_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}', f'MACDs_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']):
                logger.warning(f"无法为 {symbol} 在 {timeframe} 计算 MACD。")
                return
            df['macd'] = macd_data[f'MACD_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']
            df['macd_signal'] = macd_data[f'MACDs_{params["macd_fast"]}_{params["macd_slow"]}_{params["macd_signal"]}']
            
            if df.empty or df.iloc[-1].isnull().any():
                logger.warning(f"{symbol} 在 {timeframe} 的最新数据包含 NaN 值或 DataFrame 为空。")
                return
            
            latest = df.iloc[-1]
            status = self.check_market_status(
                latest['close'], latest['rsi'], latest['bb_upper'], 
                latest['bb_lower'], latest['macd'], latest['macd_signal']
            )
            
            logger.info(
                f"{symbol} ({timeframe}): 价格={latest['close']:.2f}, RSI={latest['rsi']:.2f} ({status['rsi_status']}), "
                f"BB=({latest['bb_lower']:.2f}-{latest['bb_upper']:.2f}) ({status['bb_status']}), "
                f"MACD={latest['macd']:.2f}, Signal={latest['macd_signal']:.2f} ({status['macd_status']}), "
                f"综合状态={status['overall_status']}"
            )

            # 根据设置发送通知
            should_notify = False
            signal_type = ""
            
            if send_all_signals and status['has_signal']:
                should_notify = True
                signal_type = "单项信号"
            elif status['has_combined_signal']:
                should_notify = True
                signal_type = "综合信号"
            
            if should_notify and self.notifier:
                emoji = "🚨" if status['has_combined_signal'] else "⚠️"
                message_type = status['overall_status'] if status['has_combined_signal'] else "单项超买/超卖"
                
                message = (
                    f"{emoji} {message_type} 信号 ({signal_type}) {emoji}\n\n"
                    f"交易对: {symbol}\n"
                    f"时间框架: {timeframe}\n"
                    f"时间: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"当前价格: {latest['close']:.2f}\n"
                    f"RSI ({params['rsi_period']}): {latest['rsi']:.2f} ({status['rsi_status']})\n"
                    f"布林带 ({params['bb_period']}): 下轨 {latest['bb_lower']:.2f}, 上轨 {latest['bb_upper']:.2f} ({status['bb_status']})\n"
                    f"MACD ({params['macd_fast']}-{params['macd_slow']}-{params['macd_signal']}): MACD {latest['macd']:.2f}, 信号 {latest['macd_signal']:.2f} ({status['macd_status']})"
                )
                await self.notifier.send_message(message)
                logger.info(f"已发送通知: {symbol} ({timeframe}) - {message_type}")

        except ccxt.NetworkError as e:
            logger.error(f"CCXT 网络错误 ({symbol}, {timeframe}): {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"CCXT 交易所错误 ({symbol}, {timeframe}): {e}")
        except Exception as e:
            logger.error(f"分析 {symbol} ({timeframe}) 时发生意外错误: {e}", exc_info=True)
    
    async def run_analysis(self, send_all_signals=False):
        """运行完整分析"""
        logger.info(f"开始超买超卖分析任务: {datetime.now()}")
        
        for symbol in SYMBOLS_TO_MONITOR:
            for timeframe, params in TIMEFRAMES_PARAMS.items():
                await self.analyze_symbol(symbol, timeframe, params, send_all_signals)
                await asyncio.sleep(2)  # API 请求之间短暂延迟