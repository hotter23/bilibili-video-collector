# API蓝图模块
from .task import task_bp
from .metrics import metrics_bp
from .config import config_bp

__all__ = ['task_bp', 'metrics_bp', 'config_bp']
