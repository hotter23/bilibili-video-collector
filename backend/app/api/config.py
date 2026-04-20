from flask import Blueprint, request, current_app
from app.models import db, SystemConfig
from app.utils.response import api_success, api_error
from datetime import datetime

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('', methods=['GET'])
def get_configs():
    """
    获取所有系统配置
    
    返回配置列表
    """
    try:
        configs = SystemConfig.query.all()
        return api_success({
            'items': [c.to_dict() for c in configs]
        })
    except Exception as e:
        return api_error(500, f'获取配置失败: {str(e)}')


@config_bp.route('/<key>', methods=['GET'])
def get_config(key):
    """
    获取指定配置
    
    Args:
        key: 配置键
    """
    try:
        config = SystemConfig.query.filter_by(config_key=key).first()
        if not config:
            return api_error(404, f'配置项不存在: {key}')
        return api_success(config.to_dict())
    except Exception as e:
        return api_error(500, f'获取配置失败: {str(e)}')


@config_bp.route('', methods=['POST'])
def create_or_update_config():
    """
    创建或更新系统配置
    
    请求体:
    {
        "config_key": "max_concurrent",
        "config_value": "5",
        "description": "最大并发任务数"
    }
    """
    try:
        data = request.get_json() or {}
        config_key = data.get('config_key', '').strip()
        config_value = data.get('config_value', '')
        description = data.get('description', '')
        
        if not config_key:
            return api_error(400, '配置键不能为空')
        
        # 检查是否已存在
        config = SystemConfig.query.filter_by(config_key=config_key).first()
        
        if config:
            # 更新
            config.config_value = config_value
            config.description = description or config.description
            config.updated_at = datetime.now()
        else:
            # 创建
            config = SystemConfig(
                config_key=config_key,
                config_value=config_value,
                description=description
            )
            db.session.add(config)
        
        db.session.commit()
        
        return api_success(config.to_dict(), '配置保存成功')
        
    except Exception as e:
        return api_error(500, f'保存配置失败: {str(e)}')


@config_bp.route('/batch', methods=['POST'])
def batch_update_configs():
    """
    批量更新配置
    
    请求体:
    {
        "configs": [
            {"config_key": "key1", "config_value": "value1"},
            {"config_key": "key2", "config_value": "value2"}
        ]
    }
    """
    try:
        data = request.get_json() or {}
        configs_data = data.get('configs', [])
        
        if not configs_data:
            return api_error(400, '配置列表不能为空')
        
        updated = []
        for item in configs_data:
            config_key = item.get('config_key', '').strip()
            config_value = item.get('config_value', '')
            description = item.get('description', '')
            
            if not config_key:
                continue
            
            config = SystemConfig.query.filter_by(config_key=config_key).first()
            if config:
                config.config_value = config_value
                config.updated_at = datetime.now()
            else:
                config = SystemConfig(
                    config_key=config_key,
                    config_value=config_value,
                    description=description
                )
                db.session.add(config)
            
            updated.append(config_key)
        
        db.session.commit()
        
        return api_success({
            'updated_count': len(updated),
            'updated_keys': updated
        }, f'成功更新 {len(updated)} 个配置项')
        
    except Exception as e:
        return api_error(500, f'批量更新失败: {str(e)}')


@config_bp.route('/defaults', methods=['GET'])
def get_default_configs():
    """
    获取默认配置（系统内置）
    
    这些是系统的默认配置，可以通过配置管理页面修改
    """
    defaults = {
        'max_concurrent_tasks': {
            'value': str(current_app.config.get('MAX_CONCURRENT_TASKS', 3)),
            'description': '最大并发任务数',
            'type': 'integer',
            'min': 1,
            'max': 10
        },
        'default_rate_limit_ms': {
            'value': str(current_app.config.get('DEFAULT_RATE_LIMIT_MS', 1000)),
            'description': '默认限速间隔（毫秒）',
            'type': 'integer',
            'min': 100,
            'max': 10000
        },
        'default_max_retries': {
            'value': str(current_app.config.get('DEFAULT_MAX_RETRIES', 3)),
            'description': '默认最大重试次数',
            'type': 'integer',
            'min': 0,
            'max': 10
        },
        'download_temp_dir': {
            'value': current_app.config.get('DOWNLOADTemp_DIR', '/tmp/bilibili-downloads'),
            'description': '下载临时目录',
            'type': 'string'
        },
        'download_output_dir': {
            'value': current_app.config.get('DOWNLOAD_OUTPUT_DIR', './downloads'),
            'description': '下载输出目录',
            'type': 'string'
        },
        'default_quality': {
            'value': '1080P',
            'description': '默认清晰度',
            'type': 'select',
            'options': ['4K', '1080P60', '1080P', '720P', '480P', '360P']
        }
    }
    
    return api_success(defaults)


@config_bp.route('/validate/<key>', methods=['GET'])
def validate_config(key, value):
    """
    验证配置值是否有效
    
    Args:
        key: 配置键
        value: 待验证的值
    """
    try:
        value = request.args.get('value', '')
        
        # 获取默认值定义
        defaults = get_default_configs().get_json()['data']
        
        if key not in defaults:
            return api_error(404, f'未知配置项: {key}')
        
        config_def = defaults[key]
        config_type = config_def.get('type', 'string')
        
        # 类型验证
        if config_type == 'integer':
            try:
                int_value = int(value)
                
                # 范围检查
                if 'min' in config_def and int_value < config_def['min']:
                    return api_error(400, f'值不能小于 {config_def["min"]}')
                if 'max' in config_def and int_value > config_def['max']:
                    return api_error(400, f'值不能大于 {config_def["max"]}')
                
                return api_success({'valid': True, 'value': int_value})
                
            except ValueError:
                return api_error(400, '必须是整数')
        
        elif config_type == 'select':
            if value not in config_def.get('options', []):
                return api_error(400, f'必须是以下值之一: {config_def["options"]}')
            return api_success({'valid': True, 'value': value})
        
        else:
            return api_success({'valid': True, 'value': value})
            
    except Exception as e:
        return api_error(500, f'验证失败: {str(e)}')
