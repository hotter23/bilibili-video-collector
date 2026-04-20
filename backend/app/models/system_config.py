from . import db
from datetime import datetime


class SystemConfig(db.Model):
    """系统配置表 - 保存全局配置项"""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(80), unique=True, nullable=False, comment='配置键')
    config_value = db.Column(db.String(255), comment='配置值')
    description = db.Column(db.String(256), comment='配置说明')
    updated_by = db.Column(db.String(64), comment='更新人')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<SystemConfig {self.config_key}={self.config_value}>'


class ExportRecord(db.Model):
    """导出记录表 - 记录报表导出的历史"""
    __tablename__ = 'export_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), comment='发起导出的用户')
    export_type = db.Column(db.String(30), comment='导出类型: task_list/metrics_report')
    filter_conditions = db.Column(db.Text, comment='筛选条件JSON')
    output_path = db.Column(db.String(256), comment='导出文件路径')
    status = db.Column(db.String(20), comment='状态: pending/completed/failed')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    finished_at = db.Column(db.DateTime, comment='完成时间')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'export_type': self.export_type,
            'filter_conditions': self.filter_conditions,
            'output_path': self.output_path,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None
        }

    def __repr__(self):
        return f'<ExportRecord {self.export_type} [{self.status}]>'
