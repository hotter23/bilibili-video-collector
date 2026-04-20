import re
import hashlib


def sanitize_cookie(cookie_string):
    """
    Cookie脱敏：日志中只记录长度和哈希摘要
    
    Args:
        cookie_string: 原始Cookie字符串
    
    Returns:
        脱敏后的字典 {length, hash}
    """
    if not cookie_string:
        return None
    
    return {
        'length': len(cookie_string),
        'hash': hashlib.sha256(cookie_string.encode()).hexdigest()[:16]
    }


def validate_bilibili_url(url):
    """
    验证B站视频URL格式
    
    Args:
        url: 待验证的URL
    
    Returns:
        True or ValueError
    
    Raises:
        ValueError: URL格式无效
    """
    if not url:
        raise ValueError('URL不能为空')
    
    # B站视频URL正则
    pattern = r'^https?://(www\.bilibili\.com/video/|bilibili\.com/video/)BV[\w]+'
    if not re.match(pattern, url):
        raise ValueError('仅支持B站公开视频链接，格式如: https://www.bilibili.com/video/BVxxxx')
    
    return True


def safe_output_path(user_path, base_dir):
    """
    安全路径验证：防止路径穿越攻击
    
    Args:
        user_path: 用户提供的相对路径
        base_dir: 基础目录
    
    Returns:
        安全的绝对路径
    
    Raises:
        ValueError: 路径不安全
    """
    import os
    
    # 清理路径
    user_path = user_path.strip()
    if not user_path:
        raise ValueError('输出路径不能为空')
    
    # 禁止包含 .. 等上级目录引用
    if '..' in user_path or user_path.startswith('/'):
        raise ValueError('不允许的路径格式')
    
    # 构建绝对路径
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(os.path.join(abs_base, user_path))
    
    # 确保路径在base_dir范围内
    if not abs_path.startswith(abs_base):
        raise ValueError('不允许的输出路径：禁止访问base_dir以外的文件')
    
    return abs_path


def classify_error(status_code, error_msg):
    """
    根据HTTP状态码和错误消息分类错误类型
    
    Returns:
        ErrorType枚举值
    """
    from app.models.error_log import ErrorType
    
    status_code = str(status_code) if status_code else ''
    
    if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
        return ErrorType.network_timeout
    elif status_code == '403' or '权限' in error_msg or 'permission' in error_msg.lower():
        return ErrorType.permission_denied
    elif status_code == '429' or '频率' in error_msg or 'rate limit' in error_msg.lower():
        return ErrorType.network_timeout  # 频率限制也归类为网络问题
    elif '解析' in error_msg or 'parse' in error_msg.lower():
        return ErrorType.parse_failed
    elif '合并' in error_msg or 'merge' in error_msg.lower() or 'ffmpeg' in error_msg.lower():
        return ErrorType.merge_failed
    else:
        return ErrorType.unknown
