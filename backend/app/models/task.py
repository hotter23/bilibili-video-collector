from . import db
from datetime import datetime
import uuid
import enum


class TaskStatus(enum.Enum):
    """任务状态枚举"""
    created = 'created'           # 已创建
    queued = 'queued'             # 排队中
    parsing = 'parsing'           # 解析中
    downloading = 'downloading'   # 下载中
    merging = 'merging'           # 合并中
    completed = 'completed'       # 已完成
    failed = 'failed'             # 已失败
    cancelled = 'cancelled'       # 已取消


class Task(db.Model):
    """任务表 - 记录视频采集任务"""
    __tablename__ = 'tasks'

    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = db.Column(db.String(512), nullable=False, comment='视频链接')
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.created, comment='任务状态')
    quality = db.Column(db.String(32), default='1080P', comment='清晰度档位')
    concurrency = db.Column(db.Integer, default=3, comment='并发数')
    rate_limit_ms = db.Column(db.Integer, default=1000, comment='限速间隔(毫秒)')
    max_retries = db.Column(db.Integer, default=3, comment='最大重试次数')
    output_dir = db.Column(db.String(256), comment='输出目录')
    progress = db.Column(db.Integer, default=0, comment='进度 0-100')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    started_at = db.Column(db.DateTime, comment='开始执行时间')
    finished_at = db.Column(db.DateTime, comment='结束时间')
    cancelled = db.Column(db.Integer, default=0, comment='取消标记: 0否 1是')
    
    # 关系
    video_metadata = db.relationship('VideoMetadata', backref='task', lazy=True, cascade='all, delete-orphan')
    metrics = db.relationship('Metrics', backref='task', lazy=True, cascade='all, delete-orphan')
    error_logs = db.relationship('ErrorLog', backref='task', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'url': self.url,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'quality': self.quality,
            'concurrency': self.concurrency,
            'rate_limit_ms': self.rate_limit_ms,
            'max_retries': self.max_retries,
            'output_dir': self.output_dir,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'cancelled': self.cancelled,
            'metadata': self.video_metadata[0].to_dict() if self.video_metadata else None
        }

    def __repr__(self):
        return f'<Task {self.id} [{self.status.value}]>'
