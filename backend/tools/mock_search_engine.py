"""
模拟搜索引擎工具 - 用于在没有真实搜索API时提供模拟搜索结果
"""
import asyncio
from typing import List, Dict, Union
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine, SearchEngineType


class MockSearchWrapper:
    """
    模拟搜索引擎包装器，提供预设的搜索结果
    """
    def __init__(self):
        # 预设的搜索结果模板
        self.mock_results = {
            "绩效评价": [
                {
                    'title': '财政绩效评价管理办法',
                    'link': 'http://www.mof.gov.cn/zhengwuxinxi/caizhengwengao/wg2020/wg202012/202012/t20201231_3635394.htm',
                    'snippet': '为规范和加强财政绩效评价管理，提高财政资金使用效益，根据《中华人民共和国预算法》等法律法规，制定本办法。'
                },
                {
                    'title': '河南省财政厅绩效评价工作指南',
                    'link': 'http://czt.henan.gov.cn/2021/10-15/2234567.html',
                    'snippet': '河南省财政厅关于加强预算绩效管理的实施意见，明确了绩效评价的基本原则、评价内容、评价方法等。'
                }
            ],
            "小麦一喷三防": [
                {
                    'title': '小麦"一喷三防"技术指导意见',
                    'link': 'http://www.moa.gov.cn/nybgb/2021/202104/202104/t20210430_6366789.html',
                    'snippet': '小麦"一喷三防"是指在小麦生长后期，通过喷施杀虫剂、杀菌剂、植物生长调节剂或叶面肥等，达到防病虫、防干热风、防倒伏的目的。'
                },
                {
                    'title': '开封市小麦"一喷三防"项目实施方案',
                    'link': 'http://www.kaifeng.gov.cn/zwgk/zfxxgkml/nyncgz/202203/t20220315_1234567.html',
                    'snippet': '为做好小麦"一喷三防"工作，确保小麦稳产增产，制定本实施方案。项目覆盖全市小麦种植区域。'
                }
            ],
            "财政局": [
                {
                    'title': '开封市祥符区财政局职能介绍',
                    'link': 'http://www.xiangfu.gov.cn/bmxx/czj/gkml/202201/t20220115_1234567.html',
                    'snippet': '开封市祥符区财政局是区政府工作部门，负责财政收支、预算管理、绩效评价等工作。'
                }
            ]
        }

    async def run(self, query: str, max_results: int = 5, as_string: bool = False) -> Union[str, List[Dict]]:
        """
        执行模拟搜索并返回预设结果
        """
        logger.info(f"[MockSearch] 执行模拟搜索: {query}")
        
        # 根据查询关键词匹配预设结果
        results = []
        for keyword, mock_data in self.mock_results.items():
            if keyword in query:
                results.extend(mock_data[:max_results])
                break
        
        # 如果没有匹配的关键词，返回通用结果
        if not results:
            results = [
                {
                    'title': f'关于"{query}"的相关信息',
                    'link': 'http://example.com/mock-result',
                    'snippet': f'这是关于"{query}"的模拟搜索结果。由于网络连接问题，当前使用模拟数据。'
                }
            ]
        
        logger.info(f"[MockSearch] 返回 {len(results)} 个模拟结果")
        return results[:max_results]


def mock_search_engine() -> SearchEngine:
    """
    创建模拟搜索引擎实例
    """
    class MockSearch(SearchEngine):
        def __init__(self, **kwargs):
            super().__init__(engine=SearchEngineType.CUSTOM_ENGINE, **kwargs)
            self.engine_class = MockSearchWrapper()
            self.run_func = self.engine_class.run
    
    return MockSearch()