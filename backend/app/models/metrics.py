from . import db
from datetime import datetime


class Metrics(db.Model):
    """运行指标表 - 记录任务执行过程的性能数据"""
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(64), db.ForeignKey('tasks.id'), nullable=False, comment='关联任务ID')
    parse_time_ms = db.Column(db.Integer, comment='解析耗时(毫秒)')
    download_time_ms = db.Column(db.Integer, comment='下载耗时(毫秒)')
    merge_time_ms = db.Column(db.Integer, comment='合并耗时(毫秒)')
    total_time_ms = db.Column(db.Integer, comment='端到端总耗时(毫秒)')
    download_bytes = db.Column(db.BigInteger, comment='下载总字节数')
    avg_speed_bps = db.Column(db.BigInteger, comment='平均速率 Bytes/s')
    peak_speed_bps = db.Column(db.BigInteger, comment='峰值速率 Bytes/s')
    retry_count = db.Column(db.Integer, default=0, comment='实际重试次数')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='记录创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'parse_time_ms': self.parse_time_ms,
            'download_time_ms': self.download_time_ms,
            'merge_time_ms': self.merge_time_ms,
            'total_time_ms': self.total_time_ms,
            'download_bytes': self.download_bytes,
            'avg_speed_bps': self.avg_speed_bps,
            'peak_speed_bps': self.peak_speed_bps,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Metrics {self.task_id} - {self.total_time_ms}ms>'
