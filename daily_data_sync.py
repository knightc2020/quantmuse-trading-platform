#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专用日线数据同步脚本
每日晚上8点执行，下载最新交易日的全市场股票数据
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any
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
        logging.FileHandler('daily_sync.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class DailyDataSyncer:
    """每日数据同步器"""
    
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
            # 工作日，如果当前时间在20点之前，可能还没有今日数据
            if today.hour < 16:  # 下午4点前，使用昨日数据
                trading_date = today - timedelta(days=1)
                # 如果昨日是周末，继续回退
                while trading_date.weekday() >= 5:
                    trading_date = trading_date - timedelta(days=1)
            else:
                trading_date = today
                
        return trading_date.strftime('%Y-%m-%d')
    
    def check_data_gap(self, target_date: str) -> Dict[str, Any]:
        """检查指定日期的数据缺口"""
        gap_info = {
            'target_date': target_date,
            'daily_quotes_missing': False,
            'seat_daily_missing': False,
            'trade_flow_missing': False,
            'missing_count': 0
        }
        
        try:
            # 检查日线数据
            daily_result = self.data_sync.supabase_client.client.table('daily_quotes')\
                .select('*', count='exact')\
                .eq('trade_date', target_date)\
                .execute()
            
            if daily_result.count == 0:
                gap_info['daily_quotes_missing'] = True
                gap_info['missing_count'] += 1
                
            # 检查龙虎榜席位数据
            seat_result = self.data_sync.supabase_client.client.table('seat_daily')\
                .select('*', count='exact')\
                .eq('trade_date', target_date)\
                .execute()
                
            if seat_result.count == 0:
                gap_info['seat_daily_missing'] = True
                gap_info['missing_count'] += 1
                
            # 检查交易流向数据
            flow_result = self.data_sync.supabase_client.client.table('trade_flow')\
                .select('*', count='exact')\
                .eq('trade_date', target_date)\
                .execute()
                
            if flow_result.count == 0:
                gap_info['trade_flow_missing'] = True
                gap_info['missing_count'] += 1
                
        except Exception as e:
            logger.error(f"检查数据缺口失败: {e}")
            gap_info['error'] = str(e)
            
        return gap_info
    
    def sync_daily_quotes_data(self, date_str: str, force: bool = False) -> bool:
        """同步日线数据"""
        logger.info(f"开始同步日线数据: {date_str}")
        
        # 如果不是强制模式，先检查是否已有数据
        if not force:
            try:
                existing = self.data_sync.supabase_client.client.table('daily_quotes')\
                    .select('*', count='exact')\
                    .eq('trade_date', date_str)\
                    .execute()
                    
                if existing.count > 0:
                    logger.info(f"日期 {date_str} 的日线数据已存在 ({existing.count} 条)，跳过同步")
                    return True
                    
            except Exception as e:
                logger.warning(f"检查现有数据失败: {e}，继续同步")
        
        try:
            # 获取股票列表
            stock_codes = self.ths_client.get_stock_list('all')
            if not stock_codes:
                logger.error("获取股票列表失败")
                return False
                
            logger.info(f"准备同步 {len(stock_codes)} 只股票的日线数据")
            
            # 执行同步
            success = self.data_sync.sync_daily_quotes(stock_codes, date_str, date_str)
            
            if success:
                logger.info(f"日线数据同步成功: {date_str}")
                
                # 验证数据
                verify_result = self.data_sync.supabase_client.client.table('daily_quotes')\
                    .select('*', count='exact')\
                    .eq('trade_date', date_str)\
                    .execute()
                    
                logger.info(f"验证结果: 成功写入 {verify_result.count} 条日线数据")
                
            return success
            
        except Exception as e:
            logger.error(f"日线数据同步失败: {e}")
            return False
    
    def sync_historical_data(self, start_date: str, end_date: str = None) -> Dict[str, Any]:
        """同步历史数据段"""
        if not end_date:
            end_date = self.get_latest_trading_date()
            
        logger.info(f"开始同步历史数据: {start_date} 到 {end_date}")
        
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
            # 跳过周末
            if current_dt.weekday() < 5:  # 周一到周五
                date_str = current_dt.strftime('%Y-%m-%d')
                results['total_days'] += 1
                
                logger.info(f"处理日期: {date_str}")
                
                try:
                    # 检查数据缺口
                    gap_info = self.check_data_gap(date_str)
                    
                    if gap_info['missing_count'] == 0:
                        logger.info(f"{date_str} 数据完整，跳过")
                        results['skipped_days'] += 1
                    else:
                        # 同步缺失的数据
                        success = True
                        
                        if gap_info['daily_quotes_missing']:
                            success &= self.sync_daily_quotes_data(date_str, force=True)
                        
                        if gap_info['seat_daily_missing'] or gap_info['trade_flow_missing']:
                            success &= self.data_sync.sync_dragon_tiger_data(date_str, date_str)
                        
                        if success:
                            results['success_days'] += 1
                            logger.info(f"✓ {date_str} 数据同步成功")
                        else:
                            results['failed_days'] += 1
                            logger.error(f"✗ {date_str} 数据同步失败")
                        
                        results['details'].append({
                            'date': date_str,
                            'success': success,
                            'gap_info': gap_info
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
        logger.info(f"历史数据同步完成:")
        logger.info(f"  总工作日数: {results['total_days']}")
        logger.info(f"  成功同步: {results['success_days']}")
        logger.info(f"  失败: {results['failed_days']}")
        logger.info(f"  跳过: {results['skipped_days']}")
        
        return results
    
    def run_daily_sync(self) -> bool:
        """运行每日同步任务"""
        logger.info("开始执行每日数据同步任务")
        
        try:
            # 检查连接状态
            if not self.data_sync.check_connection():
                logger.error("数据连接检查失败")
                return False
            
            # 获取最新交易日
            trading_date = self.get_latest_trading_date()
            logger.info(f"目标交易日期: {trading_date}")
            
            # 检查数据缺口
            gap_info = self.check_data_gap(trading_date)
            
            if gap_info['missing_count'] == 0:
                logger.info(f"日期 {trading_date} 的数据已完整，无需同步")
                return True
            
            logger.info(f"检测到 {gap_info['missing_count']} 项数据缺失，开始同步...")
            
            success_results = []
            
            # 同步日线数据
            if gap_info['daily_quotes_missing']:
                success = self.sync_daily_quotes_data(trading_date)
                success_results.append(('daily_quotes', success))
            
            # 同步龙虎榜数据
            if gap_info['seat_daily_missing'] or gap_info['trade_flow_missing']:
                success = self.data_sync.sync_dragon_tiger_data(trading_date, trading_date)
                success_results.append(('dragon_tiger', success))
            
            # 汇总结果
            total_success = all(result[1] for result in success_results)
            
            logger.info(f"每日同步任务完成: {'总体成功' if total_success else '存在失败'}")
            for task_name, result in success_results:
                logger.info(f"  {task_name}: {'✓' if result else '✗'}")
            
            return total_success
            
        except Exception as e:
            logger.error(f"每日同步任务失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='日线数据同步工具')
    parser.add_argument('command', 
                       choices=['daily', 'historical', 'check-gap'],
                       help='执行命令: daily(每日同步), historical(历史同步), check-gap(检查缺口)')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--start-date', help='历史同步开始日期')
    parser.add_argument('--end-date', help='历史同步结束日期')
    parser.add_argument('--force', action='store_true', help='强制同步，忽略现有数据')
    
    args = parser.parse_args()
    
    syncer = DailyDataSyncer()
    
    try:
        if args.command == 'daily':
            if args.date:
                # 同步指定日期
                success = syncer.sync_daily_quotes_data(args.date, args.force)
                logger.info(f"指定日期同步结果: {'成功' if success else '失败'}")
            else:
                # 运行每日同步
                success = syncer.run_daily_sync()
                logger.info(f"每日同步结果: {'成功' if success else '失败'}")
                
        elif args.command == 'historical':
            if not args.start_date:
                logger.error("历史同步需要指定 --start-date 参数")
                return 1
                
            results = syncer.sync_historical_data(args.start_date, args.end_date)
            success = results['failed_days'] == 0
            
        elif args.command == 'check-gap':
            date_to_check = args.date or syncer.get_latest_trading_date()
            gap_info = syncer.check_data_gap(date_to_check)
            
            print(f"\n=== 数据缺口检查: {date_to_check} ===")
            print(f"日线数据缺失: {'是' if gap_info['daily_quotes_missing'] else '否'}")
            print(f"席位数据缺失: {'是' if gap_info['seat_daily_missing'] else '否'}")
            print(f"交易流向缺失: {'是' if gap_info['trade_flow_missing'] else '否'}")
            print(f"总缺失项数: {gap_info['missing_count']}")
            
            success = True
            
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)