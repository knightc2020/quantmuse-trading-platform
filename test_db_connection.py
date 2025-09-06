#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Supabase数据库连接和表结构
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_service'))

from supabase_client import SupabaseDataClient
import pandas as pd

def test_connection():
    """测试数据库连接"""
    print("=== 测试Supabase数据库连接 ===\n")
    
    # 初始化客户端
    client = SupabaseDataClient()
    
    # 检查连接状态
    if not client.is_connected():
        print("[ERROR] 客户端初始化失败")
        return False
    
    print("[SUCCESS] 客户端初始化成功")
    
    # 测试基本连接
    if not client.test_connection():
        print("[ERROR] 数据库连接测试失败")
        return False
    
    print("[SUCCESS] 数据库连接测试通过")
    
    # 检查表结构
    tables_to_check = ['seat_daily', 'inst_flow', 'trade_flow']
    
    for table_name in tables_to_check:
        try:
            print(f"\n--- 检查表: {table_name} ---")
            result = client.client.table(table_name).select('*').limit(5).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                print(f"[SUCCESS] 表 {table_name} 存在，包含 {len(result.data)} 条记录")
                print(f"字段: {list(df.columns)}")
                print(f"最新几条记录的日期范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")
            else:
                print(f"[WARNING] 表 {table_name} 存在但为空")
        except Exception as e:
            print(f"[ERROR] 表 {table_name} 检查失败: {str(e)}")
    
    # 测试数据查询功能
    print(f"\n--- 测试数据查询功能 ---")
    try:
        summary = client.get_dragon_tiger_summary(days=7, table_type='seat')
        if summary:
            print("[SUCCESS] 数据概览查询成功:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
        else:
            print("[WARNING] 数据概览查询返回空结果")
    except Exception as e:
        print(f"[ERROR] 数据概览查询失败: {str(e)}")
    
    return True

if __name__ == "__main__":
    test_connection()