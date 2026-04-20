import requests
import re
import json
from typing import Dict, Optional
from urllib.parse import urlparse


class BilibiliParser:
    """
    B站视频媒体解析器
    
    负责从B站视频URL解析出真实的媒体资源地址
    """
    
    # B站 API 地址
    PLAYER_API = 'https://api.bilibili.com/x/player/playurl'
    VIDEO_INFO_API = 'https://api.bilibili.com/x/web-interface/view'
    
    def __init__(self, cookies: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            cookies: 可选的Cookie字符串，用于获取更高清晰度的视频
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        if cookies:
            self.session.headers['Cookie'] = cookies
    
    def parse(self, url: str, quality: int = 80) -> Dict:
        """
        解析B站视频URL，返回媒体资源信息
        
        Args:
            url: B站视频链接，如 https://www.bilibili.com/video/BV1xx411c7mD
            quality: 视频质量码，80=1080P, 64=720P, 32=480P, 16=360P
        
        Returns:
            包含以下键的字典:
            - bvid: B站视频号
            - cid: 视频CID
            - title: 视频标题
            - author: 作者
            - duration: 时长(秒)
            - cover_url: 封面URL
            - video_url: 视频流地址
            - audio_url: 音频流地址
            - filesize: 预估文件大小(字节)
        
        Raises:
            ValueError: URL格式无效或解析失败
        """
        # 1. 提取 BV 号
        bvid = self._extract_bvid(url)
        if not bvid:
            raise ValueError(f'无法从URL提取BV号: {url}')
        
        # 2. 获取视频基本信息 (CID等)
        video_info = self._get_video_info(bvid)
        cid = video_info['cid']
        
        # 3. 调用播放API获取媒体地址
        media_info = self._get_media_url(bvid, cid, quality)
        
        # 4. 整合结果
        return {
            'bvid': bvid,
            'cid': cid,
            'title': video_info.get('title', '未知标题'),
            'author': video_info.get('author', '未知作者'),
            'duration': video_info.get('duration', 0),
            'cover_url': video_info.get('cover_url', ''),
            'video_url': media_info['video_url'],
            'audio_url': media_info['audio_url'],
            'filesize': media_info.get('filesize', 0)
        }
    
    def _extract_bvid(self, url: str) -> Optional[str]:
        """从URL提取BV号"""
        # 支持的格式:
        # https://www.bilibili.com/video/BV1xx411c7mD
        # https://bilibili.com/video/BV1xx411c7mD
        # BV1xx411c7mD
        patterns = [
            r'BV([A-Za-z0-9]+)',
            r'bilibili\.com/video/(BV[\w]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                bvid = match.group(1) if match.lastindex else match.group()
                return bvid if bvid.startswith('BV') else f'BV{match.group(1)}'
        
        return None
    
    def _get_video_info(self, bvid: str) -> Dict:
        """获取视频基本信息"""
        try:
            url = f'{self.VIDEO_INFO_API}?bvid={bvid}'
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data['code'] != 0:
                raise ValueError(f"B站API错误: {data.get('message', '未知错误')}")
            
            result = data['data']
            # 获取下载视频所需CID
            cid = result.get('cid') or result['pages'][0]['cid']
            
            # 处理标题
            title = result.get('title', '')
            if not title and result.get('pages'):
                title = result['pages'][0].get('part', title)
            
            return {
                'cid': cid,
                'title': title,
                'author': result.get('owner', {}).get('name', ''),
                'duration': result.get('duration', 0),
                'cover_url': result.get('pic', '')
            }
        except requests.exceptions.RequestException as e:
            raise ValueError(f'获取视频信息失败: {str(e)}')
    
    def _get_media_url(self, bvid: str, cid: int, quality: int = 80) -> Dict:
        """
        调用B站播放API获取真实媒体地址
        
        Args:
            bvid: 视频BV号
            cid: 视频CID
            quality: 质量码
        
        Returns:
            包含video_url, audio_url, filesize的字典
        """
        try:
            params = {
                'bvid': bvid,
                'cid': cid,
                'qn': quality,
                'type': '',
                'valioc': '1',
                'platform': 'html5',
                'high_quality': '1'
            }
            
            resp = self.session.get(self.PLAYER_API, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data['code'] != 0:
                raise ValueError(f"播放地址API错误: {data.get('message', '未知错误')}")
            
            result = data['data']
            
            # 优先使用 DASH 格式 (通常包含分离的音视频)
            if 'dash' in result:
                dash = result['dash']
                video_url = ''
                audio_url = ''
                filesize = 0
                
                # 获取视频流
                if dash.get('video'):
                    video_url = dash['video'][0]['baseUrl']
                    filesize = dash['video'][0].get('size', 0)
                
                # 获取音频流
                if dash.get('audio'):
                    audio_url = dash['audio'][0]['baseUrl']
                
                if not video_url:
                    raise ValueError('无法获取视频流地址')
                
                return {
                    'video_url': video_url,
                    'audio_url': audio_url,
                    'filesize': filesize
                }
            
            # 降级到 flv 格式
            elif 'durl' in result:
                durl = result['durl'][0]
                return {
                    'video_url': durl['url'],
                    'audio_url': '',  # FLV格式通常音视频混合
                    'filesize': durl.get('size', 0)
                }
            
            else:
                raise ValueError('无法解析媒体格式')
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f'获取播放地址失败: {str(e)}')
    
    def get_available_qualities(self, bvid: str, cid: int) -> list:
        """获取可用的清晰度列表"""
        try:
            params = {
                'bvid': bvid,
                'cid': cid,
                'qn': 0,  # 获取所有可用质量
                'type': '',
                'valioc': '1',
                'platform': 'html5'
            }
            
            resp = self.session.get(self.PLAYER_API, params=params, timeout=10)
            data = resp.json()
            
            if data['code'] != 0:
                return []
            
            result = data['data']
            qualities = []
            
            if 'accept_quality' in result:
                quality_map = {
                    120: '4K', 112: '1080P60', 80: '1080P',
                    64: '720P', 32: '480P', 16: '360P'
                }
                for q in result['accept_quality']:
                    qualities.append({
                        'qn': q,
                        'desc': quality_map.get(q, f'{q}p')
                    })
            
            return qualities
        except Exception:
            return []


def test_parser():
    """测试解析器"""
    parser = BilibiliParser()
    
    # 测试URL
    test_url = 'https://www.bilibili.com/video/BV1xx411c7mD'
    
    try:
        result = parser.parse(test_url)
        print('解析成功!')
        print(f'标题: {result["title"]}')
        print(f'作者: {result["author"]}')
        print(f'视频流: {result["video_url"][:100]}...')
        print(f'音频流: {result["audio_url"][:100] if result["audio_url"] else "无"}...')
    except Exception as e:
        print(f'解析失败: {e}')


if __name__ == '__main__':
    test_parser()
