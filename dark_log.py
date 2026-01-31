# dark_log.py
import logging
import os
from datetime import datetime


class DarkLog:
    def __init__(self, name, log_dir="logs"):
        self.name = name
        self.log_dir = log_dir

        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)

        # 日志文件按天分割
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"{name}_{today}.log")

        # 配置 logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件 handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # 控制台 handler（可选）
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '[%(levelname)s] %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def exception(self, msg):
        self.logger.exception(msg)