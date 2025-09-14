#!/usr/bin/env python3
"""
简单的数据库连接测试脚本
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_service'))

from supabase_client import get_supabase_client

def test_connection():
    print("正在测试Supabase数据库连接...")
    
    # 检查环境变量
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {url}")
    print(f"SUPABASE_KEY: {'*' * 20 if key else 'None'}")
    
    # 获取客户端
    client = get_supabase_client()
    
    if client.is_connected():
        print("✅ 客户端初始化成功")
        
        # 测试连接
        if client.test_connection():
            print("✅ 数据库连接测试成功！")
            
            # 尝试获取一些数据
            try:
                summary = client.get_dragon_tiger_summary(days=7, table_type='seat')
                if summary:
                    print(f"✅ 数据查询成功，获取到概览数据: {summary}")
                else:
                    print("⚠️ 数据查询返回空结果")
            except Exception as e:
                print(f"❌ 数据查询失败: {e}")
        else:
            print("❌ 数据库连接测试失败")
    else:
        print("❌ 客户端初始化失败")

if __name__ == "__main__":
    test_connection()