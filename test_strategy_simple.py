#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版游资跟投策略测试
使用真实Supabase数据进行验证
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from supabase import create_client, Client
import os

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_supabase_client():
    """获取Supabase客户端"""
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")
    
    return create_client(url, key)

def test_supabase_connection():
    """测试Supabase连接"""
    try:
        supabase = get_supabase_client()
        
        # 测试连接 - 获取seat_daily表的几条记录
        response = supabase.table('seat_daily').select("*").limit(5).execute()
        
        if response.data:
            print(f"SUCCESS: Supabase连接成功")
            print(f"测试数据: {len(response.data)} 条记录")
            return True
        else:
            print("WARNING: Supabase连接成功但无数据")
            return False
            
    except Exception as e:
        print(f"ERROR: Supabase连接失败: {e}")
        return False

def get_dragon_tiger_data():
    """获取龙虎榜数据"""
    try:
        supabase = get_supabase_client()
        
        # 先获取最新的5000条seat_daily数据
        print(f"获取最新的龙虎榜数据...")
        
        response = supabase.table('seat_daily').select("*").order('trade_date', desc=True).limit(5000).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            print(f"SUCCESS: 获取龙虎榜数据 {len(df)} 条")
            
            # 数据预处理
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            numeric_columns = ['net_amt', 'buy_amt', 'sell_amt']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
        else:
            print("WARNING: 未获取到任何数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"ERROR: 获取数据失败: {e}")
        return pd.DataFrame()

def analyze_hotmoney_performance(data):
    """分析游资表现"""
    if data.empty:
        print("WARNING: 数据为空，无法分析")
        return pd.DataFrame()
    
    print(f"开始分析游资表现...")
    
    # 基础统计
    print(f"数据统计:")
    print(f"  - 总记录数: {len(data)}")
    print(f"  - 游资数量: {data['seat_name'].nunique()}")
    print(f"  - 股票数量: {data['code'].nunique()}")
    print(f"  - 时间跨度: {data['trade_date'].min()} 至 {data['trade_date'].max()}")
    
    # 游资表现分析
    hotmoney_stats = data.groupby('seat_name').agg({
        'net_amt': ['count', 'sum', 'mean'],
        'code': 'nunique'
    }).round(2)
    
    hotmoney_stats.columns = ['交易次数', '总净买入', '平均净买入', '涉及股票数']
    
    # 计算胜率
    hotmoney_stats['胜率'] = (data.groupby('seat_name')['net_amt'].apply(lambda x: (x > 0).mean()) * 100).round(1)
    
    # 综合评分
    hotmoney_stats['评分'] = (
        np.log1p(hotmoney_stats['交易次数']) * 5 +
        (hotmoney_stats['总净买入'] / hotmoney_stats['总净买入'].max()) * 40 +
        np.log1p(hotmoney_stats['涉及股票数']) * 8 +
        (hotmoney_stats['胜率'] / 100) * 10
    ).round(2)
    
    # 筛选条件
    qualified = hotmoney_stats[
        (hotmoney_stats['交易次数'] >= 5) & 
        (hotmoney_stats['总净买入'] > 0)
    ].sort_values('评分', ascending=False)
    
    print(f"\n符合条件的游资: {len(qualified)} 个")
    
    if not qualified.empty:
        print(f"\nTop 10 游资:")
        for i, (seat_name, row) in enumerate(qualified.head(10).iterrows(), 1):
            short_name = seat_name[:30] + "..." if len(seat_name) > 30 else seat_name
            print(f"  {i:2d}. {short_name}")
            print(f"      评分: {row['评分']:.1f}, 胜率: {row['胜率']:.1f}%, 交易: {int(row['交易次数'])}次")
    
    return qualified.reset_index()

def generate_investment_signals(data, hotmoney_performance):
    """生成投资信号"""
    if data.empty or hotmoney_performance.empty:
        print("WARNING: 无法生成信号 - 数据不足")
        return []
    
    print(f"\n开始生成投资信号...")
    
    # 选择Top 10 游资
    top_hotmoney = hotmoney_performance.head(10)
    
    # 获取最近30天数据
    recent_date = data['trade_date'].max()
    start_date = recent_date - timedelta(days=30)
    recent_data = data[data['trade_date'] >= start_date]
    
    print(f"分析最近30天数据: {len(recent_data)} 条记录")
    
    signals = []
    min_net_buy = 1000000  # 1000万
    
    for _, hotmoney in top_hotmoney.iterrows():
        seat_name = hotmoney['seat_name']
        score = hotmoney['评分']
        
        # 获取该游资的大额买入
        hotmoney_trades = recent_data[
            (recent_data['seat_name'] == seat_name) & 
            (recent_data['net_amt'] >= min_net_buy)
        ].sort_values('trade_date', ascending=False)
        
        # 取最近3笔大额买入
        for _, trade in hotmoney_trades.head(3).iterrows():
            signals.append({
                'stock_code': trade['code'],
                'seat_name': seat_name[:20] + "...",
                'net_amount': trade['net_amt'],
                'trade_date': trade['trade_date'].strftime('%Y-%m-%d'),
                'score': score,
                'weight': min(0.05, trade['net_amt'] / 50000000)  # 最大5%权重
            })
    
    # 去重并排序
    unique_signals = {}
    for signal in signals:
        stock = signal['stock_code']
        if stock not in unique_signals or signal['score'] > unique_signals[stock]['score']:
            unique_signals[stock] = signal
    
    final_signals = list(unique_signals.values())
    final_signals.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"生成投资信号: {len(final_signals)} 个")
    
    return final_signals

def main():
    """主函数"""
    print("="*60)
    print("游资跟投策略技术验证")
    print("使用真实Supabase数据")
    print("="*60)
    
    # 1. 测试连接
    print("\n1. 测试数据库连接:")
    if not test_supabase_connection():
        print("ERROR: 数据库连接失败，请检查配置")
        return
    
    # 2. 获取数据
    print("\n2. 获取龙虎榜数据:")
    dragon_tiger_data = get_dragon_tiger_data()
    
    if dragon_tiger_data.empty:
        print("ERROR: 未获取到数据")
        return
    
    # 3. 分析游资表现
    print("\n3. 分析游资表现:")
    hotmoney_performance = analyze_hotmoney_performance(dragon_tiger_data)
    
    # 4. 生成投资信号
    print("\n4. 生成投资信号:")
    signals = generate_investment_signals(dragon_tiger_data, hotmoney_performance)
    
    # 5. 展示结果
    if signals:
        print(f"\n=== 投资信号结果 ===")
        print(f"{'股票代码':<10} {'权重':<8} {'净买入(万)':<12} {'游资':<25} {'日期':<12} {'评分':<6}")
        print("-" * 80)
        
        total_weight = 0
        for signal in signals[:15]:  # 显示前15个
            weight = signal['weight']
            total_weight += weight
            print(f"{signal['stock_code']:<10} {weight:.2%}    "
                  f"{signal['net_amount']/10000:<10.0f}  "
                  f"{signal['seat_name']:<25} "
                  f"{signal['trade_date']:<12} "
                  f"{signal['score']:<6.1f}")
        
        print("-" * 80)
        print(f"总权重: {total_weight:.2%}")
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"strategy_validation_result_{timestamp}.txt"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("游资跟投策略验证结果\n")
            f.write(f"验证时间: {datetime.now()}\n")
            f.write(f"信号数量: {len(signals)}\n")
            f.write(f"总权重: {total_weight:.2%}\n")
            f.write("\n投资信号:\n")
            for signal in signals:
                f.write(f"{signal}\n")
        
        print(f"\nSUCCESS: 技术验证完成！")
        print(f"详细结果已保存至: {result_file}")
        
    else:
        print("WARNING: 未生成有效投资信号")
        print("可能原因:")
        print("  - 最近30天无大额游资交易")
        print("  - 参数设置过于严格")
        print("  - 数据质量问题")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()