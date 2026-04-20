import threading
import queue
import time
import os
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional, Callable
from datetime import datetime

from .parser import BilibiliParser
from .downloader import ChunkDownloader, get_rate_limiter
from .merger import VideoMerger
from app import get_config


class TaskScheduler:
    """
    任务调度器
    
    管理采集任务的执行，支持:
    - 任务队列管理
    - 并发控制
    - 任务状态机转换
    - 指标记录
    """
    
    def __init__(self, max_concurrent: int = 3):
        """
        初始化调度器
        
        Args:
            max_concurrent: 最大并发任务数
        """
        self.max_concurrent = max_concurrent
        self.task_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.running_tasks: Dict[str, Future] = {}
        self.lock = threading.Lock()
        self._stopped = False
        
        # 存储app实例，用于数据库操作
        self._app = None
    
    def start(self, app):
        """
        启动调度器
        
        Args:
            app: Flask应用实例
        """
        self._app = app
        
        if self._stopped:
            self._stopped = False
            self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        
        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._run_scheduler_loop,
            daemon=True,
            name='TaskScheduler'
        )
        self._scheduler_thread.start()
        print(f'任务调度器已启动，最大并发: {self.max_concurrent}')
    
    def stop(self):
        """停止调度器"""
        self._stopped = True
        self.executor.shutdown(wait=False)
        print('任务调度器已停止')
    
    def submit(self, task_id: str, config: Dict):
        """
        提交任务到调度队列

        Args:
            task_id: 任务ID
            config: 任务配置，包含url, cookies, quality等
        """
        print(f'[DEBUG] submit called: task_id={task_id}, queue_size before={self.task_queue.qsize()}')
        self.task_queue.put((task_id, config))
        print(f'[DEBUG] task {task_id} added to queue, queue_size after={self.task_queue.qsize()}')

    def _run_scheduler_loop(self):
        """调度主循环"""
        print('[DEBUG] Scheduler loop started')
        loop_count = 0
        while not self._stopped:
            loop_count += 1
            if loop_count <= 5 or loop_count % 100 == 0:
                print(f'[DEBUG] Scheduler loop alive, iteration={loop_count}, queue_size={self.task_queue.qsize()}, running={len(self.running_tasks)}')
            try:
                # 检查是否有空闲槽位
                with self.lock:
                    active_count = len(self.running_tasks)
                
                if active_count >= self.max_concurrent:
                    time.sleep(0.5)
                    continue
                
                # 从队列获取任务（非阻塞）
                try:
                    task_id, config = self.task_queue.get(block=False)
                except queue.Empty:
                    time.sleep(0.1)
                    continue
                
                # 提交到线程池执行
                with self.lock:
                    future = self.executor.submit(self._execute_task, task_id, config)
                    self.running_tasks[task_id] = future
                print(f'[DEBUG] Task {task_id} submitted to executor, running_tasks count={len(self.running_tasks)}')
                
                # 启动任务监控
                threading.Thread(
                    target=self._monitor_task,
                    args=(task_id,),
                    daemon=True
                ).start()
                
            except Exception as e:
                print(f'调度循环异常: {e}')
                time.sleep(1)
    
    def _execute_task(self, task_id: str, config: Dict):
        """
        执行单个采集任务

        Args:
            task_id: 任务ID
            config: 任务配置
        """
        print(f'[DEBUG] _execute_task started for {task_id}')
        try:
            from app.models import db, Task, TaskStatus, VideoMetadata, Metrics, ErrorLog
            from app.models.error_log import ErrorStage, ErrorType
            from app.utils.security import classify_error, sanitize_cookie

            app = self._app
            print(f'[DEBUG] _execute_task got app for {task_id}')

            # 初始化组件
            parser = BilibiliParser(cookies=config.get('cookies'))
            downloader = ChunkDownloader(
                rate_limit_ms=config.get('rate_limit_ms', 1000),
                max_retries=config.get('max_retries', 3)
            )

            from app import get_config
            from app.config import BASE_DIR
            cfg = get_config()
            ffmpeg_path = os.path.join(BASE_DIR, 'bin', 'ffmpeg.exe')
            temp_dir = cfg.DOWNLOAD_TEMP_DIR
            output_dir = cfg.DOWNLOAD_OUTPUT_DIR

            merger = VideoMerger(ffmpeg_path=ffmpeg_path)

            rate_limiter = get_rate_limiter()

            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            video_temp = os.path.join(temp_dir, f'{task_id}_video.ts')
            audio_temp = os.path.join(temp_dir, f'{task_id}_audio.ts')
            output_path = os.path.join(output_dir, f'{task_id}.mp4')

            # 指标数据
            parse_time_ms = 0
            download_time_ms = 0
            merge_time_ms = 0
            download_bytes = 0
            speeds = []
            retry_count = 0

            print(f'[DEBUG] _execute_task initialized components for {task_id}')

            # 日志脱敏
            cookie_info = sanitize_cookie(config.get('cookies'))
            print(f'[DEBUG] Starting task {task_id}, Cookie: {cookie_info}')

            try:
                with app.app_context():
                    # 更新状态：解析中
                    task = Task.query.get(task_id)
                    if not task:
                        print(f'任务 {task_id} 不存在')
                        return

                    task.status = TaskStatus.parsing
                    task.started_at = datetime.now()
                    db.session.commit()

                # ===== 阶段1：解析 =====
                parse_start = time.time()
                try:
                    media_info = parser.parse(config['url'], quality=_quality_to_qn(config.get('quality', '1080P')))
                    parse_time_ms = int((time.time() - parse_start) * 1000)

                    with app.app_context():
                        task = Task.query.get(task_id)
                        # 保存元数据
                        metadata = VideoMetadata(
                            task_id=task_id,
                            bvid=media_info.get('bvid'),
                            title=media_info.get('title'),
                            author=media_info.get('author'),
                            duration=media_info.get('duration'),
                            quality=config.get('quality', '1080P'),
                            cover_url=media_info.get('cover_url', ''),
                            output_path=output_path
                        )
                        db.session.add(metadata)
                        db.session.commit()

                except Exception as e:
                    parse_time_ms = int((time.time() - parse_start) * 1000)
                    _save_error(app, task_id, ErrorStage.parse, None, ErrorType.parse_failed, str(e))
                    _update_task_failed(app, task_id, f'解析失败: {str(e)}')
                    return

                # ===== 阶段2：下载 =====
                download_start = time.time()

                # 更新状态：下载中
                _update_task_status(app, task_id, TaskStatus.downloading)

                try:
                    # 下载视频
                    def progress_callback(downloaded, total):
                        if total > 0:
                            progress = int(downloaded / total * 50)  # 下载占50%进度
                            _update_task_progress(app, task_id, progress)

                    def speed_callback(speed):
                        speeds.append(speed)

                    # 下载视频流
                    rate_limiter.acquire()
                    _, video_speeds = downloader.download(
                        media_info['video_url'],
                        video_temp,
                        parser.session.headers,
                        progress_callback,
                        speed_callback
                    )

                    # 下载音频流
                    if media_info.get('audio_url'):
                        rate_limiter.acquire()
                        _, audio_speeds = downloader.download(
                            media_info['audio_url'],
                            audio_temp,
                            parser.session.headers,
                            progress_callback,
                            speed_callback
                        )
                        speeds.extend(audio_speeds)

                    download_bytes = media_info.get('filesize', 0)
                    download_time_ms = int((time.time() - download_start) * 1000)

                except Exception as e:
                    download_time_ms = int((time.time() - download_start) * 1000)
                    status_code = _extract_status_code(e)
                    error_type = classify_error(status_code, str(e))
                    _save_error(app, task_id, ErrorStage.download, status_code, error_type, str(e))
                    _update_task_failed(app, task_id, f'下载失败: {str(e)}')
                    return

                # ===== 阶段3：合并 =====
                merge_start = time.time()
                _update_task_status(app, task_id, TaskStatus.merging)
                _update_task_progress(app, task_id, 80)  # 合并阶段开始

                try:
                    merger.merge(video_temp, audio_temp, output_path)
                    merge_time_ms = int((time.time() - merge_start) * 1000)

                    # 验证输出文件
                    if not merger.validate_output(output_path):
                        raise RuntimeError('合并后文件验证失败')

                    # 更新元数据中的文件大小
                    with app.app_context():
                        metadata = VideoMetadata.query.filter_by(task_id=task_id).first()
                        if metadata:
                            metadata.file_size = os.path.getsize(output_path)
                            db.session.commit()

                except Exception as e:
                    merge_time_ms = int((time.time() - merge_start) * 1000)
                    _save_error(app, task_id, ErrorStage.merge, None, ErrorType.merge_failed, str(e))
                    _update_task_failed(app, task_id, f'合并失败: {str(e)}')
                    return

                # ===== 阶段4：完成 =====
                total_time_ms = parse_time_ms + download_time_ms + merge_time_ms
                avg_speed = int(sum(speeds) / len(speeds)) if speeds else 0
                peak_speed = max(speeds) if speeds else 0

                with app.app_context():
                    task = Task.query.get(task_id)
                    task.status = TaskStatus.completed
                    task.progress = 100
                    task.finished_at = datetime.now()
                    db.session.commit()

                    # 保存指标
                    metrics = Metrics(
                        task_id=task_id,
                        parse_time_ms=parse_time_ms,
                        download_time_ms=download_time_ms,
                        merge_time_ms=merge_time_ms,
                        total_time_ms=total_time_ms,
                        download_bytes=download_bytes,
                        avg_speed_bps=avg_speed,
                        peak_speed_bps=peak_speed,
                        retry_count=retry_count
                    )
                    db.session.add(metrics)
                    db.session.commit()

                print(f'任务 {task_id} 已完成，总耗时: {total_time_ms}ms')

            except Exception as e:
                _save_error(app, task_id, None, None, ErrorType.unknown, str(e))
                _update_task_failed(app, task_id, f'任务执行异常: {str(e)}')

            finally:
                # 清理临时文件
                merger.cleanup_temp_files(video_temp, audio_temp)

        except Exception as e:
            print(f'[DEBUG] _execute_task outer exception: {e}')
            _save_error(app, task_id, None, None, ErrorType.unknown, str(e))
            _update_task_failed(app, task_id, f'任务执行异常: {str(e)}')
    
    def _monitor_task(self, task_id: str):
        """监控任务完成"""
        try:
            future = self.running_tasks.get(task_id)
            if future:
                future.result()  # 等待任务完成
        except Exception as e:
            print(f'任务 {task_id} 执行异常: {e}')
        finally:
            with self.lock:
                self.running_tasks.pop(task_id, None)
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.task_queue.qsize()
    
    def get_running_count(self) -> int:
        """获取正在运行的任务数"""
        with self.lock:
            return len(self.running_tasks)


# ===== 辅助函数 =====

def _quality_to_qn(quality: str) -> int:
    """将清晰度名称转换为B站API的qn参数"""
    quality_map = {
        '4K': 120,
        '1080P60': 112,
        '1080P': 80,
        '720P': 64,
        '480P': 32,
        '360P': 16,
    }
    return quality_map.get(quality, 80)


def _update_task_status(app, task_id: str, status: 'TaskStatus'):
    """更新任务状态"""
    from app.models import db, Task, TaskStatus
    with app.app_context():
        task = Task.query.get(task_id)
        if task:
            task.status = status
            db.session.commit()


def _update_task_progress(app, task_id: str, progress: int):
    """更新任务进度"""
    from app.models import db, Task
    with app.app_context():
        task = Task.query.get(task_id)
        if task:
            task.progress = min(progress, 100)
            db.session.commit()


def _update_task_failed(app, task_id: str, error_msg: str):
    """标记任务失败"""
    from app.models import db, Task, TaskStatus
    with app.app_context():
        task = Task.query.get(task_id)
        if task:
            task.status = TaskStatus.failed
            task.finished_at = datetime.now()
            db.session.commit()


def _save_error(app, task_id: str, stage, status_code, error_type, error_msg: str):
    """保存错误日志"""
    from app.models import db, ErrorLog
    with app.app_context():
        error_log = ErrorLog(
            task_id=task_id,
            stage=stage,
            status_code=str(status_code) if status_code else None,
            error_type=error_type,
            error_msg=error_msg[:500]  # 限制长度
        )
        db.session.add(error_log)
        db.session.commit()


def _extract_status_code(exception: Exception) -> Optional[int]:
    """从异常中提取状态码"""
    import requests
    if isinstance(exception, requests.exceptions.HTTPError) and exception.response:
        return exception.response.status_code
    return None


# 全局调度器实例
task_scheduler = TaskScheduler(max_concurrent=3)
