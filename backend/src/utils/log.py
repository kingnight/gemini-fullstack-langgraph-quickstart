import logging
import sys
import inspect
import os
from datetime import datetime
from typing import Optional

# ANSI颜色代码
COLORS = {
    'RESET': '\033[0m',
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
}

# 日志级别对应的颜色
LEVEL_COLORS = {
    'DEBUG': COLORS['BLUE'],
    'INFO': COLORS['GREEN'],
    'WARNING': COLORS['YELLOW'],
    'ERROR': COLORS['RED'],
    'CRITICAL': COLORS['MAGENTA'],
}

def get_caller_info():
    """获取调用者的文件名、函数名和行号"""
    # 获取调用栈
    stack = inspect.stack()
    # 跳过log.py中的函数调用
    for frame in stack[2:]:  # 从第3个frame开始，跳过log函数和便捷函数
        if not frame.filename.endswith('log.py'):
            return frame.filename, frame.function, frame.lineno
    # 如果没找到，返回最后一个调用者的信息
    return stack[-1].filename, stack[-1].function, stack[-1].lineno

def log(
    message: str,
    level: str = 'INFO',
    color: Optional[str] = None,
    show_caller: bool = True
) -> None:
    """
    输出带颜色的日志信息
    
    Args:
        message: 日志消息
        level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        color: 自定义颜色 (可选)
        show_caller: 是否显示调用者信息
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    level = level.upper()
    
    # 获取调用者信息
    caller_info = ""
    if show_caller:
        filename, function_name, lineno = get_caller_info()
        # 使用相对路径显示文件名
        filename = os.path.relpath(filename)
        caller_info = f"[{filename}:{function_name}:{lineno}]"
    
    # 确定颜色
    log_color = color if color else LEVEL_COLORS.get(level, COLORS['RESET'])
    
    # 构建日志消息
    log_message = f"{log_color}[{timestamp}] [{level}] {caller_info} {message}{COLORS['RESET']}"
    
    # 输出到控制台
    print(log_message)
    
    # 同时写入到日志文件
    logging.basicConfig(
        filename='app.log',
        level=logging.INFO,  # 将默认级别设置为 INFO
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.log(
        getattr(logging, level),
        f"{caller_info} {message}"
    )

# 便捷函数
def debug(message: str, color: Optional[str] = None) -> None:
    log(message, 'DEBUG', color)

def info(message: str, color: Optional[str] = None) -> None:
    log(message, 'INFO', color)

def warning(message: str, color: Optional[str] = None) -> None:
    log(message, 'WARNING', color)

def error(message: str, color: Optional[str] = None) -> None:
    log(message, 'ERROR', color)

def critical(message: str, color: Optional[str] = None) -> None:
    log(message, 'CRITICAL', color)
