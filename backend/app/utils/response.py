from flask import jsonify


def api_response(code=0, message='success', data=None):
    """
    统一API响应格式
    
    Args:
        code: 状态码，0表示成功，非0表示错误
        message: 响应消息
        data: 响应数据
    
    Returns:
        Flask Response对象
    """
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    })


def api_success(data=None, message='success'):
    """成功响应"""
    return api_response(0, message, data)


def api_error(code=400, message='error', data=None):
    """错误响应"""
    return api_response(code, message, data), code if code >= 400 else 200
