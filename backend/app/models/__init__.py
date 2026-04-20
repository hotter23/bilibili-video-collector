from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .task import Task, TaskStatus
from .metadata import VideoMetadata
from .metrics import Metrics
from .error_log import ErrorLog
from .system_config import SystemConfig

__all__ = [
    'db', 'Task', 'TaskStatus', 'VideoMetadata', 
    'Metrics', 'ErrorLog', 'SystemConfig'
]
