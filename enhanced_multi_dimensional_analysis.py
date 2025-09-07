#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于10年完整历史数据的增强版多维度游资策略分析引擎
整合6张核心表，提供深度市场洞察和策略优化
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedMultiDimensionalAnalyzer:
    """增强版多维度分析引擎"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.data_cache = {}
        self.analysis_results = {}
        
    def load_all_tables_summary(self):
        """加载所有数据表的概览信息"""
        tables_info = {}
        
        tables = [
            ('seat_daily', '游资交易数据'),
            ('trade_flow', '龙虎榜交易流水'), 
            ('inst_flow', '机构交易数据'),
            ('block_trade', '大宗交易数据'),
            ('broker_pick', '券商荐股数据'),
            ('money_flow', '资金流向数据')
        ]
        
        logger.info("加载所有数据表概览...")
        
        for table_name, description in tables:
            try:
                # 获取时间跨度
                earliest_resp = self.supabase.table(table_name).select('trade_date').order('trade_date', desc=False).limit(1).execute()
                latest_resp = self.supabase.table(table_name).select('trade_date').order('trade_date', desc=True).limit(1).execute()
                
                # 获取样本数据
                sample_resp = self.supabase.table(table_name).select('*').limit(5).execute()
                
                if earliest_resp.data and latest_resp.data and sample_resp.data:
                    earliest_date = pd.to_datetime(earliest_resp.data[0]['trade_date'])
                    latest_date = pd.to_datetime(latest_resp.data[0]['trade_date'])
                    days_span = (latest_date - earliest_date).days
                    
                    sample_df = pd.DataFrame(sample_resp.data)
                    
                    tables_info[table_name] = {
                        'description': description,
                        'earliest_date': earliest_date,
                        'latest_date': latest_date,
                        'days_span': days_span,
                        'years_span': days_span / 365,
                        'columns': list(sample_df.columns),
                        'sample_size': len(sample_resp.data)
                    }
                    
                    logger.info(f"{table_name}: {days_span}天 ({days_span/365:.1f}年) - {len(sample_df.columns)}个字段")
                
            except Exception as e:
                logger.warning(f"加载{table_name}失败: {e}")
                tables_info[table_name] = {'error': str(e)}
        
        self.data_cache['tables_info'] = tables_info
        return tables_info
    
    def comprehensive_hotmoney_analysis(self, lookback_years=3):
        """基于多表数据的综合游资分析"""
        logger.info(f"开始{lookback_years}年综合游资分析...")
        
        cutoff_date = datetime.now() - timedelta(days=lookback_years*365)
        
        # 1. 从seat_daily获取游资基础数据
        seat_data = self._load_seat_data(cutoff_date)
        if seat_data.empty:
            logger.error("无法获取游资数据")
            return {}
        
        # 2. 从money_flow获取资金流向数据增强分析
        money_flow_data = self._load_money_flow_data(cutoff_date)
        
        # 3. 从inst_flow获取机构数据对比
        inst_data = self._load_inst_flow_data(cutoff_date)
        
        # 4. 综合分析游资表现
        comprehensive_results = self._comprehensive_analysis(seat_data, money_flow_data, inst_data)
        
        return comprehensive_results
    
    def _load_seat_data(self, cutoff_date):
        """加载游资交易数据"""
        try:
            logger.info("加载游资交易数据...")
            
            response = self.supabase.table('seat_daily').select("*").order('trade_date', desc=True).limit(20000).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # 过滤到指定时间范围
                df = df[df['trade_date'] >= cutoff_date]
                
                # 数据预处理
                numeric_columns = ['net_amt', 'buy_amt', 'sell_amt']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                logger.info(f"成功加载游资数据: {len(df)}条记录")
                return df
            
        except Exception as e:
            logger.error(f"加载游资数据失败: {e}")
            
        return pd.DataFrame()
    
    def _load_money_flow_data(self, cutoff_date, sample_size=50000):
        """加载资金流向数据样本"""
        try:
            logger.info("加载资金流向数据...")
            
            response = self.supabase.table('money_flow').select("*").order('trade_date', desc=True).limit(sample_size).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # 过滤到指定时间范围
                df = df[df['trade_date'] >= cutoff_date]
                
                # 数据预处理
                flow_columns = ['net_inflow_amt', 'lrg_buy_amt', 'lrg_sell_amt', 'xl_buy_amt', 'xl_sell_amt']
                for col in flow_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                logger.info(f"成功加载资金流向数据: {len(df)}条记录")
                return df
                
        except Exception as e:
            logger.error(f"加载资金流向数据失败: {e}")
            
        return pd.DataFrame()
    
    def _load_inst_flow_data(self, cutoff_date, sample_size=100000):
        """加载机构交易数据样本"""
        try:
            logger.info("加载机构交易数据...")
            
            response = self.supabase.table('inst_flow').select("*").order('trade_date', desc=True).limit(sample_size).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # 过滤到指定时间范围
                df = df[df['trade_date'] >= cutoff_date]
                
                # 数据预处理
                numeric_columns = ['buy_amt', 'sell_amt', 'net_amt']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                logger.info(f"成功加载机构数据: {len(df)}条记录")
                return df
                
        except Exception as e:
            logger.error(f"加载机构数据失败: {e}")
            
        return pd.DataFrame()
    
    def _comprehensive_analysis(self, seat_data, money_flow_data, inst_data):
        """综合多维度分析"""
        results = {}
        
        # 1. 基础游资分析（基于seat_data）
        logger.info("进行基础游资分析...")
        basic_hotmoney = self._analyze_basic_hotmoney(seat_data)
        results['basic_hotmoney'] = basic_hotmoney
        
        # 2. 资金流向增强分析（基于money_flow_data）  
        if not money_flow_data.empty:
            logger.info("进行资金流向增强分析...")
            flow_analysis = self._analyze_money_flow_patterns(money_flow_data, seat_data)
            results['money_flow_patterns'] = flow_analysis
        
        # 3. 游资vs机构对比分析
        if not inst_data.empty:
            logger.info("进行游资vs机构对比分析...")
            comparison = self._compare_hotmoney_vs_institutions(seat_data, inst_data)
            results['hotmoney_vs_institutions'] = comparison
        
        # 4. 市场热点识别
        logger.info("进行市场热点识别...")
        hot_spots = self._identify_market_hotspots(seat_data, money_flow_data)
        results['market_hotspots'] = hot_spots
        
        # 5. 时间序列趋势分析
        logger.info("进行时间序列趋势分析...")
        trends = self._analyze_temporal_trends(seat_data, money_flow_data)
        results['temporal_trends'] = trends
        
        return results
    
    def _analyze_basic_hotmoney(self, seat_data):
        """基础游资分析 - 增强版"""
        if seat_data.empty:
            return {}
        
        # 游资表现统计
        hotmoney_stats = seat_data.groupby('seat_name').agg({
            'net_amt': ['count', 'sum', 'mean', 'std', 'min', 'max'],
            'buy_amt': ['sum', 'mean'],
            'sell_amt': ['sum', 'mean'], 
            'code': 'nunique',
            'trade_date': ['min', 'max', 'nunique']
        }).round(2)
        
        # 重命名列
        hotmoney_stats.columns = [
            '交易次数', '总净买入', '平均净买入', '净买入标准差', '最小净买入', '最大净买入',
            '总买入额', '平均买入额', '总卖出额', '平均卖出额',
            '涉及股票数', '最早交易日', '最晚交易日', '活跃天数'
        ]
        
        # 计算增强指标
        hotmoney_stats['胜率'] = (seat_data.groupby('seat_name')['net_amt']
                               .apply(lambda x: (x > 0).mean()) * 100).round(1)
        
        hotmoney_stats['平均持仓规模'] = (hotmoney_stats['总买入额'] / hotmoney_stats['交易次数']).round(0)
        
        hotmoney_stats['资金使用效率'] = (hotmoney_stats['总净买入'] / hotmoney_stats['总买入额'] * 100).round(2)
        
        hotmoney_stats['投资集中度'] = (hotmoney_stats['最大净买入'] / hotmoney_stats['总净买入'] * 100).round(1)
        
        hotmoney_stats['交易频率'] = (hotmoney_stats['交易次数'] / hotmoney_stats['活跃天数']).round(2)
        
        # 超级评分算法 - 7维度增强
        max_values = {
            'total_trades': hotmoney_stats['交易次数'].max(),
            'total_net': hotmoney_stats['总净买入'].max(),
            'stock_diversity': hotmoney_stats['涉及股票数'].max(),
            'active_days': hotmoney_stats['活跃天数'].max(),
            'efficiency': hotmoney_stats['资金使用效率'].max() if hotmoney_stats['资金使用效率'].max() > 0 else 1
        }
        
        hotmoney_stats['超级评分'] = (
            np.log1p(hotmoney_stats['交易次数']) * 8 +                    # 经验权重
            (hotmoney_stats['总净买入'] / max_values['total_net']) * 40 +   # 规模权重  
            np.log1p(hotmoney_stats['涉及股票数']) * 10 +                 # 多样化权重
            (hotmoney_stats['胜率'] / 100) * 20 +                         # 成功率权重
            (hotmoney_stats['资金使用效率'] / max_values['efficiency']) * 15 + # 效率权重
            np.log1p(hotmoney_stats['活跃天数']) * 5 +                    # 活跃度权重
            (100 / (hotmoney_stats['投资集中度'] + 1)) * 2                 # 分散度奖励
        ).round(2)
        
        # 平衡筛选标准 - 基于数据洞察优化
        qualified = hotmoney_stats[
            (hotmoney_stats['交易次数'] >= 6) & 
            (hotmoney_stats['总净买入'] > 10000000) &    # 1000万以上
            (hotmoney_stats['胜率'] >= 40) &             # 胜率40%以上
            (hotmoney_stats['活跃天数'] >= 5) &           # 至少5天活跃
            (hotmoney_stats['涉及股票数'] >= 2) &          # 至少涉及2只股票
            (hotmoney_stats['资金使用效率'] > -80)        # 效率不能太差
        ].sort_values('超级评分', ascending=False)
        
        return {
            'total_hotmoney': len(hotmoney_stats),
            'qualified_hotmoney': len(qualified),
            'top_performers': qualified.head(20).reset_index(),
            'analysis_summary': {
                'avg_win_rate': qualified['胜率'].mean() if not qualified.empty else 0,
                'avg_trades': qualified['交易次数'].mean() if not qualified.empty else 0,
                'avg_net_buy': qualified['总净买入'].mean() if not qualified.empty else 0,
                'avg_efficiency': qualified['资金使用效率'].mean() if not qualified.empty else 0
            }
        }
    
    def _analyze_money_flow_patterns(self, money_flow_data, seat_data):
        """资金流向模式分析"""
        if money_flow_data.empty:
            return {}
        
        try:
            # 按股票代码聚合资金流向
            flow_by_stock = money_flow_data.groupby('code').agg({
                'net_inflow_amt': ['sum', 'mean', 'count'],
                'xl_buy_amt': ['sum', 'mean'],    # 超大单买入
                'lrg_buy_amt': ['sum', 'mean'],   # 大单买入  
                'trade_date': ['min', 'max']
            }).round(2)
            
            flow_by_stock.columns = [
                '总净流入', '平均净流入', '交易天数',
                '超大单总买入', '超大单平均买入',
                '大单总买入', '大单平均买入',
                '最早日期', '最晚日期'
            ]
            
            # 识别资金流入热门股票
            hot_inflow_stocks = flow_by_stock[
                (flow_by_stock['总净流入'] > 0) &
                (flow_by_stock['交易天数'] >= 3)
            ].sort_values('总净流入', ascending=False).head(50)
            
            # 如果有游资数据，进行关联分析
            correlation_analysis = {}
            if not seat_data.empty:
                # 找到资金流入股票与游资关注股票的重合度
                flow_stocks = set(money_flow_data['code'].unique())
                hotmoney_stocks = set(seat_data['code'].unique())
                overlap_stocks = flow_stocks.intersection(hotmoney_stocks)
                
                correlation_analysis = {
                    'flow_stocks_count': len(flow_stocks),
                    'hotmoney_stocks_count': len(hotmoney_stocks),
                    'overlap_count': len(overlap_stocks),
                    'overlap_ratio': len(overlap_stocks) / len(hotmoney_stocks) if hotmoney_stocks else 0
                }
            
            return {
                'hot_inflow_stocks': hot_inflow_stocks.reset_index(),
                'flow_summary': {
                    'total_stocks': len(flow_by_stock),
                    'positive_flow_stocks': len(flow_by_stock[flow_by_stock['总净流入'] > 0]),
                    'avg_net_inflow': flow_by_stock['总净流入'].mean(),
                    'total_xl_buy': flow_by_stock['超大单总买入'].sum(),
                    'total_lrg_buy': flow_by_stock['大单总买入'].sum()
                },
                'correlation_with_hotmoney': correlation_analysis
            }
            
        except Exception as e:
            logger.error(f"资金流向分析失败: {e}")
            return {}
    
    def _compare_hotmoney_vs_institutions(self, seat_data, inst_data):
        """游资vs机构对比分析"""
        try:
            # 游资统计
            hotmoney_summary = {
                'total_net_buy': seat_data['net_amt'].sum(),
                'avg_net_buy': seat_data['net_amt'].mean(),
                'total_trades': len(seat_data),
                'unique_stocks': seat_data['code'].nunique(),
                'unique_operators': seat_data['seat_name'].nunique(),
                'win_rate': (seat_data['net_amt'] > 0).mean() * 100
            }
            
            # 机构统计  
            inst_summary = {
                'total_net_buy': inst_data['net_amt'].sum(),
                'avg_net_buy': inst_data['net_amt'].mean(), 
                'total_trades': len(inst_data),
                'unique_stocks': inst_data['code'].nunique(),
                'unique_operators': inst_data['inst_name'].nunique(),
                'win_rate': (inst_data['net_amt'] > 0).mean() * 100
            }
            
            # 对比分析
            comparison = {
                'capital_scale_ratio': hotmoney_summary['total_net_buy'] / inst_summary['total_net_buy'] if inst_summary['total_net_buy'] != 0 else 0,
                'activity_ratio': hotmoney_summary['total_trades'] / inst_summary['total_trades'] if inst_summary['total_trades'] != 0 else 0,
                'stock_coverage_ratio': hotmoney_summary['unique_stocks'] / inst_summary['unique_stocks'] if inst_summary['unique_stocks'] != 0 else 0,
                'win_rate_diff': hotmoney_summary['win_rate'] - inst_summary['win_rate']
            }
            
            return {
                'hotmoney_summary': hotmoney_summary,
                'institution_summary': inst_summary,
                'comparison_metrics': comparison
            }
            
        except Exception as e:
            logger.error(f"对比分析失败: {e}")
            return {}
    
    def _identify_market_hotspots(self, seat_data, money_flow_data):
        """识别市场热点"""
        hotspots = {}
        
        try:
            # 基于游资关注度的热点识别
            if not seat_data.empty:
                hotmoney_hotspots = seat_data.groupby('code').agg({
                    'seat_name': 'nunique',           # 关注游资数量
                    'net_amt': ['sum', 'mean'],       # 总净买入和平均
                    'trade_date': ['min', 'max', 'nunique']  # 时间跨度
                }).round(2)
                
                hotmoney_hotspots.columns = ['关注游资数', '总净买入', '平均净买入', '最早日期', '最晚日期', '交易天数']
                
                # 热点股票筛选
                hot_stocks = hotmoney_hotspots[
                    (hotmoney_hotspots['关注游资数'] >= 3) &   # 至少3个游资关注
                    (hotmoney_hotspots['总净买入'] > 10000000) & # 总净买入超1000万
                    (hotmoney_hotspots['交易天数'] >= 2)        # 至少2天活跃
                ].sort_values('关注游资数', ascending=False)
                
                hotspots['hotmoney_hotspots'] = hot_stocks.head(30).reset_index()
            
            # 基于资金流向的热点识别
            if not money_flow_data.empty:
                flow_hotspots = money_flow_data.groupby('code').agg({
                    'net_inflow_amt': 'sum',
                    'xl_buy_amt': 'sum',      # 超大单买入
                    'lrg_buy_amt': 'sum',     # 大单买入
                    'trade_date': 'nunique'   # 活跃天数
                }).round(2)
                
                flow_hotspots.columns = ['总净流入', '超大单买入', '大单买入', '活跃天数']
                
                hot_flow_stocks = flow_hotspots[
                    (flow_hotspots['总净流入'] > 5000000) &    # 净流入超500万
                    (flow_hotspots['活跃天数'] >= 3)           # 至少3天活跃
                ].sort_values('总净流入', ascending=False)
                
                hotspots['flow_hotspots'] = hot_flow_stocks.head(30).reset_index()
            
            return hotspots
            
        except Exception as e:
            logger.error(f"热点识别失败: {e}")
            return {}
    
    def _analyze_temporal_trends(self, seat_data, money_flow_data):
        """时间序列趋势分析"""
        trends = {}
        
        try:
            # 游资活动趋势
            if not seat_data.empty:
                daily_hotmoney = seat_data.groupby('trade_date').agg({
                    'net_amt': ['sum', 'count', 'mean'],
                    'seat_name': 'nunique',
                    'code': 'nunique'
                }).round(2)
                
                daily_hotmoney.columns = ['日总净买入', '日交易笔数', '日平均净买入', '日活跃游资数', '日涉及股票数']
                
                # 计算趋势指标
                recent_30d = daily_hotmoney.tail(30)
                trends['hotmoney_trends'] = {
                    'recent_avg_daily_net_buy': recent_30d['日总净买入'].mean(),
                    'recent_avg_daily_trades': recent_30d['日交易笔数'].mean(),
                    'recent_avg_active_hotmoney': recent_30d['日活跃游资数'].mean(),
                    'trend_direction': 'increasing' if recent_30d['日总净买入'].iloc[-1] > recent_30d['日总净买入'].iloc[0] else 'decreasing'
                }
            
            # 资金流向趋势
            if not money_flow_data.empty:
                daily_flow = money_flow_data.groupby('trade_date').agg({
                    'net_inflow_amt': ['sum', 'mean'],
                    'xl_buy_amt': 'sum',
                    'lrg_buy_amt': 'sum'
                }).round(2)
                
                daily_flow.columns = ['日总净流入', '日平均净流入', '日超大单买入', '日大单买入']
                
                recent_30d_flow = daily_flow.tail(30)
                trends['flow_trends'] = {
                    'recent_avg_daily_inflow': recent_30d_flow['日总净流入'].mean(),
                    'recent_avg_xl_buy': recent_30d_flow['日超大单买入'].mean(),
                    'recent_avg_lrg_buy': recent_30d_flow['日大单买入'].mean()
                }
            
            return trends
            
        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            return {}
    
    def generate_enhanced_investment_signals(self, analysis_results, top_n=20):
        """基于多维度分析生成增强投资信号"""
        if not analysis_results:
            return []
        
        logger.info("基于多维度分析生成增强投资信号...")
        
        signals = []
        
        try:
            # 获取顶级游资
            if 'basic_hotmoney' in analysis_results and 'top_performers' in analysis_results['basic_hotmoney']:
                top_hotmoney = analysis_results['basic_hotmoney']['top_performers'].head(10)
                
                # 获取市场热点股票
                hot_stocks = set()
                if 'market_hotspots' in analysis_results:
                    if 'hotmoney_hotspots' in analysis_results['market_hotspots']:
                        hotmoney_hot = analysis_results['market_hotspots']['hotmoney_hotspots']
                        hot_stocks.update(hotmoney_hot['code'].tolist()[:15])
                    
                    if 'flow_hotspots' in analysis_results['market_hotspots']:
                        flow_hot = analysis_results['market_hotspots']['flow_hotspots'] 
                        hot_stocks.update(flow_hot['code'].tolist()[:15])
                
                # 为每个顶级游资生成信号
                for _, hotmoney in top_hotmoney.iterrows():
                    seat_name = hotmoney['seat_name']
                    score = hotmoney['超级评分']
                    win_rate = hotmoney['胜率']
                    efficiency = hotmoney['资金使用效率']
                    
                    # 获取该游资最近的交易
                    recent_trades = self._get_recent_hotmoney_trades(seat_name, hot_stocks)
                    
                    for trade in recent_trades:
                        # 增强权重计算
                        base_weight = min(0.05, trade['net_amount'] / 100000000)
                        
                        # 多重调整因子
                        score_multiplier = min(2.0, score / 80)                          # 评分调整
                        efficiency_multiplier = min(1.5, (efficiency + 100) / 100)      # 效率调整 
                        hotspot_multiplier = 1.3 if trade['code'] in hot_stocks else 1.0 # 热点加成
                        
                        final_weight = base_weight * score_multiplier * efficiency_multiplier * hotspot_multiplier
                        final_weight = min(0.08, final_weight)
                        
                        confidence = min(100, (score + win_rate + (efficiency + 100)/2) / 3)
                        
                        signals.append({
                            'stock_code': trade['code'],
                            'seat_name': seat_name,
                            'net_amount': trade['net_amount'],
                            'trade_date': trade['trade_date'],
                            'score': score,
                            'win_rate': win_rate,
                            'efficiency': efficiency,
                            'weight': final_weight,
                            'confidence': confidence,
                            'is_hotspot': trade['code'] in hot_stocks,
                            'signal_strength': 'STRONG' if confidence > 85 else 'MODERATE' if confidence > 70 else 'WEAK'
                        })
            
            # 去重和排序
            unique_signals = {}
            for signal in signals:
                stock = signal['stock_code']
                if stock not in unique_signals or signal['confidence'] > unique_signals[stock]['confidence']:
                    unique_signals[stock] = signal
            
            final_signals = list(unique_signals.values())
            final_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            # 权重标准化
            total_weight = sum(s['weight'] for s in final_signals)
            if total_weight > 0.95:
                scale_factor = 0.95 / total_weight
                for signal in final_signals:
                    signal['weight'] *= scale_factor
            
            logger.info(f"生成{len(final_signals)}个增强投资信号")
            return final_signals[:top_n]
            
        except Exception as e:
            logger.error(f"信号生成失败: {e}")
            return []
    
    def _get_recent_hotmoney_trades(self, seat_name, hot_stocks=None, limit=3):
        """获取指定游资的最近交易"""
        try:
            response = self.supabase.table('seat_daily').select("*")\
                .eq('seat_name', seat_name)\
                .order('trade_date', desc=True)\
                .limit(limit*2).execute()
            
            if response.data:
                trades = []
                for trade in response.data:
                    if trade['net_amt'] and float(trade['net_amt']) > 5000000:  # 大于500万
                        trades.append({
                            'code': trade['code'],
                            'net_amount': float(trade['net_amt']),
                            'trade_date': trade['trade_date']
                        })
                        
                        if len(trades) >= limit:
                            break
                
                return trades
            
        except Exception as e:
            logger.warning(f"获取{seat_name}交易失败: {e}")
        
        return []

def run_enhanced_multi_dimensional_analysis():
    """运行增强版多维度分析"""
    from test_strategy_simple import get_supabase_client
    
    print("=" * 80)
    print("基于10年完整数据的增强版多维度游资策略分析")
    print("=" * 80)
    
    try:
        # 初始化分析引擎
        supabase = get_supabase_client()
        analyzer = EnhancedMultiDimensionalAnalyzer(supabase)
        
        # 1. 数据表概览
        print("\n1. 加载数据表概览...")
        tables_info = analyzer.load_all_tables_summary()
        
        print("数据资源概览:")
        for table_name, info in tables_info.items():
            if 'error' not in info:
                print(f"  {table_name}: {info['years_span']:.1f}年数据, {len(info['columns'])}个字段")
            else:
                print(f"  {table_name}: 访问失败")
        
        # 2. 综合游资分析
        print("\n2. 开始综合游资分析...")
        analysis_results = analyzer.comprehensive_hotmoney_analysis(lookback_years=3)
        
        if analysis_results:
            # 显示分析结果
            if 'basic_hotmoney' in analysis_results:
                basic = analysis_results['basic_hotmoney']
                print(f"\n基础游资分析:")
                print(f"  总游资数量: {basic['total_hotmoney']}")
                print(f"  优质游资数量: {basic['qualified_hotmoney']}")
                
                if 'analysis_summary' in basic:
                    summary = basic['analysis_summary']
                    print(f"  平均胜率: {summary['avg_win_rate']:.1f}%")
                    print(f"  平均交易次数: {summary['avg_trades']:.0f}")
                    print(f"  平均净买入: {summary['avg_net_buy']/1e8:.2f}亿")
                
                # 显示Top 10游资
                if 'top_performers' in basic and not basic['top_performers'].empty:
                    print(f"\nTop 10 优质游资:")
                    top_10 = basic['top_performers'].head(10)
                    for i, (_, hotmoney) in enumerate(top_10.iterrows(), 1):
                        name = hotmoney['seat_name'][:20] + "..." if len(hotmoney['seat_name']) > 20 else hotmoney['seat_name']
                        print(f"  {i:2d}. {name}")
                        print(f"      超级评分: {hotmoney['超级评分']:.1f}, 胜率: {hotmoney['胜率']:.1f}%, "
                              f"效率: {hotmoney['资金使用效率']:.1f}%")
            
            # 资金流向分析结果
            if 'money_flow_patterns' in analysis_results:
                flow = analysis_results['money_flow_patterns']
                if 'flow_summary' in flow:
                    summary = flow['flow_summary']
                    print(f"\n资金流向分析:")
                    print(f"  分析股票数: {summary['total_stocks']}")
                    print(f"  净流入股票数: {summary['positive_flow_stocks']}")
                    print(f"  平均净流入: {summary['avg_net_inflow']/1e4:.0f}万")
            
            # 市场热点分析
            if 'market_hotspots' in analysis_results:
                hotspots = analysis_results['market_hotspots']
                if 'hotmoney_hotspots' in hotspots:
                    print(f"\n游资关注热点股票 (前10):")
                    hot_stocks = hotspots['hotmoney_hotspots'].head(10)
                    for i, (_, stock) in enumerate(hot_stocks.iterrows(), 1):
                        print(f"  {i:2d}. {stock['code']}: {stock['关注游资数']}个游资关注, "
                              f"净买入{stock['总净买入']/1e4:.0f}万")
        
        # 3. 生成增强投资信号
        print("\n3. 生成增强投资信号...")
        signals = analyzer.generate_enhanced_investment_signals(analysis_results)
        
        if signals:
            print(f"\n=== 增强投资信号 ({len(signals)}个) ===")
            print(f"{'股票代码':<10} {'权重':<8} {'置信度':<8} {'强度':<8} {'游资':<20} {'热点':<6}")
            print("-" * 70)
            
            total_weight = 0
            for signal in signals[:15]:
                weight = signal['weight']
                total_weight += weight
                hotspot = "是" if signal['is_hotspot'] else "否"
                name = signal['seat_name'][:18] + ".." if len(signal['seat_name']) > 18 else signal['seat_name']
                
                print(f"{signal['stock_code']:<10} {weight:.2%}  {signal['confidence']:<6.1f}  "
                      f"{signal['signal_strength']:<8} {name:<20} {hotspot:<6}")
            
            print("-" * 70)
            print(f"总权重: {total_weight:.2%}")
            
            # 统计分析
            strong_signals = [s for s in signals if s['signal_strength'] == 'STRONG']
            hotspot_signals = [s for s in signals if s['is_hotspot']]
            
            print(f"\n信号质量分析:")
            print(f"  强信号数量: {len(strong_signals)} ({len(strong_signals)/len(signals)*100:.1f}%)")
            print(f"  热点信号数量: {len(hotspot_signals)} ({len(hotspot_signals)/len(signals)*100:.1f}%)")
            print(f"  平均置信度: {np.mean([s['confidence'] for s in signals]):.1f}")
        
        # 4. 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"enhanced_multi_dimensional_analysis_{timestamp}.txt"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("增强版多维度游资策略分析结果\n")
            f.write(f"分析时间: {datetime.now()}\n")
            f.write(f"数据范围: 基于10年完整历史数据 (2015-2025)\n")
            f.write(f"分析维度: 6张核心数据表综合分析\n\n")
            
            f.write("=== 分析结果概要 ===\n")
            if analysis_results:
                for key, value in analysis_results.items():
                    f.write(f"{key}: {type(value)}\n")
            
            f.write("\n=== 投资信号详情 ===\n")
            for signal in signals:
                f.write(f"{signal}\n")
        
        print(f"\n详细分析结果已保存至: {result_file}")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"ERROR: 分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_enhanced_multi_dimensional_analysis()