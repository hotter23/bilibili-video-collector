from . import db
from datetime import datetime
import enum


class ErrorStage(enum.Enum):
    """错误发生阶段"""
    parse = 'parse'       # 解析阶段
    download = 'download' # 下载阶段
    merge = 'merge'       # 合并阶段


class ErrorType(enum.Enum):
    """错误类型分类"""
    network_timeout = 'network_timeout'       # 网络超时
    parse_failed = 'parse_failed'             # 解析失败
    permission_denied = 'permission_denied'   # 权限不足
    merge_failed = 'merge_failed'             # 合并失败
    unknown = 'unknown'                       # 未知错误


class ErrorLog(db.Model):
    """错误日志表 - 保存任务失败或异常时的关键信息"""
    __tablename__ = 'error_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(64), db.ForeignKey('tasks.id'), nullable=False, comment='关联任务ID')
    stage = db.Column(db.Enum(ErrorStage), comment='发生阶段: parse/download/merge')
    status_code = db.Column(db.String(10), comment='HTTP状态码')
    error_type = db.Column(db.Enum(ErrorType), comment='错误类型')
    error_msg = db.Column(db.Text, comment='错误消息摘要')
    stack_summary = db.Column(db.Text, comment='堆栈摘要')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='记录时间')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'stage': self.stage.value if isinstance(self.stage, ErrorStage) else self.stage,
            'status_code': self.status_code,
            'error_type': self.error_type.value if isinstance(self.error_type, ErrorType) else self.error_type,
            'error_msg': self.error_msg,
            'stack_summary': self.stack_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<ErrorLog {self.task_id} [{self.error_type.value}]>'
