#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查Supabase数据库表结构和数据量
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service.supabase_client import SupabaseDataClient
import logging

# 设置日志级别
logging.basicConfig(level=logging.WARNING)

def main():
    """检查Supabase数据库详细信息"""
    try:
        print("=" * 70)
        print("              Supabase数据库详细检查")
        print("=" * 70)
        
        client = SupabaseDataClient()
        
        # 尝试获取所有可能的表
        table_names = [
            'seat_daily',      # 龙虎榜席位数据
            'money_flow',      # 资金流向数据  
            'inst_flow',       # 机构流向数据
            'trade_flow',      # 交易流向数据
            'daily_quotes',    # 日线数据
            'stock_basic',     # 股票基础信息
            'market_data',     # 市场数据
            'financial_data',  # 财务数据
        ]
        
        from datetime import datetime
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        existing_tables = []
        total_records = 0
        
        for table_name in table_names:
            try:
                # 检查表是否存在并获取记录数
                response = client.client.table(table_name).select("*", count="exact").limit(1).execute()
                
                if hasattr(response, 'count') and response.count is not None:
                    count = response.count
                    total_records += count
                    existing_tables.append((table_name, count))
                    print(f"✅ {table_name:15} | 记录数: {count:>10,}")
                    
                    # 获取表结构信息 (获取一条记录查看字段)
                    if count > 0:
                        sample = client.client.table(table_name).select("*").limit(1).execute()
                        if sample.data:
                            fields = list(sample.data[0].keys())
                            print(f"    字段({len(fields)}): {', '.join(fields[:8])}" + ("..." if len(fields) > 8 else ""))
                            
                            # 获取日期范围
                            if 'trade_date' in fields:
                                date_range = client.client.table(table_name).select("trade_date").order("trade_date").limit(1).execute()
                                if date_range.data:
                                    min_date = date_range.data[0]['trade_date']
                                    date_range_max = client.client.table(table_name).select("trade_date").order("trade_date", desc=True).limit(1).execute()
                                    if date_range_max.data:
                                        max_date = date_range_max.data[0]['trade_date']
                                        print(f"    日期范围: {min_date} ~ {max_date}")
                    print()
                        
            except Exception as e:
                if "does not exist" in str(e):
                    print(f"❌ {table_name:15} | 表不存在")
                else:
                    print(f"⚠️  {table_name:15} | 检查失败: {str(e)[:50]}")
        
        print("=" * 70)
        print("汇总信息:")
        print(f"存在的表数量: {len(existing_tables)}")
        print(f"总记录数: {total_records:,}")
        print()
        
        if existing_tables:
            print("表详情:")
            for table_name, count in sorted(existing_tables, key=lambda x: x[1], reverse=True):
                percentage = (count / total_records * 100) if total_records > 0 else 0
                print(f"  {table_name:15} | {count:>10,} 条 ({percentage:5.1f}%)")
        
        print("=" * 70)
        
        # 检查最近数据
        print("最近数据检查:")
        for table_name, _ in existing_tables:
            try:
                recent = client.client.table(table_name).select("trade_date").order("trade_date", desc=True).limit(3).execute()
                if recent.data:
                    dates = [d['trade_date'] for d in recent.data]
                    print(f"  {table_name:15} | 最新3天: {', '.join(dates)}")
            except:
                pass
        
        return existing_tables, total_records
        
    except Exception as e:
        print(f"检查失败: {e}")
        return [], 0

if __name__ == "__main__":
    main()