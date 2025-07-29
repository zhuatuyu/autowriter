import asyncio
import json
from pathlib import Path
import pytest
import pandas as pd

from metagpt.schema import Message
from backend.roles.data_analyst import DataAnalystAgent
from backend.utils.project_repo import ProjectRepo
from backend.actions.data_analyst_action import AnalyzeData, SummarizeAnalysis

# 1. 准备测试环境和数据
@pytest.fixture
def project_repo(tmp_path: Path) -> ProjectRepo:
    repo = ProjectRepo(tmp_path)
    # 创建一个假的上传文件
    uploads_dir = repo.get_path('uploads')
    uploads_dir.mkdir(exist_ok=True)
    sample_data = pd.DataFrame({
        'feature1': [1, 2, 3, 4, 5],
        'feature2': [5, 4, 3, 2, 1],
        'category': ['A', 'B', 'A', 'B', 'A']
    })
    sample_file_path = uploads_dir / "sample_data.csv"
    sample_data.to_csv(sample_file_path, index=False)
    return repo

@pytest.fixture
def agent(project_repo: ProjectRepo) -> DataAnalystAgent:
    # 创建 agent 并注入 project_repo
    agent = DataAnalystAgent(project_repo=project_repo)
    return agent

# 2. 编写测试用例
@pytest.mark.asyncio
async def test_data_analyst_full_run(agent: DataAnalystAgent, project_repo: ProjectRepo):
    """测试DataAnalystAgent能否完成一个完整的数据分析和报告生成流程"""
    
    # 步骤1: 模拟输入消息 (分析数据)
    instruction = "对数据进行描述性统计，并按类别(category)进行分组计数。"
    file_name = "sample_data.csv"
    msg_content = json.dumps({"instruction": instruction, "file_name": file_name})
    msg = Message(content=msg_content, role="user")
    
    # 步骤2: 运行 agent 的完整流程
    # run 方法会处理整个生命周期，直到 is_idle 为 True
    final_message = await agent.run(msg)

    # 断言最终消息是由 SummarizeAnalysis 生成的
    # cause_by 在 Message 中会被序列化为完整的类路径字符串
    expected_cause_by = f"{SummarizeAnalysis.__module__}.{SummarizeAnalysis.__name__}"
    assert final_message.cause_by == expected_cause_by
    
    # 断言最终产出是一个报告文件的路径
    report_path_str = final_message.content
    report_path = Path(report_path_str)
    
    assert report_path.exists()
    assert report_path.name == f"analysis_report_{file_name}.md"
    
    # 检查报告内容
    report_content = report_path.read_text(encoding='utf-8')
    assert '数据分析报告' in report_content
    print(f"Report Content:\n{report_content}")

    print(f"测试成功，报告已生成于: {report_path}")

# 运行测试 (如果直接执行此文件)
if __name__ == "__main__":
    pytest.main(['-s', __file__])