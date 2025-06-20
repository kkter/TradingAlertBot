"""
Telegram Bot 通知模块
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import SYMBOLS_TO_MONITOR

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.application = None
        
    def initialize(self):
        """初始化机器人"""
        if not self.bot_token:
            logger.critical("错误：TELEGRAM_BOT_TOKEN 未在 .env 文件中设置。机器人无法启动。")
            return False
        if not self.chat_id:
            logger.warning("警告：TELEGRAM_CHAT_ID 未在 .env 文件中设置。机器人将运行，但无法发送通知。")
        
        self.application = Application.builder().token(self.bot_token).build()
        self.application.add_handler(CommandHandler("start", self.start_command))
        return True
    
    async def send_message(self, message: str):
        """发送消息到指定聊天"""
        if not self.chat_id:
            logger.error("TELEGRAM_CHAT_ID 未设置，无法发送通知。")
            return
        
        try:
            await self.application.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info("消息发送成功")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 /start 命令"""
        user = update.effective_user
        monitored_symbols_str = ", ".join(SYMBOLS_TO_MONITOR)
        await update.message.reply_html(
            rf"你好 {user.mention_html()}!",
        )
        await update.message.reply_text(
            f"我已经开始监控以下交易对：{monitored_symbols_str}\n"
            f"当出现超买、超卖或EMA突破信号时，我会发送通知。\n"
            f"监控任务默认每小时运行一次。"
        )
    
    def add_job(self, callback, interval=3600, first=10):
        """添加定时任务"""
        if self.application and self.application.job_queue:
            self.application.job_queue.run_repeating(callback, interval=interval, first=first)
    
    def run(self):
        """启动机器人"""
        if self.application:
            logger.info("机器人已启动，正在轮询更新...")
            self.application.run_polling()