import os
import sys
from datetime import timedelta

def get_base_dir():
    """获取应用基础目录，兼容打包后的场景"""
    if getattr(sys, 'frozen', False):
        # 打包后的场景
        return os.path.dirname(sys.executable)
    # 开发环境
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bilibili-collector-secret-key-2024')

    # 数据库配置 - 使用绝对路径
    db_path = os.path.join(BASE_DIR, 'bilibili_collector.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # 下载配置 - 使用绝对路径
    DOWNLOAD_TEMP_DIR = os.environ.get('TEMP_DIR', os.path.join(BASE_DIR, 'temp'))
    DOWNLOAD_OUTPUT_DIR = os.environ.get('OUTPUT_DIR', os.path.join(BASE_DIR, 'downloads'))

    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', '3'))
    DEFAULT_RATE_LIMIT_MS = int(os.environ.get('DEFAULT_RATE_LIMIT_MS', '1000'))
    DEFAULT_MAX_RETRIES = int(os.environ.get('DEFAULT_MAX_RETRIES', '3'))

    # 调度配置
    SCHEDULER_API_ENABLED = True

    # 分块下载配置
    CHUNK_SIZE = 1024 * 1024

    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
