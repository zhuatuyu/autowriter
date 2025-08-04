# SOP流程测试指南

## 📋 概述

本测试套件用于验证整个SOP流程（ProductManager → Architect → ProjectManager → WriterExpert）是否按预期工作。

## 🧪 测试类型

### 1. 快速验证 (推荐) 
**文件**: `tests/quick_sop_test.py`
- ⏱️ 执行时间: 2-5分钟
- 🎯 目标: 快速确认基本功能正常
- ✅ 适用于: 日常开发验证

```bash
python tests/quick_sop_test.py
```

### 2. 完整测试
**文件**: `tests/test_complete_sop_flow.py`  
- ⏱️ 执行时间: 5-10分钟
- 🎯 目标: 全面测试所有组件
- ✅ 适用于: 重大更改后的验证

```bash
python tests/test_complete_sop_flow.py
```

### 3. 实际环境验证
**文件**: `sop_flow_validator.py`
- ⏱️ 执行时间: 3-8分钟  
- 🎯 目标: 在真实环境中验证流程
- ✅ 适用于: 部署前最终确认

```bash
python sop_flow_validator.py
```

## 🚀 快速开始

### 使用便捷脚本
```bash
./run_sop_test.sh
```
然后选择测试类型 (1-3)

### 手动运行
```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 选择运行一个测试
python tests/quick_sop_test.py           # 快速验证
python tests/test_complete_sop_flow.py   # 完整测试  
python sop_flow_validator.py             # 实际环境验证
```

## 📊 测试评估标准

### ✅ 成功标准
- **智能体执行率**: ≥75% (至少3/4个智能体执行)
- **文件生成**: ≥2个有效文件
- **执行时间**: <5分钟
- **无严重错误**: 没有阻塞性错误

### 📄 预期文件输出
```
workspace/project_id/docs/
├── *research_brief.md         # ProductManager输出
├── report_structure.md        # Architect输出1
├── metric_analysis_table.md   # Architect输出2
├── task_plan.md              # ProjectManager输出
└── final_report.md           # WriterExpert输出
```

## 🔍 测试报告解读

### 智能体执行状态
- **✅ ProductManager**: 研究简报生成成功
- **✅ Architect**: 报告结构和指标设计完成
- **✅ ProjectManager**: 任务计划创建成功
- **✅ WriterExpert**: 最终报告生成完成

### 文件输出检查
- **research_brief**: 包含市场研究和案例分析
- **report_structure**: 包含报告章节结构
- **metric_analysis**: 包含关键绩效指标
- **final_report**: 包含完整的分析报告

## 🐛 常见问题排查

### 问题1: 智能体未执行
**症状**: 某个智能体显示❌状态
**可能原因**:
- 数据传递问题
- Action导入错误
- 监听配置错误

**解决方法**:
```bash
# 检查具体错误日志
python sop_flow_validator.py 2>&1 | grep -E "(ERROR|失败|错误)"
```

### 问题2: 文件未生成
**症状**: 预期文件不存在或为空
**可能原因**:
- 文件保存逻辑错误
- 权限问题  
- project_repo配置问题

**解决方法**:
```bash
# 检查工作目录权限
ls -la workspace/
# 查看详细执行日志
python -u sop_flow_validator.py
```

### 问题3: 执行超时
**症状**: 测试运行超过5分钟
**可能原因**:
- 网络请求慢
- LLM响应慢
- 死锁或无限循环

**解决方法**:
```bash
# 使用Ctrl+C中断并检查日志
# 考虑减少研究轮次
```

## 🔧 自定义测试

### 修改测试消息
编辑测试文件中的`test_message`变量：
```python
test_message = "你的自定义测试消息"
```

### 调整成功标准
修改测试文件中的成功判断逻辑：
```python
success_criteria = {
    "至少3个智能体执行": ...,
    "生成至少2个文件": ...,
    # 添加你的标准
}
```

### 添加新的检查项
扩展`validation_results`字典添加新的检查维度。

## 📈 性能基准

### 正常执行时间
- **ProductManager**: 30-60秒
- **Architect**: 10-30秒  
- **ProjectManager**: 5-15秒
- **WriterExpert**: 60-120秒
- **总时间**: 2-4分钟

### 正常文件大小
- **research_brief**: 2-10KB
- **report_structure**: 0.5-2KB
- **metric_analysis**: 0.5-1KB
- **final_report**: 3-15KB

## 📞 支持

如果测试持续失败，请检查：
1. 虚拟环境是否正确激活
2. 所有依赖是否正确安装
3. API密钥是否正确配置
4. 网络连接是否正常

---

**💡 提示**: 建议在每次重要代码更改后运行快速验证，在发布前运行完整测试。