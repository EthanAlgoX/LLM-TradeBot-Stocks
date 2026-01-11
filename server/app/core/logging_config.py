"""
Logging Configuration
优化的日志输出配置
"""
import logging
import sys
from typing import Any
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # 简化时间格式
        record.asctime = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        return super().format(record)


def setup_logging(level: str = "INFO", simple: bool = False):
    """
    配置日志
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        simple: 简化模式（只显示消息）
    """
    # 清除现有 handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # 创建 handler
    handler = logging.StreamHandler(sys.stdout)
    
    # 设置格式
    if simple:
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper()))
    
    # 静默第三方库日志
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取 logger"""
    return logging.getLogger(name)
