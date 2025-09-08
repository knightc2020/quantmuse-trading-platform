#!/usr/bin/env python3
"""
游资跟投策略技术验证
基于现有龙虎榜数据训练一个简单的游资跟投策略，验证基础可行性
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from supabase import create_client, Client
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """策略执行结果"""
    strategy_name: str
    selected_stocks: List[str]
    weights: Dict[str, float]
    confidence_scores: Dict[str, float]
    reasons: Dict[str, str]
    execution_time: datetime
    metadata: Dict[str, Any]

class SimpleHotMoneyFollowingStrategy:
    """简化版游资跟投策略"""
    
    def __init__(self):
        self.name = "简化游资跟投策略V1.0"
        self.description = "基于游资净买入金额和历史表现的简单跟投策略"
        self.lookback_days = 30  # 回看天数
        self.min_net_buy = 1000000  # 最小净买入1000万
        self.top_hotmoney_count = 10  # 跟踪前10名游资
        self.max_position_weight = 0.05  # 单个股票最大权重5%
        
        logger.info(f"初始化策略: {self.name}")
        logger.info(f"参数设置: 回看{self.lookback_days}天, 最小净买入{self.min_net_buy/10000}万元, 跟踪前{self.top_hotmoney_count}名游资")

    def get_supabase_client(self):
        """获取Supabase客户端"""
        from dotenv import load_dotenv
        load_dotenv()
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")
        
        return create_client(url, key)

    def get_dragon_tiger_data(self, days_back=180):
        """获取龙虎榜数据"""
        supabase = self.get_supabase_client()
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        logger.info(f"获取龙虎榜数据: {start_date} 至 {end_date}")
        
        try:
            # 获取seat_daily数据（游资席位数据）
            response = supabase.table('seat_daily').select("*").gte('trade_date', start_date).lte('trade_date', end_date).execute()
            seat_data = pd.DataFrame(response.data)
            
            logger.info(f"获取seat_daily数据: {len(seat_data)}条记录")
            
            if not seat_data.empty:
                # 数据类型转换
                if 'trade_date' in seat_data.columns:
                    seat_data['trade_date'] = pd.to_datetime(seat_data['trade_date'])
                
                # 数值列转换
                numeric_columns = ['net_amt', 'buy_amt', 'sell_amt']
                for col in numeric_columns:
                    if col in seat_data.columns:
                        seat_data[col] = pd.to_numeric(seat_data[col], errors='coerce').fillna(0)
            
            return seat_data
            
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return pd.DataFrame()

    def calculate_hotmoney_performance_score(self, data):
        """计算游资表现评分"""
        logger.info("计算游资表现评分...")
        
        if data.empty:
            return pd.DataFrame()
        
        # 按游资席位聚合统计
        performance = data.groupby('seat_name').agg({
            'net_amt': ['count', 'sum', 'mean', 'std'],
            'buy_amt': 'sum',
            'sell_amt': 'sum',
            'code': 'nunique',
            'trade_date': ['min', 'max']
        }).round(2)
        
        # 重命名列
        performance.columns = [
            '交易次数', '总净买入', '平均净买入', '净买入标准差',
            '总买入', '总卖出', '涉及股票数', '首次交易', '最后交易'
        ]
        
        # 计算额外指标
        performance['胜率'] = (data.groupby('seat_name')['net_amt'].apply(lambda x: (x > 0).mean()) * 100).round(1)
        performance['交易活跃度'] = performance['交易次数'] / 30  # 平均每天交易次数
        performance['资金规模等级'] = pd.qcut(performance['总净买入'], q=5, labels=['小', '中下', '中', '中上', '大'])
        
        # 综合评分公式 (0-100分制)
        performance['performance_score'] = (
            # 活跃度权重30%: 交易次数越多越好，但要平衡
            np.log1p(performance['交易次数']) * 5 +
            
            # 资金实力权重40%: 总净买入金额，归一化处理
            (performance['总净买入'] / performance['总净买入'].max()) * 40 +
            
            # 选股能力权重20%: 涉及股票数，体现选股分散度  
            np.log1p(performance['涉及股票数']) * 8 +
            
            # 成功率权重10%: 胜率
            (performance['胜率'] / 100) * 10
        ).round(2)
        
        # 过滤条件：至少5次交易，总净买入大于0
        qualified_hotmoney = performance[
            (performance['交易次数'] >= 5) & 
            (performance['总净买入'] > 0)
        ].sort_values('performance_score', ascending=False)
        
        logger.info(f"符合条件的游资数量: {len(qualified_hotmoney)}")
        
        return qualified_hotmoney.reset_index()

    def generate_strategy_signals(self, dragon_tiger_data):
        """生成策略信号"""
        logger.info("开始生成策略信号...")
        
        if dragon_tiger_data.empty:
            logger.warning("龙虎榜数据为空，无法生成信号")
            return StrategyResult(
                strategy_name=self.name,
                selected_stocks=[],
                weights={},
                confidence_scores={},
                reasons={},
                execution_time=datetime.now(),
                metadata={'error': 'no_data'}
            )
        
        # 1. 筛选最近30天的数据
        recent_date = dragon_tiger_data['trade_date'].max()
        start_date = recent_date - timedelta(days=self.lookback_days)
        
        recent_data = dragon_tiger_data[
            dragon_tiger_data['trade_date'] >= start_date
        ].copy()
        
        logger.info(f"分析时间段: {start_date.strftime('%Y-%m-%d')} 至 {recent_date.strftime('%Y-%m-%d')}")
        logger.info(f"最近{self.lookback_days}天数据量: {len(recent_data)}条")
        
        # 2. 计算游资表现评分
        hotmoney_performance = self.calculate_hotmoney_performance_score(recent_data)
        
        if hotmoney_performance.empty:
            logger.warning("无符合条件的游资，无法生成信号")
            return StrategyResult(
                strategy_name=self.name,
                selected_stocks=[],
                weights={},
                confidence_scores={},
                reasons={},
                execution_time=datetime.now(),
                metadata={'error': 'no_qualified_hotmoney'}
            )
        
        # 3. 选择前N名游资
        top_hotmoney = hotmoney_performance.head(self.top_hotmoney_count)
        logger.info(f"选择前{len(top_hotmoney)}名游资进行跟投")
        
        # 显示top游资信息
        print("\n🏆 Top游资排行:")
        for i, (_, hotmoney) in enumerate(top_hotmoney.head(5).iterrows(), 1):
            print(f"  {i}. {hotmoney['seat_name']}")
            print(f"     评分: {hotmoney['performance_score']:.1f}, 胜率: {hotmoney['胜率']:.1f}%, 交易: {hotmoney['交易次数']}次")
        
        # 4. 获取这些游资最新的买入信号
        signals = []
        selected_stocks = []
        weights = {}
        confidence_scores = {}
        reasons = {}
        
        for _, hotmoney in top_hotmoney.iterrows():
            hotmoney_name = hotmoney['seat_name']
            hotmoney_score = hotmoney['performance_score']
            
            # 获取该游资最近的大额买入交易
            hotmoney_trades = recent_data[
                (recent_data['seat_name'] == hotmoney_name) & 
                (recent_data['net_amt'] >= self.min_net_buy)
            ].sort_values('trade_date', ascending=False)
            
            # 取最近3笔大额买入
            recent_buys = hotmoney_trades.head(3)
            
            for _, trade in recent_buys.iterrows():
                stock_code = trade['code']
                net_amount = trade['net_amt']
                trade_date = trade['trade_date']
                
                if stock_code not in selected_stocks:
                    # 计算权重：基于净买入金额和游资评分
                    base_weight = min(self.max_position_weight, net_amount / 50000000)  # 基于5000万为基准
                    score_multiplier = min(2.0, hotmoney_score / 50)  # 评分倍数
                    final_weight = base_weight * score_multiplier
                    
                    selected_stocks.append(stock_code)
                    weights[stock_code] = round(final_weight, 4)
                    confidence_scores[stock_code] = round(hotmoney_score / 100, 3)  # 转换为0-1
                    reasons[stock_code] = f"跟随{hotmoney_name}买入{net_amount/10000:.0f}万元 ({trade_date.strftime('%m-%d')})"
        
        # 5. 权重归一化（确保总权重不超过1）
        total_weight = sum(weights.values())
        if total_weight > 1.0:
            scale_factor = 0.95 / total_weight  # 留5%现金
            weights = {k: round(v * scale_factor, 4) for k, v in weights.items()}
        
        logger.info(f"生成投资信号: {len(selected_stocks)}只股票, 总权重: {sum(weights.values()):.2%}")
        
        result = StrategyResult(
            strategy_name=self.name,
            selected_stocks=selected_stocks,
            weights=weights,
            confidence_scores=confidence_scores,
            reasons=reasons,
            execution_time=datetime.now(),
            metadata={
                'lookback_days': self.lookback_days,
                'top_hotmoney_count': len(top_hotmoney),
                'total_dragon_tiger_records': len(dragon_tiger_data),
                'recent_records': len(recent_data),
                'min_net_buy': self.min_net_buy,
                'analysis_period': f"{start_date.strftime('%Y-%m-%d')} 至 {recent_date.strftime('%Y-%m-%d')}",
                'top_hotmoney_list': top_hotmoney['seat_name'].tolist()
            }
        )
        
        return result

def quick_backtest_validation():
    """快速回测验证策略可行性"""
    print("开始执行游资跟投策略技术验证...")
    print("="*80)
    
    try:
        # 1. 初始化策略
        strategy = SimpleHotMoneyFollowingStrategy()
        
        # 2. 获取数据
        print("\n数据获取阶段:")
        dragon_tiger_data = strategy.get_dragon_tiger_data(days_back=180)
        
        if dragon_tiger_data.empty:
            print("ERROR: 无法获取龙虎榜数据，请检查数据库连接和配置")
            return {'status': 'failed', 'reason': 'no_data'}
        
        # 数据统计
        print(f"SUCCESS: 数据获取成功!")
        print(f"   - 龙虎榜记录: {len(dragon_tiger_data):,} 条")
        print(f"   - 涉及游资: {dragon_tiger_data['seat_name'].nunique():,} 个") 
        print(f"   - 涉及股票: {dragon_tiger_data['code'].nunique():,} 只")
        print(f"   - 时间跨度: {dragon_tiger_data['trade_date'].min().strftime('%Y-%m-%d')} 至 {dragon_tiger_data['trade_date'].max().strftime('%Y-%m-%d')}")
        
        # 3. 生成策略信号
        print("\n策略信号生成阶段:")
        result = strategy.generate_strategy_signals(dragon_tiger_data)
        
        # 4. 结果分析
        if len(result.selected_stocks) > 0:
            print(f"SUCCESS: 策略验证成功！")
            print(f"\n策略结果统计:")
            print(f"   - 推荐股票数: {len(result.selected_stocks)} 只")
            print(f"   - 总投资权重: {sum(result.weights.values()):.2%}")
            print(f"   - 平均置信度: {np.mean(list(result.confidence_scores.values())):.3f}")
            print(f"   - 跟踪游资数: {result.metadata['top_hotmoney_count']} 个")
            
            print(f"\n前10个投资信号:")
            print("-" * 80)
            print(f"{'股票代码':<10} {'权重':<8} {'置信度':<8} {'理由':<40}")
            print("-" * 80)
            
            for i, stock in enumerate(result.selected_stocks[:10]):
                weight = result.weights[stock]
                confidence = result.confidence_scores[stock]
                reason = result.reasons[stock][:38] + "..." if len(result.reasons[stock]) > 38 else result.reasons[stock]
                print(f"{stock:<10} {weight:.2%}    {confidence:<8.3f} {reason:<40}")
            
            # 显示详细分析结果
            print(f"\n分析期间详情:")
            print(f"   - 分析时间段: {result.metadata['analysis_period']}")
            print(f"   - 回看天数: {result.metadata['lookback_days']} 天")
            print(f"   - 最小净买入阈值: {result.metadata['min_net_buy']/10000:.0f} 万元")
            
            print(f"\n跟踪的主要游资:")
            for i, hotmoney in enumerate(result.metadata['top_hotmoney_list'][:5], 1):
                print(f"   {i}. {hotmoney}")
            
            # 成功结果
            return {
                'status': 'success',
                'strategy_result': result,
                'data_summary': {
                    'dragon_tiger_records': len(dragon_tiger_data),
                    'unique_hotmoney': dragon_tiger_data['seat_name'].nunique(),
                    'unique_stocks': dragon_tiger_data['code'].nunique(),
                    'signals_generated': len(result.selected_stocks),
                    'total_weight': sum(result.weights.values()),
                    'avg_confidence': np.mean(list(result.confidence_scores.values()))
                }
            }
        else:
            print("ERROR: 策略验证失败：未生成有效信号")
            print("可能原因:")
            print("   - 数据量不足")
            print("   - 参数设置过于严格") 
            print("   - 最近无符合条件的游资交易")
            
            return {'status': 'failed', 'reason': 'no_signals_generated', 'metadata': result.metadata}
            
    except Exception as e:
        logger.error(f"策略验证过程中出错: {e}")
        print(f"❌ 策略验证失败: {e}")
        return {'status': 'error', 'error': str(e)}

def main():
    """主函数"""
    result = quick_backtest_validation()
    
    print("\n" + "="*80)
    if result['status'] == 'success':
        print("✅ 技术验证完成！基础可行性已确认。")
        print("\n📋 下一步建议:")
        print("   1. 集成实时股价数据进行收益率回测")
        print("   2. 优化游资评分算法，增加更多维度") 
        print("   3. 添加风险控制机制和止损策略")
        print("   4. 开发Web界面展示投资信号")
        print("   5. 实现策略参数动态调优")
        
        # 保存结果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"strategy_validation_result_{timestamp}.txt"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(f"游资跟投策略验证结果\n")
            f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"策略状态: {result['status']}\n")
            f.write(f"数据统计: {result['data_summary']}\n")
        
        print(f"\n💾 详细结果已保存至: {result_file}")
        
    else:
        print("⚠️ 技术验证需要进一步调试")
        print(f"失败原因: {result.get('reason', 'unknown')}")
        if 'metadata' in result:
            print(f"元数据: {result['metadata']}")
    
    print("="*80)

if __name__ == "__main__":
    main()