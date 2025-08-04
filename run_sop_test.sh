#!/bin/bash

echo "🧪 SOP流程测试启动器"
echo "======================"

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  请先激活虚拟环境:"
    echo "   source venv/bin/activate"
    exit 1
fi

# 检查当前目录
if [[ ! -f "app.py" ]]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

echo "📋 选择测试类型:"
echo "1. 简化测试 (推荐) - 使用现有Company服务"
echo "2. 快速验证"
echo "3. 完整测试"
echo "4. 实际环境验证"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo "🚀 运行简化测试..."
        python simple_sop_test.py
        ;;
    2)
        echo "🚀 运行快速验证..."
        python tests/quick_sop_test.py
        ;;
    3)
        echo "🚀 运行完整测试..."
        python tests/test_complete_sop_flow.py
        ;;
    4)
        echo "🚀 运行实际环境验证..."
        python sop_flow_validator.py
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成"