"""
EMA 突破策略模块
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
        self.exchange = ccxt.binance()
        self.notifier = notifier
        # 存储上一次的价格位置，用于检测突破
        self.last_positions = {}
    
    def check_ema_breakthrough(self, df, ema_periods):
        """检查 EMA 突破"""
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
            
            # 检查向上突破
            if (previous_price <= previous_ema and current_price > current_ema):
                breakthroughs.append({
                    'type': '向上突破',
                    'ema_period': period,
                    'price': current_price,
                    'ema_value': current_ema,
                    'emoji': '🚀'
                })
            
            # 检查向下跌破
            elif (previous_price >= previous_ema and current_price < current_ema):
                breakthroughs.append({
                    'type': '向下跌破',
                    'ema_period': period,
                    'price': current_price,
                    'ema_value': current_ema,
                    'emoji': '📉'
                })
        
        return breakthroughs
    
    async def analyze_symbol(self, symbol, timeframe):
        """分析单个交易对的 EMA"""
        try:
            logger.info(f"正在分析 {symbol} 的 {timeframe} EMA 突破...")
            
            # 使用配置文件中的 limit
            limit = TIMEFRAMES_PARAMS[timeframe]['limit']
            ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"未能获取 {symbol} 在 {timeframe} 的 OHLCV 数据。")
                return

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if df.empty or len(df) < max(EMA_PERIODS):
                logger.warning(f"{symbol} 在 {timeframe} 的数据不足以计算 EMA。")
                return

            # 计算所有 EMA
            for period in EMA_PERIODS:
                df[f'ema_{period}'] = ta.ema(df['close'], length=period)
            
            # 检查突破
            breakthroughs = self.check_ema_breakthrough(df, EMA_PERIODS)
            
            if breakthroughs and self.notifier:
                latest = df.iloc[-1]
                
                for breakthrough in breakthroughs:
                    message = (
                        f"{breakthrough['emoji']} EMA {breakthrough['type']} 信号 {breakthrough['emoji']}\n\n"
                        f"交易对: {symbol}\n"
                        f"时间框架: {timeframe}\n"
                        f"时间: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                        f"当前价格: {breakthrough['price']:.2f}\n"
                        f"EMA{breakthrough['ema_period']}: {breakthrough['ema_value']:.2f}\n"
                        f"突破类型: {breakthrough['type']}"
                    )
                    
                    await self.notifier.send_message(message)
                    logger.info(f"已发送 EMA 通知: {symbol} ({timeframe}) - EMA{breakthrough['ema_period']} {breakthrough['type']}")

        except ccxt.NetworkError as e:
            logger.error(f"CCXT 网络错误 ({symbol}, {timeframe}): {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"CCXT 交易所错误 ({symbol}, {timeframe}): {e}")
        except Exception as e:
            logger.error(f"分析 {symbol} ({timeframe}) EMA 时发生意外错误: {e}", exc_info=True)
    
    async def run_analysis(self):
        """运行完整的 EMA 分析"""
        logger.info(f"开始 EMA 突破分析任务: {datetime.now()}")
        
        for symbol in SYMBOLS_TO_MONITOR:
            for timeframe in EMA_TIMEFRAMES:
                await self.analyze_symbol(symbol, timeframe)
                await asyncio.sleep(2)  # API 请求之间短暂延迟