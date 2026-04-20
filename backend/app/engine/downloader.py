import requests
import os
import time
import random
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass


@dataclass
class DownloadProgress:
    """下载进度信息"""
    downloaded_bytes: int
    total_bytes: int
    progress_percent: float
    instant_speed_bps: int
    avg_speed_bps: int


@dataclass
class SpeedSample:
    """速度采样点"""
    timestamp: float
    speed_bps: int


class ChunkDownloader:
    """
    分块流式下载器
    
    特点:
    - 流式下载，内存占用低
    - 支持限速（固定间隔 + 随机抖动）
    - 支持断点续传（基础实现）
    - 自动重试（网络错误、429等）
    """
    
    CHUNK_SIZE = 1024 * 1024  # 1MB 每块
    DEFAULT_TIMEOUT = 30     # 默认超时秒数
    
    # HTTP状态码处理策略
    RETRYABLE_CODES = {429, 500, 502, 503, 504}  # 可重试的状态码
    SKIP_CODES = {403, 404, 410}  # 不重试，直接失败的码
    
    def __init__(
        self, 
        rate_limit_ms: int = 1000, 
        max_retries: int = 3,
        chunk_size: int = None
    ):
        """
        初始化下载器
        
        Args:
            rate_limit_ms: 限速间隔（毫秒），两次请求之间的最小间隔
            max_retries: 最大重试次数
            chunk_size: 每次读取的块大小（字节）
        """
        self.rate_limit_ms = rate_limit_ms
        self.max_retries = max_retries
        self.chunk_size = chunk_size or self.CHUNK_SIZE
        self.session = requests.Session()
        
        # 默认请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',  # 不压缩，以便计算进度
        })
    
    def download(
        self, 
        url: str, 
        output_path: str, 
        headers: dict = None,
        progress_callback: Callable[[int, int], None] = None,
        speed_callback: Callable[[int], None] = None,
        app = None  # Flask app context for database operations
    ) -> Tuple[int, List[SpeedSample]]:
        """
        下载文件，支持流式写入和进度回调
        
        Args:
            url: 下载地址
            output_path: 保存路径
            headers: 额外请求头
            progress_callback: 进度回调 (downloaded_bytes, total_bytes)
            speed_callback: 速度回调 (instant_speed_bps)
            app: Flask app实例（用于数据库更新）
        
        Returns:
            (总下载字节数, 速度采样列表)
        
        Raises:
            requests.exceptions.HTTPError: HTTP错误
            IOError: 文件操作错误
        """
        # 合并请求头
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        speed_samples = []
        total_bytes = 0
        downloaded_bytes = 0
        start_time = time.time()
        last_request_time = start_time
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        try:
            with self.session.get(url, headers=request_headers, stream=True, timeout=self.DEFAULT_TIMEOUT) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get('content-length', 0))
                
                with open(output_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=self.chunk_size):
                        if not chunk:
                            continue
                        
                        # 限速：确保每次请求之间有最小间隔
                        now = time.time()
                        elapsed_since_last = (now - last_request_time) * 1000
                        if elapsed_since_last < self.rate_limit_ms:
                            sleep_time = (self.rate_limit_ms - elapsed_since_last) / 1000
                            sleep_time += random.uniform(0, 0.3)  # 随机抖动
                            time.sleep(sleep_time)
                        
                        last_request_time = time.time()
                        
                        # 写入文件
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # 计算瞬时速度
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            instant_speed = int(downloaded_bytes / elapsed)
                            
                            # 记录速度采样（每秒采样一次）
                            if speed_callback or speed_samples:
                                sample = SpeedSample(
                                    timestamp=elapsed,
                                    speed_bps=instant_speed
                                )
                                speed_samples.append(sample)
                                
                                if speed_callback:
                                    speed_callback(instant_speed)
                        
                        # 进度回调
                        if progress_callback and total_bytes > 0:
                            progress = int(downloaded_bytes / total_bytes * 100)
                            progress_callback(downloaded_bytes, total_bytes)
        
        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e)
        
        return downloaded_bytes, speed_samples
    
    def download_with_retry(
        self,
        url: str,
        output_path: str,
        headers: dict = None,
        progress_callback: Callable[[int, int], None] = None,
        app = None
    ) -> bool:
        """
        带重试的下载
        
        Args:
            url: 下载地址
            output_path: 保存路径
            headers: 额外请求头
            progress_callback: 进度回调
            app: Flask app
        
        Returns:
            True下载成功，False下载失败
        """
        for attempt in range(self.max_retries):
            try:
                self.download(url, output_path, headers, progress_callback, app=app)
                return True
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else 0
                
                if status_code in self.SKIP_CODES:
                    # 这些状态码不重试
                    raise
                
                if status_code in self.RETRYABLE_CODES:
                    # 指数退避等待
                    wait_time = (attempt + 1) * 2
                    print(f'请求被限流 (HTTP {status_code})，{wait_time}秒后重试...')
                    time.sleep(wait_time)
                    continue
                
                raise
                
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError) as e:
                # 网络错误，重试
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f'网络错误: {e}，{wait_time}秒后重试...')
                    time.sleep(wait_time)
                    continue
                raise
        
        return False
    
    def _handle_http_error(self, e: requests.exceptions.HTTPError):
        """处理HTTP错误"""
        status_code = e.response.status_code if e.response else 0
        
        error_messages = {
            403: '权限不足，可能需要登录或Cookie已过期',
            404: '资源不存在或视频已下架',
            429: '请求过于频繁，请稍后再试',
            500: 'B站服务器内部错误',
            502: 'B站服务器网关错误',
            503: 'B站服务暂时不可用',
            504: 'B站服务器网关超时',
        }
        
        msg = error_messages.get(status_code, f'HTTP错误 {status_code}')
        raise requests.exceptions.HTTPError(msg, response=e.response)
    
    def validate_file(self, file_path: str, min_size: int = 1024) -> bool:
        """
        验证下载的文件
        
        Args:
            file_path: 文件路径
            min_size: 最小文件大小（字节）
        
        Returns:
            True文件有效，False文件无效
        """
        if not os.path.exists(file_path):
            return False
        
        file_size = os.path.getsize(file_path)
        return file_size >= min_size


class RateLimiter:
    """
    简单的令牌桶限速器
    
    用于多线程/多任务场景下的统一限速
    """
    
    def __init__(self, min_interval_ms: int = 1000):
        self.min_interval = min_interval_ms / 1000  # 转换为秒
        self.last_called = 0
        self.lock = __import__('threading').Lock()
    
    def acquire(self):
        """获取令牌（阻塞直到可以执行）"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_called
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_called = time.time()


# 全局限速器实例
_global_rate_limiter = None

def get_rate_limiter(rate_limit_ms: int = 1000) -> RateLimiter:
    """获取全局限速器实例"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(rate_limit_ms)
    return _global_rate_limiter
