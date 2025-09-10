#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版游资跟投策略回测系统
集成实时股价数据进行完整的策略回测验证
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedHotMoneyStrategy:
    """增强版游资跟投策略"""
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.signals_cache = {}
        self.performance_cache = {}
        
    def get_dragon_tiger_data(self, limit=15000):
        """获取龙虎榜数据"""
        if not self.supabase:
            raise ValueError("Supabase客户端未初始化")
            
        try:
            logger.info(f"获取最新的{limit}条龙虎榜数据...")
            
            response = self.supabase.table('seat_daily').select("*").order('trade_date', desc=True).limit(limit).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                logger.info(f"SUCCESS: 获取龙虎榜数据 {len(df)} 条")
                
                # 数据预处理
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                numeric_columns = ['net_amt', 'buy_amt', 'sell_amt']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                return df
            else:
                logger.warning("未获取到任何数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return pd.DataFrame()
    
    def analyze_hotmoney_advanced(self, data, lookback_days=180):
        """高级游资表现分析"""
        if data.empty:
            return pd.DataFrame()
        
        logger.info("开始高级游资表现分析...")
        
        # 限制分析时间窗口
        cutoff_date = data['trade_date'].max() - timedelta(days=lookback_days)
        recent_data = data[data['trade_date'] >= cutoff_date]
        
        # 基础统计
        hotmoney_stats = recent_data.groupby('seat_name').agg({
            'net_amt': ['count', 'sum', 'mean', 'std', 'min', 'max'],
            'code': 'nunique',
            'trade_date': ['min', 'max', 'nunique']
        }).round(2)
        
        hotmoney_stats.columns = [
            '交易次数', '总净买入', '平均净买入', '净买入标准差', '最小净买入', '最大净买入',
            '涉及股票数', '最早交易日', '最晚交易日', '活跃天数'
        ]
        
        # 计算胜率和其他指标
        hotmoney_stats['胜率'] = (recent_data.groupby('seat_name')['net_amt']
                               .apply(lambda x: (x > 0).mean()) * 100).round(1)
        
        # 计算夏普比率 (简化版)
        hotmoney_stats['收益稳定性'] = (hotmoney_stats['平均净买入'] / 
                                  (hotmoney_stats['净买入标准差'] + 1)).round(2)
        
        # 计算集中度 (单笔最大投入占比)
        hotmoney_stats['投资集中度'] = (hotmoney_stats['最大净买入'] / 
                                   hotmoney_stats['总净买入'] * 100).round(1)
        
        # 计算频率因子 (交易频率)
        hotmoney_stats['交易频率'] = (hotmoney_stats['交易次数'] / 
                                 hotmoney_stats['活跃天数']).round(2)
        
        # 多维度综合评分算法
        # 标准化各项指标
        stats_norm = hotmoney_stats.copy()
        for col in ['交易次数', '总净买入', '涉及股票数', '活跃天数', '收益稳定性']:
            if col in stats_norm.columns and stats_norm[col].max() > 0:
                stats_norm[f'{col}_norm'] = stats_norm[col] / stats_norm[col].max()
        
        # 综合评分 - 权重优化
        hotmoney_stats['综合评分'] = (
            np.log1p(hotmoney_stats['交易次数']) * 6 +              # 交易经验
            (hotmoney_stats['总净买入'] / hotmoney_stats['总净买入'].max()) * 35 +  # 资金规模
            np.log1p(hotmoney_stats['涉及股票数']) * 8 +             # 多样化
            (hotmoney_stats['胜率'] / 100) * 15 +                    # 成功率
            (hotmoney_stats['收益稳定性'] / hotmoney_stats['收益稳定性'].max()) * 10 +  # 稳定性
            np.log1p(hotmoney_stats['活跃天数']) * 5 +               # 活跃度
            (1 / (hotmoney_stats['投资集中度'] / 100 + 0.1)) * 3      # 分散度奖励
        ).round(2)
        
        # 筛选条件 - 更严格的标准
        qualified = hotmoney_stats[
            (hotmoney_stats['交易次数'] >= 8) & 
            (hotmoney_stats['总净买入'] > 10000000) &  # 1000万以上
            (hotmoney_stats['胜率'] >= 40) &           # 胜率40%以上
            (hotmoney_stats['活跃天数'] >= 5) &         # 至少5天活跃
            (hotmoney_stats['涉及股票数'] >= 2)          # 至少涉及2只股票
        ].sort_values('综合评分', ascending=False)
        
        logger.info(f"高级筛选后符合条件的游资: {len(qualified)} 个")
        
        return qualified.reset_index()
    
    def generate_enhanced_signals(self, data, hotmoney_performance, 
                                lookback_days=45, top_n=15, min_net_buy=8000000):
        """生成增强版投资信号"""
        if data.empty or hotmoney_performance.empty:
            return []
        
        logger.info("开始生成增强版投资信号...")
        
        # 选择Top N 游资
        top_hotmoney = hotmoney_performance.head(top_n)
        
        # 获取最近N天数据
        recent_date = data['trade_date'].max()
        start_date = recent_date - timedelta(days=lookback_days)
        recent_data = data[data['trade_date'] >= start_date]
        
        logger.info(f"分析最近{lookback_days}天数据: {len(recent_data)} 条记录")
        
        signals = []
        
        for _, hotmoney in top_hotmoney.iterrows():
            seat_name = hotmoney['seat_name']
            score = hotmoney['综合评分']
            win_rate = hotmoney['胜率']
            stability = hotmoney['收益稳定性']
            
            # 获取该游资的大额买入
            hotmoney_trades = recent_data[
                (recent_data['seat_name'] == seat_name) & 
                (recent_data['net_amt'] >= min_net_buy)
            ].sort_values(['trade_date', 'net_amt'], ascending=[False, False])
            
            # 动态选择交易数量 - 根据游资评分
            max_trades = 5 if score >= 80 else 3 if score >= 60 else 2
            
            for _, trade in hotmoney_trades.head(max_trades).iterrows():
                # 动态权重计算 - 基于多个因子
                base_weight = min(0.06, trade['net_amt'] / 120000000)  # 基础权重
                score_multiplier = min(1.5, score / 70)               # 评分调整
                stability_multiplier = min(1.3, stability)            # 稳定性调整
                recency_multiplier = 1.0 + (7 - (recent_date - trade['trade_date']).days) * 0.05  # 时间衰减
                
                final_weight = base_weight * score_multiplier * stability_multiplier * max(0.5, recency_multiplier)
                final_weight = min(0.08, final_weight)  # 单个信号最大8%权重
                
                signals.append({
                    'stock_code': trade['code'],
                    'seat_name': seat_name,
                    'net_amount': trade['net_amt'],
                    'trade_date': trade['trade_date'].strftime('%Y-%m-%d'),
                    'score': score,
                    'win_rate': win_rate,
                    'stability': stability,
                    'weight': final_weight,
                    'confidence': min(100, (score + win_rate) / 2)  # 置信度
                })
        
        # 去重和优化 - 保留每个股票的最佳信号
        unique_signals = {}
        for signal in signals:
            stock = signal['stock_code']
            if (stock not in unique_signals or 
                signal['confidence'] > unique_signals[stock]['confidence']):
                unique_signals[stock] = signal
        
        final_signals = list(unique_signals.values())
        
        # 按置信度排序
        final_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 权重标准化 - 确保总权重不超过95%
        total_weight = sum(signal['weight'] for signal in final_signals)
        if total_weight > 0.95:
            scale_factor = 0.95 / total_weight
            for signal in final_signals:
                signal['weight'] *= scale_factor
        
        logger.info(f"生成增强版投资信号: {len(final_signals)} 个")
        
        return final_signals
    
    def get_stock_prices_batch(self, stock_codes, period="5d"):
        """批量获取股票价格数据"""
        logger.info(f"批量获取 {len(stock_codes)} 只股票的价格数据...")
        
        stock_data = {}
        
        def get_single_stock_data(stock_code):
            try:
                # 转换股票代码格式
                if '.SH' in stock_code:
                    ticker = stock_code.replace('.SH', '.SS')
                elif '.SZ' in stock_code:
                    ticker = stock_code.replace('.SZ', '.SZ')  
                elif '.BJ' in stock_code:
                    # 北交所股票暂时跳过
                    return stock_code, None
                else:
                    return stock_code, None
                
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period)
                
                if not hist.empty:
                    return stock_code, {
                        'data': hist,
                        'current_price': hist['Close'].iloc[-1],
                        'open_price': hist['Open'].iloc[-1],
                        'high_price': hist['High'].iloc[-1],
                        'low_price': hist['Low'].iloc[-1],
                        'volume': hist['Volume'].iloc[-1],
                        'change_pct': ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) > 1 else 0
                    }
                return stock_code, None
            except Exception as e:
                logger.warning(f"获取 {stock_code} 数据失败: {e}")
                return stock_code, None
        
        # 使用多线程批量获取
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_single_stock_data, code) for code in stock_codes]
            
            for future in as_completed(futures):
                stock_code, data = future.result()
                if data:
                    stock_data[stock_code] = data
        
        logger.info(f"成功获取 {len(stock_data)} 只股票的数据")
        return stock_data
    
    def backtest_signals(self, signals, days_forward=5):
        """回测投资信号表现"""
        if not signals:
            return {}
        
        logger.info(f"开始回测 {len(signals)} 个投资信号...")
        
        # 获取所有相关股票的价格数据
        stock_codes = [signal['stock_code'] for signal in signals]
        stock_data = self.get_stock_prices_batch(stock_codes, period="1mo")
        
        backtest_results = []
        
        for signal in signals:
            stock_code = signal['stock_code']
            
            if stock_code not in stock_data:
                continue
            
            try:
                data = stock_data[stock_code]['data']
                trade_date = pd.to_datetime(signal['trade_date']).tz_localize(None)
                
                # 确保数据索引也没有时区信息
                if data.index.tz is not None:
                    data.index = data.index.tz_localize(None)
                
                # 找到交易日期后的数据点
                future_data = data[data.index.date > trade_date.date()]
                
                if len(future_data) >= days_forward:
                    entry_price = future_data['Open'].iloc[0]  # 次日开盘价买入
                    exit_price = future_data['Close'].iloc[days_forward-1]  # N天后收盘价卖出
                    
                    returns = (exit_price - entry_price) / entry_price * 100
                    
                    backtest_results.append({
                        'stock_code': stock_code,
                        'seat_name': signal['seat_name'][:20] + "...",
                        'entry_date': future_data.index[0].strftime('%Y-%m-%d'),
                        'exit_date': future_data.index[days_forward-1].strftime('%Y-%m-%d'),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'returns_pct': returns,
                        'weight': signal['weight'],
                        'weighted_return': returns * signal['weight'],
                        'score': signal['score'],
                        'confidence': signal['confidence']
                    })
                    
            except Exception as e:
                logger.warning(f"回测 {stock_code} 失败: {e}")
        
        if not backtest_results:
            return {}
        
        # 计算策略整体表现
        df = pd.DataFrame(backtest_results)
        
        strategy_performance = {
            'total_signals': len(backtest_results),
            'successful_signals': len(df[df['returns_pct'] > 0]),
            'win_rate': len(df[df['returns_pct'] > 0]) / len(df) * 100,
            'avg_return': df['returns_pct'].mean(),
            'weighted_return': df['weighted_return'].sum(),
            'max_return': df['returns_pct'].max(),
            'min_return': df['returns_pct'].min(),
            'volatility': df['returns_pct'].std(),
            'total_weight': df['weight'].sum(),
            'best_signal': df.loc[df['returns_pct'].idxmax()].to_dict() if not df.empty else {},
            'worst_signal': df.loc[df['returns_pct'].idxmin()].to_dict() if not df.empty else {},
            'results_detail': backtest_results
        }
        
        logger.info(f"回测完成: 胜率 {strategy_performance['win_rate']:.1f}%, "
                   f"平均收益 {strategy_performance['avg_return']:.2f}%, "
                   f"加权收益 {strategy_performance['weighted_return']:.2f}%")
        
        return strategy_performance

def run_enhanced_strategy_analysis():
    """运行增强版策略分析"""
    from test_strategy_simple import get_supabase_client
    
    print("=" * 80)
    print("增强版游资跟投策略回测分析")
    print("=" * 80)
    
    try:
        # 初始化策略
        supabase = get_supabase_client()
        strategy = EnhancedHotMoneyStrategy(supabase)
        
        # 1. 获取数据
        print("\n1. 获取龙虎榜数据...")
        data = strategy.get_dragon_tiger_data()
        
        if data.empty:
            print("ERROR: 无法获取数据")
            return
        
        # 2. 高级游资分析
        print("\n2. 进行高级游资表现分析...")
        hotmoney_performance = strategy.analyze_hotmoney_advanced(data)
        
        if hotmoney_performance.empty:
            print("WARNING: 未找到符合条件的游资")
            return
        
        print(f"符合条件的优质游资: {len(hotmoney_performance)} 个")
        
        # 显示Top 10
        print(f"\nTop 10 游资:")
        for i, (_, hotmoney) in enumerate(hotmoney_performance.head(10).iterrows(), 1):
            name = hotmoney['seat_name'][:25] + "..." if len(hotmoney['seat_name']) > 25 else hotmoney['seat_name']
            print(f"  {i:2d}. {name}")
            print(f"      评分: {hotmoney['综合评分']:.1f}, 胜率: {hotmoney['胜率']:.1f}%, "
                  f"稳定性: {hotmoney['收益稳定性']:.2f}")
        
        # 3. 生成增强信号
        print("\n3. 生成增强版投资信号...")
        signals = strategy.generate_enhanced_signals(data, hotmoney_performance)
        
        if not signals:
            print("WARNING: 未生成有效信号")
            return
        
        print(f"成功生成 {len(signals)} 个增强版投资信号")
        
        # 4. 回测验证
        print("\n4. 进行回测验证...")
        backtest_results = strategy.backtest_signals(signals)
        
        if backtest_results:
            print(f"\n=== 回测结果 ===")
            print(f"测试信号数: {backtest_results['total_signals']}")
            print(f"成功信号数: {backtest_results['successful_signals']}")
            print(f"策略胜率: {backtest_results['win_rate']:.1f}%")
            print(f"平均收益: {backtest_results['avg_return']:.2f}%")
            print(f"加权收益: {backtest_results['weighted_return']:.2f}%")
            print(f"收益波动: {backtest_results['volatility']:.2f}%")
            print(f"最大收益: {backtest_results['max_return']:.2f}%")
            print(f"最大亏损: {backtest_results['min_return']:.2f}%")
            print(f"总权重: {backtest_results['total_weight']:.2%}")
            
            if backtest_results['best_signal']:
                best = backtest_results['best_signal']
                print(f"\n最佳信号: {best['stock_code']}, 收益: {best['returns_pct']:.2f}%")
            
            if backtest_results['worst_signal']:
                worst = backtest_results['worst_signal']
                print(f"最差信号: {worst['stock_code']}, 收益: {worst['returns_pct']:.2f}%")
        
        # 5. 保存详细结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"enhanced_strategy_result_{timestamp}.txt"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("增强版游资跟投策略回测结果\n")
            f.write(f"分析时间: {datetime.now()}\n")
            f.write(f"数据记录: {len(data)} 条\n")
            f.write(f"优质游资: {len(hotmoney_performance)} 个\n")
            f.write(f"投资信号: {len(signals)} 个\n\n")
            
            if backtest_results:
                f.write("=== 回测表现 ===\n")
                for key, value in backtest_results.items():
                    if key != 'results_detail':
                        f.write(f"{key}: {value}\n")
                
                f.write("\n=== 详细信号 ===\n")
                for signal in signals[:20]:
                    f.write(f"{signal}\n")
        
        print(f"\n详细结果已保存至: {result_file}")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"ERROR: 分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_enhanced_strategy_analysis()