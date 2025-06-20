"""
主程序 - 整合所有策略和通知
"""

import asyncio
import logging
from telegram.ext import ContextTypes
from telegram_bot import TelegramNotifier
from oversold_overbought_strategy import OversoldOverboughtStrategy
from ema_strategy import EMAStrategy

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingAlertBot:
    def __init__(self):
        self.notifier = TelegramNotifier()
        self.oversold_strategy = OversoldOverboughtStrategy(self.notifier)
        self.ema_strategy = EMAStrategy(self.notifier)
    
    async def combined_analysis_job(self, context: ContextTypes.DEFAULT_TYPE):
        """组合分析任务"""
        logger.info("开始执行组合分析任务")
        
        # 运行超买超卖分析（只发送综合信号）
        await self.oversold_strategy.run_analysis(send_all_signals=False)
        
        # 运行 EMA 分析
        await self.ema_strategy.run_analysis()
        
        logger.info("组合分析任务完成")
    
    async def all_signals_analysis_job(self, context: ContextTypes.DEFAULT_TYPE):
        """所有信号分析任务（可选，用于测试）"""
        logger.info("开始执行所有信号分析任务")
        
        # 运行超买超卖分析（发送所有信号）
        await self.oversold_strategy.run_analysis(send_all_signals=True)
        
        # 运行 EMA 分析
        await self.ema_strategy.run_analysis()
        
        logger.info("所有信号分析任务完成")
    
    def run(self):
        """启动机器人"""
        if not self.notifier.initialize():
            return
        
        # 添加定时任务
        # 主要任务：每小时运行一次，只发送综合信号
        self.notifier.add_job(self.combined_analysis_job, interval=3600, first=10)
        
        # 可选：测试用任务，发送所有信号（注释掉正常使用）
        # self.notifier.add_job(self.all_signals_analysis_job, interval=60, first=10)
        
        # 启动机器人
        self.notifier.run()

def main():
    bot = TradingAlertBot()
    bot.run()

if __name__ == '__main__':
    main()