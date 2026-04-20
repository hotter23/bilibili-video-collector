# B站视频采集系统

基于 Python Flask + Vue3 的B站视频批量采集与管理系统

## 功能特性

- ✅ 任务化管理：支持单任务和批量任务创建
- 📊 可视化看板：成功率、耗时、失败分布等统计
- 📈 实时进度：任务执行进度实时更新
- ⚡ 断点续传：下载中断可续传
- 🔄 自动重试：失败任务自动重试
- 🎯 多清晰度：支持4K/1080P60/1080P/720P等
- 🛡️ 合规设计：尊重robots.txt，限速控制

## 技术栈

- **后端**: Python 3.12 + Flask + SQLAlchemy
- **前端**: Vue 3 + Element Plus + ECharts
- **数据库**: MySQL 8.0
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
- MySQL 8.0+
- FFmpeg

### 2. 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置数据库（修改 config.py 中的 DATABASE_URL）
# 创建数据库
# mysql -u root -p -e "CREATE DATABASE bilibili_collector CHARACTER SET utf8mb4;"

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

## API 接口

### 任务管理

| 方法 | 路径                  | 说明         |
| ---- | --------------------- | ------------ |
| POST | /api/tasks            | 创建任务     |
| GET  | /api/tasks            | 获取任务列表 |
| GET  | /api/tasks/:id        | 获取任务详情 |
| POST | /api/tasks/:id/cancel | 取消任务     |
| POST | /api/tasks/:id/retry  | 重试任务     |
| POST | /api/tasks/batch      | 批量创建     |
| GET  | /api/tasks/stats      | 获取统计     |

### 指标管理

| 方法 | 路径                   | 说明     |
| ---- | ---------------------- | -------- |
| GET  | /api/metrics/dashboard | 看板数据 |
| GET  | /api/metrics/trend     | 趋势数据 |
| GET  | /api/metrics/task/:id  | 任务指标 |

## 配置说明

| 配置项                | 说明           | 默认值 |
| --------------------- | -------------- | ------ |
| MAX_CONCURRENT_TASKS  | 最大并发数     | 3      |
| DEFAULT_RATE_LIMIT_MS | 请求间隔(毫秒) | 1000   |
| DEFAULT_MAX_RETRIES   | 最大重试次数   | 3      |

## 开发笔记

### B站视频下载原理

1. 从URL提取BV号
2. 调用B站API获取视频信息(CID)
3. 调用播放API获取媒体地址(m3u8/dash)
4. 下载视频流和音频流
5. FFmpeg合并为MP4

### 注意事项

- 默认只支持公开视频，高清晰度需要登录Cookie
- 请遵守B站用户协议，合理使用
- 建议设置合理的请求间隔(≥1000ms)
- 定期清理临时目录和日志
