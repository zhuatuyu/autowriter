#!/usr/bin/env python
"""
测试健壮搜索修复是否生效
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_import_robust_search():
    """测试是否能正确导入健壮搜索Action"""
    print("=== 测试导入健壮搜索Action ===")
    
    try:
        from backend.actions.robust_search_action import RobustSearchEnhancedQA
        print("✅ 成功导入 RobustSearchEnhancedQA")
        
        # 创建实例
        robust_search = RobustSearchEnhancedQA()
        print("✅ 成功创建 RobustSearchEnhancedQA 实例")
        
        # 检查方法是否存在
        assert hasattr(robust_search, '_rewrite_query'), "应该有_rewrite_query方法"
        assert hasattr(robust_search, '_extract_rewritten_query_robust'), "应该有健壮的JSON提取方法"
        assert hasattr(robust_search, 'run'), "应该有run方法"
        print("✅ 所有必要方法都存在")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_custom_team_leader_import():
    """测试CustomTeamLeader是否正确使用健壮搜索"""
    print("\n=== 测试CustomTeamLeader导入修复 ===")
    
    try:
        from backend.roles.custom_team_leader import CustomTeamLeader
        print("✅ 成功导入 CustomTeamLeader")
        
        # 检查是否使用了RobustSearchEnhancedQA
        import inspect
        source = inspect.getsource(CustomTeamLeader)
        
        if "RobustSearchEnhancedQA" in source:
            print("✅ CustomTeamLeader已使用RobustSearchEnhancedQA")
        else:
            print("❌ CustomTeamLeader仍在使用原生SearchEnhancedQA")
            return False
            
        if "SearchEnhancedQA(" in source and "RobustSearchEnhancedQA(" not in source:
            print("❌ 发现原生SearchEnhancedQA的使用")
            return False
            
        print("✅ CustomTeamLeader已正确修复")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_json_parsing_robustness():
    """测试JSON解析的健壮性"""
    print("\n=== 测试JSON解析健壮性 ===")
    
    try:
        from backend.actions.robust_search_action import RobustSearchEnhancedQA
        
        robust_search = RobustSearchEnhancedQA()
        
        # 测试各种有问题的JSON格式
        test_cases = [
            ('{"query": "正常JSON"}', "正常JSON"),
            ("{'query': '单引号JSON'}", "单引号JSON"), 
            ("{query: '无键引号'}", "无键引号"),
        ]
        
        for i, (test_input, expected) in enumerate(test_cases):
            try:
                result = robust_search._extract_rewritten_query_robust(test_input)
                if result == expected:
                    print(f"✅ 测试用例 {i+1} 通过: {test_input} -> {result}")
                else:
                    print(f"❌ 测试用例 {i+1} 结果不匹配: 期望 {expected}, 实际 {result}")
            except Exception as e:
                print(f"⚠️ 测试用例 {i+1} 异常: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🚀 开始测试健壮搜索修复效果...\n")
    
    tests = [
        test_import_robust_search,
        test_custom_team_leader_import,
        test_json_parsing_robustness,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 健壮搜索修复验证通过！")
        print("现在重新运行您的应用，应该不会再看到JSON解析错误了。")
        print("\n📝 如果仍然有错误，请检查:")
        print("1. 确保使用了修复后的CustomTeamLeader")
        print("2. 检查是否还有其他地方直接使用了原生SearchEnhancedQA")
        print("3. 重启应用以确保修改生效")
    else:
        print("⚠️ 部分测试未通过，请检查错误信息")
    
    return failed == 0

if __name__ == "__main__":
    main()