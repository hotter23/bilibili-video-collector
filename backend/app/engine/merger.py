import subprocess
import os
import shutil
from typing import List, Optional


class VideoMerger:
    """
    视频合并器
    
    使用 FFmpeg 将分离的音视频流合并为 MP4 文件
    支持流复制方式，避免重新编码，速度快且保持原始质量
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        """
        初始化合并器
        
        Args:
            ffmpeg_path: ffmpeg命令路径，默认使用系统PATH中的ffmpeg
        """
        self.ffmpeg_path = ffmpeg_path
    
    def merge(
        self, 
        video_path: str, 
        audio_path: str, 
        output_path: str,
        overwrite: bool = True
    ) -> bool:
        """
        合并视频和音频流为 MP4
        
        Args:
            video_path: 视频流文件路径 (.ts 或 .mp4)
            audio_path: 音频流文件路径 (.ts 或 .aac)
            output_path: 输出文件路径 (.mp4)
            overwrite: 是否覆盖已存在的输出文件
        
        Returns:
            True成功，False失败
        
        Raises:
            FileNotFoundError: 输入文件不存在
            RuntimeError: FFmpeg执行失败
        """
        # 验证输入文件
        if not os.path.exists(video_path):
            raise FileNotFoundError(f'视频文件不存在: {video_path}')
        
        if not audio_path or not os.path.exists(audio_path):
            # 如果没有音频文件，只复制视频
            print(f'警告: 音频文件不存在 ({audio_path})，将只保留视频流')
            audio_path = video_path  # ffmpeg会忽略第二个-i
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # 构建FFmpeg命令
        cmd = [
            self.ffmpeg_path,
            '-hide_banner',           # 隐藏版本信息
            '-loglevel', 'error',     # 只显示错误
            '-i', video_path,         # 输入视频
            '-i', audio_path,        # 输入音频
            '-c', 'copy',            # 流复制，不重新编码
            '-shortest',             # 以最短的流为准
        ]
        
        if overwrite:
            cmd.append('-y')
        else:
            cmd.append('-n')
        
        cmd.append(output_path)
        
        try:
            # 执行FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or '未知错误'
                raise RuntimeError(f'FFmpeg合并失败: {error_msg}')
            
            return True
            
        except subprocess.TimeoutExpired:
            raise RuntimeError('FFmpeg执行超时（5分钟）')
        except FileNotFoundError:
            raise RuntimeError('FFmpeg未安装或不在PATH中，请先安装FFmpeg')
    
    def merge_multiple(
        self,
        video_parts: List[str],
        audio_parts: List[str],
        output_path: str
    ) -> bool:
        """
        合并多个分片文件
        
        用于处理分片下载的视频/音频片段
        
        Args:
            video_parts: 视频分片路径列表（按顺序）
            audio_parts: 音频分片路径列表（按顺序）
            output_path: 输出路径
        
        Returns:
            True成功
        """
        # 创建临时文件列表
        video_list = self._create_concat_list(video_parts, 'video')
        audio_list = self._create_concat_list(audio_parts, 'audio')
        
        # 临时输出文件
        video_merged = output_path + '.video.tmp'
        audio_merged = output_path + '.audio.tmp'
        
        try:
            # 分别合并视频和音频分片
            if video_parts:
                self._concat_segments(video_list, video_merged, is_video=True)
            
            if audio_parts:
                self._concat_segments(audio_list, audio_merged, is_video=False)
            
            # 最终合并
            self.merge(
                video_merged if video_parts else video_parts[0],
                audio_merged if audio_parts else audio_parts[0],
                output_path
            )
            
            return True
            
        finally:
            # 清理临时文件
            self._cleanup([video_list, audio_list, video_merged, audio_merged])
    
    def _create_concat_list(self, files: List[str], stream_type: str) -> str:
        """创建FFmpeg concat文件列表"""
        list_path = f'/tmp/{stream_type}_concat_list.txt'
        with open(list_path, 'w', encoding='utf-8') as f:
            for file in files:
                f.write(f"file '{file}'\n")
        return list_path
    
    def _concat_segments(self, list_path: str, output_path: str, is_video: bool):
        """使用FFmpeg合并分片"""
        cmd = [
            self.ffmpeg_path,
            '-hide_banner',
            '-loglevel', 'error',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_path,
            '-c', 'copy',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'分片合并失败: {result.stderr}')
    
    def cleanup_temp_files(self, *file_paths: str):
        """
        清理临时文件
        
        Args:
            *file_paths: 要删除的文件路径
        """
        for path in file_paths:
            self._cleanup_single(path)
    
    def _cleanup(self, paths: List[str]):
        """批量清理文件"""
        for path in paths:
            self._cleanup_single(path)
    
    def _cleanup_single(self, path: str):
        """删除单个文件（如果存在）"""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    
    def validate_output(self, output_path: str, min_size: int = 1024) -> bool:
        """
        验证输出文件
        
        Args:
            output_path: 输出文件路径
            min_size: 最小文件大小（字节）
        
        Returns:
            True文件有效，False无效
        """
        if not os.path.exists(output_path):
            return False
        
        file_size = os.path.getsize(output_path)
        
        # 文件太小肯定有问题
        if file_size < min_size:
            return False
        
        # 尝试读取文件头部验证MP4格式
        try:
            with open(output_path, 'rb') as f:
                header = f.read(12)
                # MP4/ISO media 格式
                if not (header[4:8] in (b'ftyp', b'moov', b'mdat') or
                        header.startswith(b'\x00\x00')):
                    return False
        except Exception:
            return False
        
        return True
    
    def get_duration(self, file_path: str) -> Optional[float]:
        """
        获取视频时长
        
        Args:
            file_path: 视频文件路径
        
        Returns:
            时长（秒），获取失败返回None
        """
        cmd = [
            self.ffmpeg_path,
            '-i', file_path,
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            # 从输出中提取时长
            import re
            match = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', result.stderr)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                ms = int(match.group(4)) * 10
                return hours * 3600 + minutes * 60 + seconds + ms / 1000
            
            return None
        except Exception:
            return None


def check_ffmpeg() -> dict:
    """
    检查FFmpeg是否可用
    
    Returns:
        包含status和version的字典
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # 提取版本号
            import re
            match = re.search(r'ffmpeg version (\S+)', result.stdout)
            version = match.group(1) if match else 'unknown'
            return {'status': 'ok', 'version': version}
        else:
            return {'status': 'error', 'message': 'ffmpeg命令执行失败'}
            
    except FileNotFoundError:
        return {'status': 'error', 'message': 'ffmpeg未安装或不在PATH中'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


if __name__ == '__main__':
    # 检查FFmpeg
    status = check_ffmpeg()
    print(f"FFmpeg状态: {status}")
