#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据检查脚本
检查Supabase中的龙虎榜数据情况
"""

import pandas as pd
from datetime import datetime, timedelta
import os
from supabase import create_client

def get_supabase_client():
    """获取Supabase客户端"""
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("请设置环境变量")
    
    return create_client(url, key)

def check_tables():
    """检查各个表的数据情况"""
    supabase = get_supabase_client()
    
    tables = ['seat_daily', 'trade_flow', 'inst_flow', 'block_trade', 'broker_pick', 'money_flow']
    
    print("数据表检查结果:")
    print("-" * 60)
    
    for table in tables:
        try:
            # 获取总记录数
            response = supabase.table(table).select("*", count='exact').limit(1).execute()
            total_count = response.count if hasattr(response, 'count') else 0
            
            # 获取样本数据
            sample_response = supabase.table(table).select("*").limit(5).execute()
            sample_data = sample_response.data
            
            print(f"{table}:")
            print(f"  记录数: {total_count}")
            
            if sample_data:
                df = pd.DataFrame(sample_data)
                print(f"  字段: {list(df.columns)}")
                
                # 检查日期字段
                date_columns = [col for col in df.columns if 'date' in col.lower()]
                if date_columns:
                    for date_col in date_columns:
                        if df[date_col].notna().any():
                            print(f"  日期范围({date_col}): {df[date_col].min()} 至 {df[date_col].max()}")
                
                print(f"  样本数据: {len(sample_data)} 条")
            else:
                print(f"  样本数据: 0 条")
            
        except Exception as e:
            print(f"{table}: 查询失败 - {str(e)[:50]}...")
        
        print()

def main():
    """主函数"""
    print("Supabase数据检查")
    print("=" * 60)
    
    try:
        check_tables()
        print("检查完成！")
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    main()