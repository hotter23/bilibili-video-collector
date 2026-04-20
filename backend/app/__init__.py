"""
B站视频采集系统 - Flask应用工厂
"""
import os
from flask import Flask
from flask_cors import CORS

from .config import config
from .models import db

_config_instance = None

def get_config():
    """获取配置实例"""
    global _config_instance
    if _config_instance is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
        _config_instance = config[config_name]
    return _config_instance


def create_app(config_name=None):
    """
    Flask应用工厂
    
    Args:
        config_name: 配置名称，默认从环境变量读取或使用'default'
    """
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app.config.from_object(config[config_name])
    
    # 初始化CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 初始化默认配置
        _init_default_configs()
    
    # 注册蓝图
    from .api import task_bp, metrics_bp, config_bp
    app.register_blueprint(task_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(config_bp)

    @app.route('/test')
    def test_route():
        return {'test': 'ok'}

    print(f'[DEBUG] Registered routes:')
    for rule in app.url_map.iter_rules():
        print(f'  {rule.endpoint}: {rule.rule}')
    
    # 健康检查端点
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'service': 'bilibili-collector'}
    
    # 根路径
    @app.route('/')
    def index():
        return {
            'service': 'Bilibili Video Collector API',
            'version': '1.0.0',
            'endpoints': {
                'tasks': '/api/tasks',
                'metrics': '/api/metrics',
                'config': '/api/config'
            }
        }
    
    # 启动任务调度器
    from .engine import task_scheduler
    task_scheduler.start(app)
    
    return app


def _init_default_configs():
    """初始化默认配置"""
    from .models import SystemConfig
    
    defaults = [
        ('max_concurrent_tasks', '3', '最大并发任务数'),
        ('default_rate_limit_ms', '1000', '默认请求间隔(毫秒)'),
        ('default_max_retries', '3', '默认最大重试次数'),
        ('default_quality', '1080P', '默认视频清晰度'),
        ('download_temp_dir', '/tmp/bilibili-downloads', '临时下载目录'),
        ('download_output_dir', './downloads', '最终输出目录'),
    ]
    
    for key, value, desc in defaults:
        existing = SystemConfig.query.filter_by(config_key=key).first()
        if not existing:
            config = SystemConfig(
                config_key=key,
                config_value=value,
                description=desc
            )
            db.session.add(config)
    
    db.session.commit()
