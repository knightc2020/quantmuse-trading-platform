#!/usr/bin/env python3
"""
龙虎榜数据分析脚本
分析Supabase中的龙虎榜历史数据，提供交易洞察
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from data_service.supabase_client import SupabaseDataClient
import warnings
warnings.filterwarnings('ignore')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DragonTigerAnalyzer:
    """龙虎榜数据分析器"""
    
    def __init__(self):
        self.client = SupabaseDataClient()
        self.data = {}
        
    def load_data(self, days=30):
        """加载数据"""
        logger.info("开始加载龙虎榜数据...")
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            # 加载各表数据 - 使用更宽的时间范围
            start_date = '2020-01-01'  # 使用更早的起始日期
            
            self.data['seat_daily'] = self.client.get_dragon_tiger_data(
                start_date, end_date, 'seat_daily', limit=5000
            )
            
            self.data['trade_flow'] = self.client.get_dragon_tiger_data(
                start_date, end_date, 'trade_flow', limit=5000
            )
            
            self.data['inst_flow'] = self.client.get_dragon_tiger_data(
                start_date, end_date, 'inst_flow', limit=5000
            )
            
            self.data['block_trade'] = self.client.get_dragon_tiger_data(
                start_date, end_date, 'block_trade', limit=2000
            )
            
            logger.info("数据加载完成")
            return True
            
        except Exception as e:
            logger.error(f"数据加载失败: {e}")
            return False
    
    def analyze_seat_performance(self):
        """分析席位表现"""
        logger.info("分析席位表现...")
        
        if 'seat_daily' not in self.data or self.data['seat_daily'].empty:
            return None
            
        df = self.data['seat_daily'].copy()
        
        # 计算席位统计
        seat_stats = df.groupby('seat_name').agg({
            'net_amt': ['sum', 'mean', 'count'],
            'buy_amt': 'sum',
            'sell_amt': 'sum'
        }).round(2)
        
        seat_stats.columns = ['net_total', 'net_avg', 'trade_count', 'buy_total', 'sell_total']
        seat_stats['win_rate'] = (seat_stats['net_total'] > 0).astype(int)
        seat_stats['avg_trade_size'] = (seat_stats['buy_total'] + seat_stats['sell_total']) / seat_stats['trade_count']
        
        # 排序
        top_seats = seat_stats.sort_values('net_total', ascending=False).head(20)
        
        return {
            'top_seats': top_seats,
            'total_seats': len(seat_stats),
            'active_seats': len(seat_stats[seat_stats['trade_count'] >= 5])
        }
    
    def analyze_stock_performance(self):
        """分析股票表现"""
        logger.info("分析股票表现...")
        
        if 'trade_flow' not in self.data or self.data['trade_flow'].empty:
            return None
            
        df = self.data['trade_flow'].copy()
        
        # 计算股票统计
        stock_stats = df.groupby(['code', 'name']).agg({
            'pct_chg': ['mean', 'std', 'count'],
            'lhb_net_buy': 'sum',
            'lhb_turnover_ratio': 'mean',
            'close': 'last'
        }).round(2)
        
        stock_stats.columns = ['avg_pct_chg', 'pct_volatility', 'appear_count', 'net_buy_total', 'avg_turnover_ratio', 'last_price']
        
        # 筛选条件
        active_stocks = stock_stats[stock_stats['appear_count'] >= 3]
        top_performers = active_stocks.sort_values('avg_pct_chg', ascending=False).head(20)
        
        return {
            'top_performers': top_performers,
            'total_stocks': len(stock_stats),
            'active_stocks': len(active_stocks)
        }
    
    def analyze_market_trends(self):
        """分析市场趋势"""
        logger.info("分析市场趋势...")
        
        if 'trade_flow' not in self.data or self.data['trade_flow'].empty:
            return None
            
        df = self.data['trade_flow'].copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # 按日期聚合
        daily_stats = df.groupby('trade_date').agg({
            'pct_chg': ['mean', 'std'],
            'lhb_net_buy': 'sum',
            'lhb_turnover_ratio': 'mean',
            'code': 'count'
        }).round(2)
        
        daily_stats.columns = ['avg_pct_chg', 'pct_volatility', 'net_buy_total', 'avg_turnover_ratio', 'stock_count']
        
        # 计算趋势
        recent_5d = daily_stats.tail(5)
        trend_analysis = {
            'avg_daily_stocks': daily_stats['stock_count'].mean(),
            'avg_daily_return': daily_stats['avg_pct_chg'].mean(),
            'recent_5d_avg_return': recent_5d['avg_pct_chg'].mean(),
            'recent_5d_net_buy': recent_5d['net_buy_total'].sum(),
            'volatility_trend': daily_stats['pct_volatility'].tail(5).mean()
        }
        
        return {
            'daily_stats': daily_stats,
            'trend_analysis': trend_analysis
        }
    
    def analyze_institutional_flow(self):
        """分析机构资金流向"""
        logger.info("分析机构资金流向...")
        
        if 'inst_flow' not in self.data or self.data['inst_flow'].empty:
            return None
            
        df = self.data['inst_flow'].copy()
        
        # 机构统计
        inst_stats = df.groupby('inst_name').agg({
            'net_amt': ['sum', 'mean', 'count'],
            'buy_amt': 'sum',
            'sell_amt': 'sum'
        }).round(2)
        
        inst_stats.columns = ['net_total', 'net_avg', 'trade_count', 'buy_total', 'sell_total']
        inst_stats['activity_score'] = inst_stats['trade_count'] * abs(inst_stats['net_avg'])
        
        top_institutions = inst_stats.sort_values('net_total', ascending=False).head(15)
        
        return {
            'top_institutions': top_institutions,
            'total_institutions': len(inst_stats),
            'net_institutional_flow': inst_stats['net_total'].sum()
        }
    
    def generate_insights(self):
        """生成交易洞察"""
        logger.info("生成交易洞察...")
        
        insights = []
        
        # 席位分析洞察
        seat_analysis = self.analyze_seat_performance()
        if seat_analysis:
            top_seat = seat_analysis['top_seats'].index[0]
            top_net = seat_analysis['top_seats'].iloc[0]['net_total']
            insights.append(f"🏆 最活跃席位: {top_seat}，净买入 {top_net:,.0f} 万元")
            
            win_rate = seat_analysis['top_seats']['win_rate'].mean() * 100
            insights.append(f"📊 活跃席位胜率: {win_rate:.1f}%")
        
        # 股票分析洞察
        stock_analysis = self.analyze_stock_performance()
        if stock_analysis:
            best_stock = stock_analysis['top_performers'].index[0]
            best_return = stock_analysis['top_performers'].iloc[0]['avg_pct_chg']
            insights.append(f"🚀 表现最佳股票: {best_stock[1]}，平均涨幅 {best_return:.2f}%")
        
        # 市场趋势洞察
        trend_analysis = self.analyze_market_trends()
        if trend_analysis:
            trend = trend_analysis['trend_analysis']
            insights.append(f"📈 市场活跃度: 日均 {trend['avg_daily_stocks']:.0f} 只股票上榜")
            insights.append(f"💰 近期资金流向: 5日净买入 {trend['recent_5d_net_buy']:,.0f} 万元")
        
        # 机构分析洞察
        inst_analysis = self.analyze_institutional_flow()
        if inst_analysis:
            net_flow = inst_analysis['net_institutional_flow']
            flow_direction = "净买入" if net_flow > 0 else "净卖出"
            insights.append(f"🏦 机构资金: {flow_direction} {abs(net_flow):,.0f} 万元")
        
        return insights
    
    def print_analysis_report(self):
        """打印分析报告"""
        print("\n" + "="*80)
        print("🐉 龙虎榜数据分析报告")
        print("="*80)
        
        # 数据概览
        print(f"\n📊 数据概览:")
        for table_name, df in self.data.items():
            if df is not None and not df.empty:
                print(f"  {table_name}: {len(df)} 条记录")
            else:
                print(f"  {table_name}: 无数据")
        
        # 席位分析
        seat_analysis = self.analyze_seat_performance()
        if seat_analysis:
            print(f"\n🏆 席位分析:")
            print(f"  总席位数量: {seat_analysis['total_seats']}")
            print(f"  活跃席位数量: {seat_analysis['active_seats']}")
            print(f"\n  前10名活跃席位:")
            for i, (seat, stats) in enumerate(seat_analysis['top_seats'].head(10).iterrows()):
                print(f"    {i+1:2d}. {seat}: 净买入 {stats['net_total']:>10,.0f}万, 交易 {stats['trade_count']:>3d}次")
        
        # 股票分析
        stock_analysis = self.analyze_stock_performance()
        if stock_analysis:
            print(f"\n🚀 股票分析:")
            print(f"  总股票数量: {stock_analysis['total_stocks']}")
            print(f"  活跃股票数量: {stock_analysis['active_stocks']}")
            print(f"\n  前10名表现股票:")
            for i, ((code, name), stats) in enumerate(stock_analysis['top_performers'].head(10).iterrows()):
                print(f"    {i+1:2d}. {name}({code}): 平均涨幅 {stats['avg_pct_chg']:>6.2f}%, 上榜 {stats['appear_count']:>2d}次")
        
        # 市场趋势
        trend_analysis = self.analyze_market_trends()
        if trend_analysis:
            trend = trend_analysis['trend_analysis']
            print(f"\n📈 市场趋势:")
            print(f"  日均上榜股票: {trend['avg_daily_stocks']:.1f} 只")
            print(f"  平均日涨幅: {trend['avg_daily_return']:.2f}%")
            print(f"  近期5日平均涨幅: {trend['recent_5d_avg_return']:.2f}%")
            print(f"  近期5日净买入: {trend['recent_5d_net_buy']:,.0f} 万元")
        
        # 机构分析
        inst_analysis = self.analyze_institutional_flow()
        if inst_analysis:
            print(f"\n🏦 机构分析:")
            print(f"  总机构数量: {inst_analysis['total_institutions']}")
            print(f"  机构净流向: {inst_analysis['net_institutional_flow']:,.0f} 万元")
            print(f"\n  前10名活跃机构:")
            for i, (inst, stats) in enumerate(inst_analysis['top_institutions'].head(10).iterrows()):
                print(f"    {i+1:2d}. {inst}: 净买入 {stats['net_total']:>10,.0f}万, 交易 {stats['trade_count']:>3d}次")
        
        # 交易洞察
        insights = self.generate_insights()
        print(f"\n💡 交易洞察:")
        for insight in insights:
            print(f"  {insight}")
        
        print("\n" + "="*80)

def main():
    """主函数"""
    analyzer = DragonTigerAnalyzer()
    
    # 加载数据
    if not analyzer.load_data(days=30):
        print("❌ 数据加载失败")
        return
    
    # 生成分析报告
    analyzer.print_analysis_report()

if __name__ == "__main__":
    main()
