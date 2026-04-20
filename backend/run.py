#!/usr/bin/env python3
"""
B站视频采集系统 - 启动入口
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# 创建应用
app = create_app(os.environ.get('FLASK_CONFIG', 'development'))


def main():
    """启动服务器"""
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        B站视频采集系统  Bilibili Video Collector          ║
║                                                           ║
║        服务地址: http://{host}:{port}                       ║
║        API文档:  http://{host}:{port}/                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
