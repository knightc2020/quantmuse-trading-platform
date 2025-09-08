#!/usr/bin/env python3
"""
简化的龙虎榜数据分析脚本
直接使用Supabase客户端分析数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from data_service.supabase_client import SupabaseDataClient

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_dragon_tiger_data():
    """分析龙虎榜数据"""
    print("\n" + "="*80)
    print("🐉 龙虎榜数据分析报告")
    print("="*80)
    
    # 初始化客户端
    client = SupabaseDataClient()
    
    # 获取数据概览
    print(f"\n📊 数据概览:")
    
    # 检查各表的数据
    tables = ['seat_daily', 'trade_flow', 'inst_flow', 'block_trade', 'broker_pick', 'money_flow']
    
    for table in tables:
        try:
            # 获取最新数据
            data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', table, limit=1000)
            if data is not None and not data.empty:
                print(f"  {table}: {len(data)} 条记录")
                
                # 显示样本数据
                if len(data) > 0:
                    print(f"    最新数据日期: {data['trade_date'].max() if 'trade_date' in data.columns else 'N/A'}")
                    print(f"    数据列: {list(data.columns)}")
            else:
                print(f"  {table}: 无数据")
        except Exception as e:
            print(f"  {table}: 查询失败 - {e}")
    
    # 详细分析seat_daily表
    print(f"\n🏆 席位分析:")
    try:
        seat_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'seat_daily', limit=2000)
        if seat_data is not None and not seat_data.empty:
            print(f"  总记录数: {len(seat_data)}")
            
            # 分析席位
            if 'seat_name' in seat_data.columns:
                seat_counts = seat_data['seat_name'].value_counts().head(10)
                print(f"  前10名活跃席位:")
                for i, (seat, count) in enumerate(seat_counts.items(), 1):
                    print(f"    {i:2d}. {seat}: {count} 次交易")
            
            # 分析净买入
            if 'net_amt' in seat_data.columns:
                total_net = seat_data['net_amt'].sum()
                avg_net = seat_data['net_amt'].mean()
                print(f"  总净买入: {total_net:,.0f} 万元")
                print(f"  平均净买入: {avg_net:,.0f} 万元")
                
                # 净买入最多的席位
                if 'seat_name' in seat_data.columns:
                    seat_net = seat_data.groupby('seat_name')['net_amt'].sum().sort_values(ascending=False).head(5)
                    print(f"  净买入前5名席位:")
                    for i, (seat, net) in enumerate(seat_net.items(), 1):
                        print(f"    {i}. {seat}: {net:,.0f} 万元")
        else:
            print("  无席位数据")
    except Exception as e:
        print(f"  席位分析失败: {e}")
    
    # 详细分析trade_flow表
    print(f"\n🚀 股票表现分析:")
    try:
        trade_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'trade_flow', limit=2000)
        if trade_data is not None and not trade_data.empty:
            print(f"  总记录数: {len(trade_data)}")
            
            # 分析股票
            if 'name' in trade_data.columns:
                stock_counts = trade_data['name'].value_counts().head(10)
                print(f"  前10名上榜股票:")
                for i, (stock, count) in enumerate(stock_counts.items(), 1):
                    print(f"    {i:2d}. {stock}: {count} 次上榜")
            
            # 分析涨幅
            if 'pct_chg' in trade_data.columns:
                avg_pct = trade_data['pct_chg'].mean()
                max_pct = trade_data['pct_chg'].max()
                min_pct = trade_data['pct_chg'].min()
                print(f"  平均涨幅: {avg_pct:.2f}%")
                print(f"  最大涨幅: {max_pct:.2f}%")
                print(f"  最小涨幅: {min_pct:.2f}%")
                
                # 涨幅最大的股票
                if 'name' in trade_data.columns:
                    top_gainers = trade_data.nlargest(5, 'pct_chg')[['name', 'pct_chg', 'trade_date']]
                    print(f"  涨幅前5名股票:")
                    for i, row in top_gainers.iterrows():
                        print(f"    {row['name']}: {row['pct_chg']:.2f}% ({row['trade_date']})")
            
            # 分析龙虎榜资金
            if 'lhb_net_buy' in trade_data.columns:
                total_lhb_net = trade_data['lhb_net_buy'].sum()
                avg_lhb_net = trade_data['lhb_net_buy'].mean()
                print(f"  龙虎榜总净买入: {total_lhb_net:,.0f} 万元")
                print(f"  龙虎榜平均净买入: {avg_lhb_net:,.0f} 万元")
        else:
            print("  无交易流向数据")
    except Exception as e:
        print(f"  股票分析失败: {e}")
    
    # 分析机构流向
    print(f"\n🏦 机构资金分析:")
    try:
        inst_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'inst_flow', limit=2000)
        if inst_data is not None and not inst_data.empty:
            print(f"  总记录数: {len(inst_data)}")
            
            # 分析机构
            if 'inst_name' in inst_data.columns:
                inst_counts = inst_data['inst_name'].value_counts().head(10)
                print(f"  前10名活跃机构:")
                for i, (inst, count) in enumerate(inst_counts.items(), 1):
                    print(f"    {i:2d}. {inst}: {count} 次交易")
            
            # 分析机构净买入
            if 'net_amt' in inst_data.columns:
                total_inst_net = inst_data['net_amt'].sum()
                avg_inst_net = inst_data['net_amt'].mean()
                print(f"  机构总净买入: {total_inst_net:,.0f} 万元")
                print(f"  机构平均净买入: {avg_inst_net:,.0f} 万元")
                
                # 净买入最多的机构
                if 'inst_name' in inst_data.columns:
                    inst_net = inst_data.groupby('inst_name')['net_amt'].sum().sort_values(ascending=False).head(5)
                    print(f"  机构净买入前5名:")
                    for i, (inst, net) in enumerate(inst_net.items(), 1):
                        print(f"    {i}. {inst}: {net:,.0f} 万元")
        else:
            print("  无机构流向数据")
    except Exception as e:
        print(f"  机构分析失败: {e}")
    
    # 生成交易洞察
    print(f"\n💡 交易洞察:")
    insights = []
    
    try:
        # 基于seat_daily的洞察
        seat_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'seat_daily', limit=1000)
        if seat_data is not None and not seat_data.empty:
            if 'net_amt' in seat_data.columns:
                positive_trades = len(seat_data[seat_data['net_amt'] > 0])
                total_trades = len(seat_data)
                win_rate = (positive_trades / total_trades) * 100 if total_trades > 0 else 0
                insights.append(f"📊 龙虎榜交易胜率: {win_rate:.1f}%")
                
                avg_net = seat_data['net_amt'].mean()
                insights.append(f"💰 平均净买入: {avg_net:,.0f} 万元")
    except:
        pass
    
    try:
        # 基于trade_flow的洞察
        trade_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'trade_flow', limit=1000)
        if trade_data is not None and not trade_data.empty:
            if 'pct_chg' in trade_data.columns:
                avg_return = trade_data['pct_chg'].mean()
                insights.append(f"📈 上榜股票平均涨幅: {avg_return:.2f}%")
                
                high_gainers = len(trade_data[trade_data['pct_chg'] > 5])
                total_stocks = len(trade_data)
                high_gain_rate = (high_gainers / total_stocks) * 100 if total_stocks > 0 else 0
                insights.append(f"🚀 涨幅超过5%的股票占比: {high_gain_rate:.1f}%")
    except:
        pass
    
    try:
        # 基于inst_flow的洞察
        inst_data = client.get_dragon_tiger_data('2020-01-01', '2025-12-31', 'inst_flow', limit=1000)
        if inst_data is not None and not inst_data.empty:
            if 'net_amt' in inst_data.columns:
                inst_net = inst_data['net_amt'].sum()
                if inst_net > 0:
                    insights.append(f"🏦 机构资金净流入: {inst_net:,.0f} 万元")
                else:
                    insights.append(f"🏦 机构资金净流出: {abs(inst_net):,.0f} 万元")
    except:
        pass
    
    # 输出洞察
    if insights:
        for insight in insights:
            print(f"  {insight}")
    else:
        print("  暂无可用洞察")
    
    print("\n" + "="*80)
    print("分析完成！")

if __name__ == "__main__":
    analyze_dragon_tiger_data()
