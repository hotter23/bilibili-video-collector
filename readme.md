# 承接各类软件开发，微信号：hotter23 手机号:13705177381
# B站视频采集系统

基于 Python Flask + Vue3 的B站视频批量采集与管理系统

## 功能特性

- ✅ 任务化管理：支持单任务和批量任务创建
- 📊 可视化看板：成功率、耗时、失败分布等统计
- 📈 实时进度：任务执行进度实时更新
- 🔄 自动重试：失败任务自动重试

## 技术栈

- **后端**: Python 3.12 + Flask + SQLAlchemy
- **前端**: Vue 3 + Element Plus + ECharts
- **数据库**: SQLite
- **采集引擎**: requests + FFmpeg

## 项目结构

```
bilibili-video-collector/
├── backend/                 # Flask 后端
│   ├── app/
│   │   ├── api/            # REST API 路由
│   │   ├── engine/         # 采集引擎核心
│   │   │   ├── parser.py   # B站媒体解析器
│   │   │   ├── downloader.py # 分块下载器
│   │   │   ├── merger.py    # FFmpeg合并器
│   │   │   └── scheduler.py # 任务调度器
│   │   ├── models/          # SQLAlchemy 模型
│   │   └── utils/           # 工具函数
│   ├── run.py              # 启动入口
│   └── requirements.txt
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── api/            # API 接口封装
│   │   ├── views/          # 页面组件
│   │   └── router/         # 路由配置
│   └── package.json
└── docs/                   # 文档
```

## 快速开始

### 1. 环境要求

- Python 3.12+
- Node.js 18+
- SQLite
- FFmpeg

### 2. 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置数据库（修改 config.py 中的 DATABASE_URL，默认使用 SQLite）

# 启动服务
python run.py
```

### 3. 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev
```

### 4. 访问系统

- 前端地址: http://localhost:3000
- 后端API: http://localhost:5000

## 支持我
如果您觉得这个项目对您有帮助，您可以扫描以下二维码进行捐赠：

<img width="828" height="1124" alt="2757ca9078c29ccc3ced920bebd28061" src="https://github.com/user-attachments/assets/aaaa38f0-2841-4f1f-8653-c67f5f803186" />
