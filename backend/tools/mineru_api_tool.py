"""
Mineru API Tool
封装对Mineru.net文档解析API的调用
"""
import aiohttp
import asyncio
import yaml
from pathlib import Path
# from metagpt.config2 import config # 暂时移除对config的依赖

class MineruApiTool:
    def __init__(self):
        # 临时硬编码API密钥和URL以解决启动时配置加载问题
        self.api_key = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI2MjQwNzA4MSIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc1MzA4MTQwMSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTM2MTM4NjU2MjQiLCJvcGVuSWQiOm51bGwsInV1aWQiOiJlYWUxMzhlMy00MmQ5LTRjNzEtOTI1ZC00ZGE1NWU1NTNiM2EiLCJlbWFpbCI6IiIsImV4cCI6MTc1NDI5MTAwMX0.QhQ9BFLjSsWobi4mkr4p5QPM6-lgHPAJpmeY6r0tGvbatMCV64fAnGlAbr6dlMKwytijvNhQxfMO94IU0ifLiQ"
        self.base_url = "https://mineru.net/api/v1/file/parse"

    async def process_url(self, url: str, is_ocr: bool = True, enable_formula: bool = False) -> str:
        """
        调用Mineru API处理URL文档，并返回Markdown内容。
        :param url: 要处理的文档URL
        :param is_ocr: 是否启用OCR
        :param enable_formula: 是否启用公式识别
        :return: 解析后的Markdown文本
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            'url': url,
            'is_ocr': is_ocr,
            'enable_formula': enable_formula,
        }

        async with aiohttp.ClientSession() as session:
            try:
                print(f"🚀 正在发送URL '{url}' 到 Mineru API进行处理...")
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    
                    result = await response.json()
                    
                    # 根据API文档，任务ID在 result['data']
                    task_id = result.get('data')
                    
                    if not task_id:
                        raise ValueError("Mineru API响应中未找到任务ID")
                    
                    print(f"✅ 任务创建成功，任务ID: {task_id}")
                    
                    # 轮询任务状态直到完成
                    return await self._poll_task_result(task_id)

            except aiohttp.ClientError as e:
                print(f"❌ 调用Mineru API时发生网络错误: {e}")
                raise
            except Exception as e:
                print(f"❌ 处理Mineru API响应时发生错误: {e}")
                raise

    async def _poll_task_result(self, task_id: str, max_attempts: int = 60, interval: int = 5) -> str:
        """
        轮询任务结果
        :param task_id: 任务ID
        :param max_attempts: 最大尝试次数
        :param interval: 轮询间隔（秒）
        :return: 解析后的Markdown文本
        """
        status_url = f"https://mineru.net/api/v4/extract/task/{task_id}"
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(max_attempts):
                try:
                    async with session.get(status_url, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        status = result.get('data', {}).get('status')
                        
                        if status == 'completed':
                            markdown_content = result.get('data', {}).get('markdown', '')
                            if markdown_content:
                                print(f"✅ 任务完成，获取到Markdown内容")
                                return markdown_content
                            else:
                                raise ValueError("任务完成但未找到Markdown内容")
                        
                        elif status == 'failed':
                            error_msg = result.get('data', {}).get('error', '未知错误')
                            raise ValueError(f"任务处理失败: {error_msg}")
                        
                        elif status in ['pending', 'processing']:
                            print(f"⏳ 任务处理中... (尝试 {attempt + 1}/{max_attempts})")
                            await asyncio.sleep(interval)
                        
                        else:
                            print(f"⚠️ 未知任务状态: {status}")
                            await asyncio.sleep(interval)

                except aiohttp.ClientError as e:
                    print(f"❌ 轮询任务状态时发生网络错误: {e}")
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(interval)

            raise TimeoutError(f"任务处理超时，已尝试 {max_attempts} 次")

    async def process_file(self, file_path: str) -> dict:
        """
        处理本地文件
        :param file_path: 本地文件路径
        :return: 包含处理结果的字典
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}'
                }
            
            # 检查文件大小（限制为50MB）
            file_size = file_path.stat().st_size
            if file_size > 50 * 1024 * 1024:
                return {
                    'success': False,
                    'error': f'文件过大: {file_size / 1024 / 1024:.1f}MB，超过50MB限制'
                }
            
            # 检查文件类型
            supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.md'}
            if file_path.suffix.lower() not in supported_extensions:
                return {
                    'success': False,
                    'error': f'不支持的文件类型: {file_path.suffix}'
                }
            
            # 使用multipart/form-data上传文件
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=file_path.name)
                    data.add_field('is_ocr', 'true')
                    data.add_field('enable_formula', 'false')
                    
                    print(f"🚀 正在上传文件 '{file_path.name}' 到 MinerU API...")
                    
                    async with session.post(self.base_url, headers=headers, data=data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            return {
                                'success': False,
                                'error': f'API调用失败 (状态码: {response.status}): {error_text}'
                            }
                        
                        result = await response.json()
                        
                        # 检查API响应
                        if not result.get('success', False):
                            return {
                                'success': False,
                                'error': f"API返回错误: {result.get('message', '未知错误')}"
                            }
                        
                        task_id = result.get('data')
                        if not task_id:
                            return {
                                'success': False,
                                'error': 'API响应中未找到任务ID'
                            }
                        
                        print(f"✅ 文件上传成功，任务ID: {task_id}")
                        
                        # 轮询任务结果
                        markdown_content = await self._poll_task_result(task_id)
                        
                        return {
                            'success': True,
                            'markdown_content': markdown_content,
                            'task_id': task_id,
                            'file_name': file_path.name
                        }
                        
        except Exception as e:
            print(f"❌ 处理文件时发生错误: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 创建一个全局工具实例，方便调用
mineru_tool = MineruApiTool() 