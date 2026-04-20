from flask import Blueprint, request
from app.models import db, Task, TaskStatus, Metrics, ErrorLog
from app.utils.response import api_success, api_error
from sqlalchemy import func, desc
from datetime import datetime, timedelta

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@metrics_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    获取看板数据
    
    返回:
    - 总任务数
    - 各状态任务数
    - 成功率
    - 平均耗时
    - 失败原因分布
    """
    try:
        # 基础统计
        total = Task.query.count()
        completed = Task.query.filter(Task.status == TaskStatus.completed).count()
        failed = Task.query.filter(Task.status == TaskStatus.failed).count()
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        # 获取指标统计
        metrics_stats = db.session.query(
            func.avg(Metrics.total_time_ms).label('avg_total_time'),
            func.avg(Metrics.download_time_ms).label('avg_download_time'),
            func.avg(Metrics.avg_speed_bps).label('avg_speed')
        ).filter(
            Metrics.task_id.in_(
                db.session.query(Task.id).filter(Task.status == TaskStatus.completed)
            )
        ).first()
        
        avg_duration = int(metrics_stats.avg_total_time or 0)
        avg_download_time = int(metrics_stats.avg_download_time or 0)
        avg_speed = int(metrics_stats.avg_speed or 0)
        
        # 失败原因分布
        error_dist = db.session.query(
            ErrorLog.error_type,
            func.count(ErrorLog.id).label('count')
        ).group_by(ErrorLog.error_type).all()
        
        error_distribution = {}
        for error_type, count in error_dist:
            error_distribution[error_type.value if hasattr(error_type, 'value') else error_type] = count
        
        # 计算阶段耗时占比
        parse_time_avg = db.session.query(func.avg(Metrics.parse_time_ms)).filter(
            Metrics.task_id.in_(
                db.session.query(Task.id).filter(Task.status == TaskStatus.completed)
            )
        ).scalar() or 0
        
        merge_time_avg = db.session.query(func.avg(Metrics.merge_time_ms)).filter(
            Metrics.task_id.in_(
                db.session.query(Task.id).filter(Task.status == TaskStatus.completed)
            )
        ).scalar() or 0
        
        stage_distribution = {
            'parse': int(parse_time_avg),
            'download': int(avg_download_time),
            'merge': int(merge_time_avg)
        }
        
        return api_success({
            'total': total,
            'completed': completed,
            'failed': failed,
            'success_rate': round(success_rate, 2),
            'avg_duration_ms': avg_duration,
            'avg_download_time_ms': avg_download_time,
            'avg_speed_bps': avg_speed,
            'error_distribution': error_distribution,
            'stage_distribution': stage_distribution
        })
        
    except Exception as e:
        return api_error(500, f'获取看板数据失败: {str(e)}')


@metrics_bp.route('/trend', methods=['GET'])
def get_trend():
    """
    获取趋势数据（最近N天的统计数据）
    
    查询参数:
    - days: 天数，默认7，最大30
    """
    try:
        days = request.args.get('days', 7, type=int)
        days = min(days, 30)  # 最多30天
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 按天统计
        daily_stats = db.session.query(
            func.date(Task.created_at).label('date'),
            func.count(Task.id).label('total'),
            func.sum(
                db.case(
                    (Task.status == TaskStatus.completed, 1),
                    else_=0
                )
            ).label('completed'),
            func.sum(
                db.case(
                    (Task.status == TaskStatus.failed, 1),
                    else_=0
                )
            ).label('failed')
        ).filter(
            Task.created_at >= start_date
        ).group_by(
            func.date(Task.created_at)
        ).order_by(
            func.date(Task.created_at)
        ).all()
        
        trend_data = []
        for date, total, completed, failed in daily_stats:
            success_rate = (completed / total * 100) if total > 0 else 0
            trend_data.append({
                'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
                'total': total,
                'completed': completed or 0,
                'failed': failed or 0,
                'success_rate': round(success_rate, 2)
            })
        
        return api_success({
            'days': days,
            'trend': trend_data
        })
        
    except Exception as e:
        return api_error(500, f'获取趋势数据失败: {str(e)}')


@metrics_bp.route('/task/<task_id>', methods=['GET'])
def get_task_metrics(task_id):
    """
    获取单个任务的详细指标
    """
    try:
        metrics = Metrics.query.filter_by(task_id=task_id).first()
        if not metrics:
            return api_success(None)
        
        result = metrics.to_dict()
        
        # 计算百分比
        if result['total_time_ms'] > 0:
            result['parse_percent'] = round(result['parse_time_ms'] / result['total_time_ms'] * 100, 1)
            result['download_percent'] = round(result['download_time_ms'] / result['total_time_ms'] * 100, 1)
            result['merge_percent'] = round(result['merge_time_ms'] / result['total_time_ms'] * 100, 1)
        
        # 格式化速率
        if result['avg_speed_bps']:
            result['avg_speed_mbps'] = round(result['avg_speed_bps'] / 1024 / 1024, 2)
        if result['peak_speed_bps']:
            result['peak_speed_mbps'] = round(result['peak_speed_bps'] / 1024 / 1024, 2)
        
        return api_success(result)
        
    except Exception as e:
        return api_error(500, f'获取指标失败: {str(e)}')


@metrics_bp.route('/speed-curve/<task_id>', methods=['GET'])
def get_speed_curve(task_id):
    """
    获取任务下载速度曲线
    
    返回速度采样数据，用于绘制折线图
    """
    try:
        # 这里需要从数据库或缓存获取速度采样数据
        # 暂时返回模拟数据，实际需要扩展Metrics表或使用缓存
        metrics = Metrics.query.filter_by(task_id=task_id).first()

        if not metrics:
            return api_success({
                'task_id': task_id,
                'timestamps': [],
                'speeds_bps': [],
                'speeds_mbps': []
            })
        
        # 生成模拟速度曲线数据
        # 实际实现中，应该存储每秒钟的速度采样
        import random
        timestamps = []
        speeds = []
        
        if metrics.download_time_ms > 0:
            num_points = min(60, int(metrics.download_time_ms / 1000))
            for i in range(num_points):
                # 模拟速度曲线（开始时上升，然后稳定，最后下降）
                progress = i / num_points
                base_speed = metrics.avg_speed_bps or 1024 * 1024
                speed = int(base_speed * (0.5 + 0.5 * (1 - abs(progress - 0.3) * 1.5)))
                speed = min(speed, int(metrics.peak_speed_bps * 1.2)) if metrics.peak_speed_bps else speed
                
                timestamps.append(f'+{i}s')
                speeds.append(speed)
        
        return api_success({
            'task_id': task_id,
            'timestamps': timestamps,
            'speeds_bps': speeds,
            'speeds_mbps': [round(s / 1024 / 1024, 2) for s in speeds]
        })
        
    except Exception as e:
        return api_error(500, f'获取速度曲线失败: {str(e)}')


@metrics_bp.route('/export', methods=['POST'])
def export_metrics():
    """
    导出指标报表
    
    请求体:
    {
        "type": "csv" | "json",
        "date_from": "2024-01-01",
        "date_to": "2024-01-31",
        "status": "completed"  // 可选筛选
    }
    """
    try:
        data = request.get_json() or {}
        export_type = data.get('type', 'csv')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        status_filter = data.get('status')
        
        # 构建查询
        query = db.session.query(Task).join(
            Metrics, Task.id == Metrics.task_id, isouter=True
        )
        
        if date_from:
            query = query.filter(Task.created_at >= date_from)
        if date_to:
            query = query.filter(Task.created_at <= date_to)
        if status_filter:
            try:
                query = query.filter(Task.status == TaskStatus(status_filter))
            except ValueError:
                pass
        
        tasks = query.all()
        
        # 生成导出数据
        export_data = []
        for task in tasks:
            row = task.to_dict()
            if task.metrics:
                row['metrics'] = task.metrics[0].to_dict()
            export_data.append(row)
        
        if export_type == 'csv':
            # 生成CSV
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                '任务ID', 'URL', '状态', '创建时间', 
                '解析耗时', '下载耗时', '合并耗时', '总耗时',
                '平均速度', '峰值速度', '重试次数'
            ])
            
            # 写入数据
            for task in export_data:
                m = task.get('metrics', {})
                writer.writerow([
                    task['id'],
                    task['url'],
                    task['status'],
                    task['created_at'],
                    m.get('parse_time_ms', ''),
                    m.get('download_time_ms', ''),
                    m.get('merge_time_ms', ''),
                    m.get('total_time_ms', ''),
                    m.get('avg_speed_bps', ''),
                    m.get('peak_speed_bps', ''),
                    m.get('retry_count', '')
                ])
            
            csv_content = output.getvalue()
            return api_success({
                'format': 'csv',
                'content': csv_content,
                'count': len(export_data)
            })
        else:
            return api_success({
                'format': 'json',
                'data': export_data,
                'count': len(export_data)
            })
        
    except Exception as e:
        return api_error(500, f'导出失败: {str(e)}')
