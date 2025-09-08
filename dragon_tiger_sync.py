#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专用龙虎榜数据同步脚本
获取席位数据、交易流向数据，支持历史回补
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from data_service.data_sync import get_data_synchronizer
from data_service.tonghuashun_client import get_tonghuashun_client

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dragon_tiger_sync.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class DragonTigerSyncer:
    """龙虎榜数据同步器"""
    
    def __init__(self):
        """初始化同步器"""
        self.data_sync = get_data_synchronizer()
        self.ths_client = get_tonghuashun_client()
        
    def get_latest_trading_date(self) -> str:
        """获取最新交易日期"""
        today = datetime.now()
        
        # 如果是周末，获取上个工作日
        if today.weekday() == 5:  # 周六
            trading_date = today - timedelta(days=1)
        elif today.weekday() == 6:  # 周日  
            trading_date = today - timedelta(days=2)
        else:
            # 工作日，如果当前时间在16点之前，使用昨日数据
            if today.hour < 16:
                trading_date = today - timedelta(days=1)
                # 如果昨日是周末，继续回退
                while trading_date.weekday() >= 5:
                    trading_date = trading_date - timedelta(days=1)
            else:
                trading_date = today
                
        return trading_date.strftime('%Y-%m-%d')
    
    def check_dragon_tiger_data(self, target_date: str) -> Dict[str, Any]:
        """检查指定日期的龙虎榜数据状态"""
        status = {
            'target_date': target_date,
            'seat_daily_count': 0,
            'trade_flow_count': 0,
            'has_data': False
        }
        
        try:
            # 检查席位数据
            seat_result = self.data_sync.supabase_client.client.table('seat_daily')\
                .select('*', count='exact')\
                .eq('trade_date', target_date)\
                .execute()
            status['seat_daily_count'] = seat_result.count
            
            # 检查交易流向数据
            flow_result = self.data_sync.supabase_client.client.table('trade_flow')\
                .select('*', count='exact')\
                .eq('trade_date', target_date)\
                .execute()
            status['trade_flow_count'] = flow_result.count
            
            status['has_data'] = seat_result.count > 0 or flow_result.count > 0
            
        except Exception as e:
            logger.error(f"检查龙虎榜数据状态失败: {e}")
            status['error'] = str(e)
            
        return status
    
    def sync_dragon_tiger_for_date(self, date_str: str, force: bool = False) -> bool:
        """同步指定日期的龙虎榜数据"""
        logger.info(f"开始同步龙虎榜数据: {date_str}")
        
        # 如果不是强制模式，先检查是否已有数据
        if not force:
            status = self.check_dragon_tiger_data(date_str)
            
            if status['has_data']:
                logger.info(f"日期 {date_str} 的龙虎榜数据已存在 "
                           f"(席位: {status['seat_daily_count']}, 流向: {status['trade_flow_count']})，跳过同步")
                return True
        
        try:
            # 执行同步
            success = self.data_sync.sync_dragon_tiger_data(date_str, date_str)
            
            if success:
                # 验证数据
                status = self.check_dragon_tiger_data(date_str)
                logger.info(f"龙虎榜数据同步成功: {date_str}")
                logger.info(f"  席位数据: {status['seat_daily_count']} 条")
                logger.info(f"  交易流向: {status['trade_flow_count']} 条")
            else:
                logger.error(f"龙虎榜数据同步失败: {date_str}")
            
            return success
            
        except Exception as e:
            logger.error(f"龙虎榜数据同步异常: {e}")
            return False
    
    def analyze_dragon_tiger_trends(self, date_range: int = 30) -> Dict[str, Any]:
        """分析近期龙虎榜数据趋势"""
        end_date = self.get_latest_trading_date()
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=date_range)).strftime('%Y-%m-%d')
        
        logger.info(f"分析龙虎榜数据趋势: {start_date} 到 {end_date}")
        
        try:
            # 获取席位数据统计
            seat_result = self.data_sync.supabase_client.client.table('seat_daily')\
                .select('trade_date', count='exact')\
                .gte('trade_date', start_date)\
                .lte('trade_date', end_date)\
                .execute()
            
            # 获取交易流向统计  
            flow_result = self.data_sync.supabase_client.client.table('trade_flow')\
                .select('trade_date', count='exact')\
                .gte('trade_date', start_date)\
                .lte('trade_date', end_date)\
                .execute()
            
            # 按日期分组统计
            seat_data = pd.DataFrame(seat_result.data) if seat_result.data else pd.DataFrame()
            flow_data = pd.DataFrame(flow_result.data) if flow_result.data else pd.DataFrame()
            
            daily_stats = {}
            
            if not seat_data.empty:
                seat_counts = seat_data['trade_date'].value_counts().to_dict()
                for date, count in seat_counts.items():
                    if date not in daily_stats:
                        daily_stats[date] = {'seat_count': 0, 'flow_count': 0}
                    daily_stats[date]['seat_count'] = count
            
            if not flow_data.empty:
                flow_counts = flow_data['trade_date'].value_counts().to_dict()
                for date, count in flow_counts.items():
                    if date not in daily_stats:
                        daily_stats[date] = {'seat_count': 0, 'flow_count': 0}
                    daily_stats[date]['flow_count'] = count
            
            # 计算汇总统计
            total_seat_records = seat_result.count if seat_result.count else 0
            total_flow_records = flow_result.count if flow_result.count else 0
            
            active_days = len([d for d, stats in daily_stats.items() 
                              if stats['seat_count'] > 0 or stats['flow_count'] > 0])
            
            analysis = {
                'period': f"{start_date} 到 {end_date}",
                'total_seat_records': total_seat_records,
                'total_flow_records': total_flow_records,
                'active_days': active_days,
                'avg_daily_seat': total_seat_records / max(active_days, 1),
                'avg_daily_flow': total_flow_records / max(active_days, 1),
                'daily_breakdown': daily_stats
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"龙虎榜数据趋势分析失败: {e}")
            return {'error': str(e)}
    
    def sync_date_range(self, start_date: str, end_date: str = None, force: bool = False) -> Dict[str, Any]:
        """同步日期范围内的龙虎榜数据"""
        if not end_date:
            end_date = self.get_latest_trading_date()
            
        logger.info(f"开始同步龙虎榜历史数据: {start_date} 到 {end_date}")
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = {
            'total_days': 0,
            'success_days': 0,
            'failed_days': 0,
            'skipped_days': 0,
            'details': []
        }
        
        current_dt = start_dt
        while current_dt <= end_dt:
            # 只处理工作日
            if current_dt.weekday() < 5:  # 周一到周五
                date_str = current_dt.strftime('%Y-%m-%d')
                results['total_days'] += 1
                
                logger.info(f"处理日期: {date_str}")
                
                try:
                    # 检查现有数据
                    if not force:
                        status = self.check_dragon_tiger_data(date_str)
                        if status['has_data']:
                            logger.info(f"{date_str} 龙虎榜数据已存在，跳过")
                            results['skipped_days'] += 1
                            results['details'].append({
                                'date': date_str,
                                'skipped': True,
                                'existing_data': status
                            })
                            current_dt += timedelta(days=1)
                            continue
                    
                    # 执行同步
                    success = self.sync_dragon_tiger_for_date(date_str, force=True)
                    
                    if success:
                        results['success_days'] += 1
                        logger.info(f"✓ {date_str} 龙虎榜数据同步成功")
                    else:
                        results['failed_days'] += 1
                        logger.error(f"✗ {date_str} 龙虎榜数据同步失败")
                    
                    results['details'].append({
                        'date': date_str,
                        'success': success,
                        'skipped': False
                    })
                    
                except Exception as e:
                    logger.error(f"{date_str} 处理异常: {e}")
                    results['failed_days'] += 1
                    results['details'].append({
                        'date': date_str,
                        'success': False,
                        'error': str(e)
                    })
            
            current_dt += timedelta(days=1)
        
        # 输出汇总
        logger.info(f"龙虎榜历史数据同步完成:")
        logger.info(f"  总工作日数: {results['total_days']}")
        logger.info(f"  成功同步: {results['success_days']}")
        logger.info(f"  失败: {results['failed_days']}")
        logger.info(f"  跳过: {results['skipped_days']}")
        
        return results
    
    def run_daily_sync(self) -> bool:
        """运行每日龙虎榜同步任务"""
        logger.info("开始执行每日龙虎榜数据同步任务")
        
        try:
            # 检查连接状态
            if not self.data_sync.check_connection():
                logger.error("数据连接检查失败")
                return False
            
            # 获取最新交易日
            trading_date = self.get_latest_trading_date()
            logger.info(f"目标交易日期: {trading_date}")
            
            # 检查现有数据
            status = self.check_dragon_tiger_data(trading_date)
            
            if status['has_data']:
                logger.info(f"日期 {trading_date} 的龙虎榜数据已存在，无需同步")
                return True
            
            # 执行同步
            success = self.sync_dragon_tiger_for_date(trading_date)
            
            if success:
                logger.info("每日龙虎榜同步任务成功完成")
                
                # 显示统计信息
                final_status = self.check_dragon_tiger_data(trading_date)
                logger.info(f"最终数据统计:")
                logger.info(f"  席位数据: {final_status['seat_daily_count']} 条")
                logger.info(f"  交易流向: {final_status['trade_flow_count']} 条")
            else:
                logger.error("每日龙虎榜同步任务失败")
            
            return success
            
        except Exception as e:
            logger.error(f"每日龙虎榜同步任务异常: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='龙虎榜数据同步工具')
    parser.add_argument('command', 
                       choices=['daily', 'historical', 'check', 'analyze'],
                       help='执行命令: daily(每日同步), historical(历史同步), check(检查数据), analyze(趋势分析)')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--start-date', help='历史同步开始日期')
    parser.add_argument('--end-date', help='历史同步结束日期')
    parser.add_argument('--force', action='store_true', help='强制同步，忽略现有数据')
    parser.add_argument('--days', type=int, default=30, help='分析天数，默认30天')
    
    args = parser.parse_args()
    
    syncer = DragonTigerSyncer()
    
    try:
        if args.command == 'daily':
            if args.date:
                # 同步指定日期
                success = syncer.sync_dragon_tiger_for_date(args.date, args.force)
                logger.info(f"指定日期同步结果: {'成功' if success else '失败'}")
            else:
                # 运行每日同步
                success = syncer.run_daily_sync()
                
        elif args.command == 'historical':
            if not args.start_date:
                logger.error("历史同步需要指定 --start-date 参数")
                return 1
                
            results = syncer.sync_date_range(args.start_date, args.end_date, args.force)
            success = results['failed_days'] == 0
            
        elif args.command == 'check':
            date_to_check = args.date or syncer.get_latest_trading_date()
            status = syncer.check_dragon_tiger_data(date_to_check)
            
            print(f"\n=== 龙虎榜数据检查: {date_to_check} ===")
            print(f"席位数据: {status['seat_daily_count']} 条")
            print(f"交易流向: {status['trade_flow_count']} 条")
            print(f"有数据: {'是' if status['has_data'] else '否'}")
            
            success = True
            
        elif args.command == 'analyze':
            analysis = syncer.analyze_dragon_tiger_trends(args.days)
            
            if 'error' in analysis:
                logger.error(f"分析失败: {analysis['error']}")
                success = False
            else:
                print(f"\n=== 龙虎榜数据趋势分析 ===")
                print(f"分析期间: {analysis['period']}")
                print(f"总席位记录: {analysis['total_seat_records']:,}")
                print(f"总交易流向: {analysis['total_flow_records']:,}")
                print(f"活跃交易日: {analysis['active_days']}")
                print(f"日均席位记录: {analysis['avg_daily_seat']:.1f}")
                print(f"日均交易流向: {analysis['avg_daily_flow']:.1f}")
                success = True
                
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)