from . import db
from datetime import datetime


class VideoMetadata(db.Model):
    """视频元数据表 - 保存解析阶段得到的视频基本信息"""
    __tablename__ = 'video_metadata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(64), db.ForeignKey('tasks.id'), nullable=False, comment='关联任务ID')
    bvid = db.Column(db.String(32), comment='B站视频号')
    title = db.Column(db.String(255), comment='视频标题')
    author = db.Column(db.String(100), comment='作者')
    duration = db.Column(db.Integer, comment='时长(秒)')
    quality = db.Column(db.String(20), comment='实际下载清晰度')
    cover_url = db.Column(db.String(512), comment='封面图片地址')
    output_path = db.Column(db.String(256), comment='最终文件路径')
    file_size = db.Column(db.BigInteger, comment='文件大小(字节)')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='记录创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'bvid': self.bvid,
            'title': self.title,
            'author': self.author,
            'duration': self.duration,
            'quality': self.quality,
            'cover_url': self.cover_url,
            'output_path': self.output_path,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<VideoMetadata {self.bvid} - {self.title}>'
