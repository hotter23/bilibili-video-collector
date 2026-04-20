from flask import Blueprint, request, jsonify, current_app
from app.models import db, Task, TaskStatus
from app.engine import task_scheduler
from app.utils.response import api_success, api_error
from app.utils.security import validate_bilibili_url
import uuid
import os

task_bp = Blueprint('task', __name__, url_prefix='/api/tasks')


@task_bp.route('', methods=['POST'])
def create_task():
    """
    创建新任务
    
    请求体:
    {
        "url": "https://www.bilibili.com/video/BVxxxx",
        "quality": "1080P",       // 可选，默认1080P
        "cookies": "SESSDATA=...", // 可选，登录Cookie
        "concurrency": 3,          // 可选，默认3
        "rate_limit_ms": 1000,     // 可选，默认1000ms
        "max_retries": 3,          // 可选，默认3
        "output_dir": "./downloads" // 可选，默认./downloads
    }
    """
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        
        # 验证URL
        if not url:
            return api_error(400, '视频链接不能为空')
        
        try:
            validate_bilibili_url(url)
        except ValueError as e:
            return api_error(400, str(e))
        
        # 获取配置
        quality = data.get('quality', '1080P')
        cookies = data.get('cookies')
        concurrency = data.get('concurrency', 3)
        rate_limit_ms = data.get('rate_limit_ms', 1000)
        max_retries = data.get('max_retries', 3)
        output_dir = data.get('output_dir', current_app.config.get('DOWNLOAD_OUTPUT_DIR', './downloads'))
        temp_dir = current_app.config.get('DOWNLOADTemp_DIR', '/tmp/bilibili-downloads')
        
        # 创建任务
        task = Task(
            id=str(uuid.uuid4()),
            url=url,
            status=TaskStatus.queued,
            quality=quality,
            concurrency=concurrency,
            rate_limit_ms=rate_limit_ms,
            max_retries=max_retries,
            output_dir=output_dir
        )
        
        db.session.add(task)
        db.session.commit()

        print(f'[DEBUG API] Task created: {task.id}, calling submit...')
        # 提交到调度器
        task_scheduler.submit(task.id, {
            'url': url,
            'cookies': cookies,
            'quality': quality,
            'concurrency': concurrency,
            'rate_limit_ms': rate_limit_ms,
            'max_retries': max_retries,
            'output_dir': output_dir,
            'temp_dir': temp_dir
        })
        print(f'[DEBUG API] submit called for task {task.id}')

        return api_success({
            'task_id': task.id,
            'status': task.status.value
        }, '任务创建成功'), 201
        
    except Exception as e:
        return api_error(500, f'创建任务失败: {str(e)}')


@task_bp.route('', methods=['GET'])
def list_tasks():
    """
    获取任务列表
    
    查询参数:
    - page: 页码，默认1
    - per_page: 每页数量，默认20
    - status: 筛选状态（可选）
    - keyword: 关键词搜索（可选，搜索URL）
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        keyword = request.args.get('keyword', '').strip()
        
        # 构建查询
        query = Task.query
        
        if status_filter:
            try:
                status = TaskStatus(status_filter)
                query = query.filter(Task.status == status)
            except ValueError:
                pass
        
        if keyword:
            query = query.filter(Task.url.contains(keyword))
        
        # 按创建时间倒序
        query = query.order_by(Task.created_at.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return api_success({
            'items': [t.to_dict() for t in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
        
    except Exception as e:
        return api_error(500, f'查询失败: {str(e)}')


@task_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    获取任务详情
    
    包含任务基本信息、元数据、指标和错误日志
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return api_error(404, '任务不存在')
        
        result = task.to_dict()
        
        # 附加错误日志
        if task.error_logs:
            result['errors'] = [e.to_dict() for e in task.error_logs]
        
        # 附加速度数据（如果有）
        if task.metrics:
            result['metrics'] = task.metrics[0].to_dict() if task.metrics else None
        
        return api_success(result)
        
    except Exception as e:
        return api_error(500, f'查询失败: {str(e)}')


@task_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        task = Task.query.get(task_id)
        if not task:
            return api_error(404, '任务不存在')
        
        # 只有排队中或执行中的任务可以取消
        if task.status not in [TaskStatus.queued, TaskStatus.parsing, 
                               TaskStatus.downloading, TaskStatus.merging]:
            return api_error(400, f'当前状态不允许取消: {task.status.value}')
        
        task.status = TaskStatus.cancelled
        task.cancelled = 1
        task.finished_at = db.func.now()
        db.session.commit()
        
        return api_success(message='任务已取消')
        
    except Exception as e:
        return api_error(500, f'取消失败: {str(e)}')


@task_bp.route('/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """
    重试失败任务
    
    重新执行失败的任务，会清理之前的临时文件
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return api_error(404, '任务不存在')
        
        if task.status not in [TaskStatus.failed, TaskStatus.cancelled]:
            return api_error(400, f'只有失败或取消的任务可以重试，当前状态: {task.status.value}')
        
        # 重置任务状态
        task.status = TaskStatus.queued
        task.progress = 0
        task.started_at = None
        task.finished_at = None
        task.cancelled = 0
        db.session.commit()
        
        # 重新提交到调度器
        task_scheduler.submit(task.id, {
            'url': task.url,
            'cookies': None,  # 需要重新提供
            'quality': task.quality,
            'concurrency': task.concurrency,
            'rate_limit_ms': task.rate_limit_ms,
            'max_retries': task.max_retries,
            'output_dir': task.output_dir,
            'temp_dir': current_app.config.get('DOWNLOADTemp_DIR', '/tmp/bilibili-downloads')
        })
        
        return api_success(message='任务已重新提交')
        
    except Exception as e:
        return api_error(500, f'重试失败: {str(e)}')


@task_bp.route('/batch', methods=['POST'])
def batch_create_tasks():
    """
    批量创建任务
    
    请求体:
    {
        "urls": ["url1", "url2", ...],
        "quality": "1080P",
        "cookies": "..."
    }
    """
    try:
        data = request.get_json() or {}
        urls = data.get('urls', [])
        quality = data.get('quality', '1080P')
        cookies = data.get('cookies')
        output_dir = data.get('output_dir', current_app.config.get('DOWNLOAD_OUTPUT_DIR', './downloads'))
        temp_dir = current_app.config.get('DOWNLOADTemp_DIR', '/tmp/bilibili-downloads')
        
        if not urls:
            return api_error(400, 'URL列表不能为空')
        
        # 去重：检查已有URL
        existing_urls = set(
            r[0] for r in db.session.query(Task.url).filter(
                Task.url.in_(urls)
            ).all()
        )
        
        created_tasks = []
        skipped_urls = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            if url in existing_urls:
                skipped_urls.append(url)
                continue
            
            try:
                validate_bilibili_url(url)
            except ValueError:
                skipped_urls.append(url)
                continue
            
            task = Task(
                id=str(uuid.uuid4()),
                url=url,
                status=TaskStatus.queued,
                quality=quality,
                output_dir=output_dir
            )
            db.session.add(task)
            
            # 立即提交到调度器
            task_scheduler.submit(task.id, {
                'url': url,
                'cookies': cookies,
                'quality': quality,
                'output_dir': output_dir,
                'temp_dir': temp_dir
            })
            
            created_tasks.append({'task_id': task.id, 'url': url})
        
        db.session.commit()
        
        return api_success({
            'created_count': len(created_tasks),
            'skipped_count': len(skipped_urls),
            'tasks': created_tasks[:100],  # 最多返回100个
            'skipped_urls': skipped_urls[:50]  # 最多返回50个
        }, f'成功创建 {len(created_tasks)} 个任务')
        
    except Exception as e:
        return api_error(500, f'批量创建失败: {str(e)}')


@task_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取任务统计信息"""
    try:
        total = Task.query.count()
        
        # 各状态数量
        status_counts = db.session.query(
            Task.status,
            db.func.count(Task.id)
        ).group_by(Task.status).all()
        
        status_map = {s.value: c for s, c in status_counts}
        
        return api_success({
            'total': total,
            'queued': status_map.get('queued', 0),
            'parsing': status_map.get('parsing', 0),
            'downloading': status_map.get('downloading', 0),
            'merging': status_map.get('merging', 0),
            'completed': status_map.get('completed', 0),
            'failed': status_map.get('failed', 0),
            'cancelled': status_map.get('cancelled', 0),
            'queue_size': task_scheduler.get_queue_size(),
            'running_count': task_scheduler.get_running_count()
        })
        
    except Exception as e:
        return api_error(500, f'获取统计失败: {str(e)}')
