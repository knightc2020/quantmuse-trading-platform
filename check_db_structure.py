#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Supabase database table structure
"""

from supabase import create_client
import pandas as pd

def check_database_structure():
    """检查数据库表结构"""
    
    # Supabase配置
    url = "https://rnnflvgioxbrfdznodel.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJubmZsdmdpb3hicmZkem5vZGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDU4MjUsImV4cCI6MjA2ODU4MTgyNX0.95D04EwbpWODnFPCYQv-19su52uNjmAYP5jmGQLM7nE"
    
    try:
        client = create_client(url, key)
        print("Success: Supabase connected")
        
        # 获取所有表
        print("\n🔍 查找数据库中的表...")
        
        # 尝试不同可能的表名
        possible_tables = [
            'dragon_tiger', 'longhubang', 'lhb', 'dragon_list', 
            'top_list', 'trading_list', 'hot_money', 'seat_data'
        ]
        
        found_tables = []
        
        for table_name in possible_tables:
            try:
                result = client.table(table_name).select('*').limit(1).execute()
                if result.data:
                    found_tables.append(table_name)
                    print(f"✅ 找到表: {table_name}")
            except Exception as e:
                print(f"❌ 表 {table_name} 不存在: {str(e)[:50]}...")
        
        if not found_tables:
            print("❌ 未找到任何龙虎榜相关的表")
            
            # 尝试获取数据库schema信息
            try:
                # 查询information_schema（如果有权限）
                result = client.rpc('get_schema_info').execute()
                print("数据库schema信息:", result.data)
            except:
                print("无法获取schema信息，可能需要更高权限")
            
            return None
        
        # 分析每个找到的表
        for table_name in found_tables:
            print(f"\n📊 分析表: {table_name}")
            print("=" * 50)
            
            try:
                # 获取样本数据
                result = client.table(table_name).select('*').limit(5).execute()
                
                if result.data:
                    df = pd.DataFrame(result.data)
                    print(f"📋 表结构 ({len(result.data)} 条样本数据):")
                    print(f"字段数量: {len(df.columns)}")
                    print(f"字段列表: {list(df.columns)}")
                    
                    # 显示数据类型
                    print(f"\n🔧 字段类型:")
                    for col in df.columns:
                        dtype = str(df[col].dtype)
                        sample_value = df[col].iloc[0] if not df[col].empty else "NULL"
                        print(f"  {col}: {dtype} (示例: {sample_value})")
                    
                    # 显示前几行数据
                    print(f"\n📄 前3行数据:")
                    print(df.head(3).to_string())
                    
                    # 获取总记录数
                    try:
                        count_result = client.table(table_name).select('*', count='exact').execute()
                        total_count = len(count_result.data) if count_result.data else "未知"
                        print(f"\n📈 总记录数: {total_count}")
                    except:
                        print(f"\n📈 总记录数: 无法获取")
                        
                else:
                    print(f"⚠️ 表 {table_name} 存在但无数据")
                    
            except Exception as e:
                print(f"❌ 无法分析表 {table_name}: {e}")
        
        return found_tables
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

if __name__ == "__main__":
    print("🔍 开始检查Supabase数据库结构...")
    tables = check_database_structure()
    
    if tables:
        print(f"\n✅ 检查完成，找到 {len(tables)} 个相关表: {', '.join(tables)}")
    else:
        print("\n❌ 未找到龙虎榜相关数据表")