#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步主程序
启动定时任务或执行手动同步
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from data_service.scheduler import get_data_scheduler
from data_service.data_sync import get_data_synchronizer
from data_service.tonghuashun_client import get_tonghuashun_client

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_sync.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def check_environment():
    """检查运行环境"""
    logger.info("检查运行环境...")
    
    required_env_vars = [
        'THS_USER_ID',      # 同花顺用户ID
        'THS_PASSWORD',     # 同花顺密码
        'SUPABASE_URL',     # Supabase数据库URL
        'SUPABASE_KEY'      # Supabase API密钥
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"缺少必要的环境变量: {missing_vars}")
        logger.error("请在.env文件或系统环境变量中设置以下变量:")
        for var in missing_vars:
            logger.error(f"  {var}=your_value")
        return False
    
    # 检查同花顺客户端
    try:
        ths_client = get_tonghuashun_client()
        # 主动触发带重试的登录
        if not ths_client._ensure_login():
            logger.error("同花顺客户端登录失败，请检查用户名密码/权限/网络")
            return False
        logger.info("✓ 同花顺客户端连接成功")
    except Exception as e:
        logger.error(f"同花顺客户端连接失败: {e}")
        return False
    
    # 检查Supabase连接
    try:
        data_sync = get_data_synchronizer()
        if not data_sync.supabase_client.is_connected():
            logger.error("Supabase数据库连接失败，请检查URL和密钥")
            return False
        logger.info("✓ Supabase数据库连接成功")
    except Exception as e:
        logger.error(f"Supabase数据库连接失败: {e}")
        return False
    
    logger.info("✓ 运行环境检查通过")
    return True

def run_scheduler():
    """启动调度器"""
    if not check_environment():
        return False
    
    scheduler = get_data_scheduler()
    
    try:
        logger.info("启动数据同步调度器...")
        scheduler.start()
        
        # 显示调度信息
        next_run = scheduler.get_next_run_time()
        if next_run:
            logger.info(f"下次执行时间: {next_run}")
        
        logger.info("调度器已启动，按 Ctrl+C 停止")
        
        # 保持运行
        while True:
            import time
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
        scheduler.stop()
        logger.info("调度器已停止")
        return True
    except Exception as e:
        logger.error(f"调度器运行异常: {e}")
        return False

def run_manual_sync(sync_date: str = None, sync_type: str = 'all'):
    """运行手动同步"""
    if not check_environment():
        return False
    
    logger.info(f"开始手动数据同步: {sync_date or 'auto'}, 类型: {sync_type}")
    
    try:
        data_sync = get_data_synchronizer()
        
        # 确定同步日期
        if not sync_date:
            # 自动确定最新交易日
            today = datetime.now()
            if today.weekday() >= 5:  # 周末
                days_back = today.weekday() - 4  # 回到周五
                sync_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            else:
                sync_date = today.strftime('%Y-%m-%d')
        
        success_results = {}
        
        # 同步龙虎榜数据
        if sync_type in ['all', 'dragon_tiger']:
            logger.info("开始同步龙虎榜数据...")
            success = data_sync.sync_dragon_tiger_data(sync_date)
            success_results['dragon_tiger'] = success
            logger.info(f"龙虎榜数据同步{'成功' if success else '失败'}")
        
        # 同步日线数据
        if sync_type in ['all', 'daily_quotes']:
            logger.info("开始同步日线数据...")
            
            # 获取股票列表
            ths_client = get_tonghuashun_client()
            stock_codes = ths_client.get_stock_list('all')
            
            if stock_codes:
                success = data_sync.sync_daily_quotes(stock_codes, sync_date)
                success_results['daily_quotes'] = success
                logger.info(f"日线数据同步{'成功' if success else '失败'}，涉及{len(stock_codes)}只股票")
            else:
                logger.error("获取股票列表失败，跳过日线数据同步")
                success_results['daily_quotes'] = False
        
        # 输出结果摘要
        total_success = all(success_results.values()) if success_results else False
        logger.info(f"手动同步完成: {'总体成功' if total_success else '存在失败'}")
        
        for sync_name, result in success_results.items():
            logger.info(f"  {sync_name}: {'✓' if result else '✗'}")
        
        # 显示数据库状态
        status = data_sync.get_sync_status()
        logger.info("当前数据库状态:")
        for table_name, stats in status.get('table_stats', {}).items():
            if stats:
                logger.info(f"  {table_name}: {stats.get('总记录数', 0)}条记录, "
                           f"最新日期: {stats.get('最新日期', 'N/A')}")
        
        return total_success
        
    except Exception as e:
        logger.error(f"手动同步失败: {e}")
        return False

def show_status():
    """显示当前状态"""
    if not check_environment():
        return
    
    data_sync = get_data_synchronizer()
    status = data_sync.get_sync_status()
    
    print("\n=== 数据同步状态报告 ===")
    print(f"报告时间: {status['timestamp']}")
    
    print("\n连接状态:")
    connections = status['connections']
    print(f"  Supabase: {'✓' if connections['supabase'] else '✗'}")
    print(f"  同花顺:   {'✓' if connections['tonghuashun'] else '✗'}")
    
    print("\n最后同步日期:")
    for table_type, last_date in status['last_sync_dates'].items():
        print(f"  {table_type}: {last_date or '无数据'}")
    
    print("\n数据表统计:")
    for table_name, stats in status.get('table_stats', {}).items():
        if stats:
            print(f"  {table_name}:")
            print(f"    总记录数: {stats.get('总记录数', 0):,}")
            print(f"    涉及股票: {stats.get('涉及股票数', 0):,}")
            print(f"    日期范围: {stats.get('最早日期', 'N/A')} ~ {stats.get('最新日期', 'N/A')}")
    
    # 显示调度器状态
    scheduler = get_data_scheduler()
    next_run = scheduler.get_next_run_time()
    if next_run:
        print(f"\n下次自动同步: {next_run}")
    
    print("\n" + "="*50)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据同步工具')
    parser.add_argument('command', choices=['scheduler', 'sync', 'status'],
                       help='执行命令: scheduler(启动调度器), sync(手动同步), status(显示状态)')
    parser.add_argument('--date', help='同步日期 (YYYY-MM-DD)')
    parser.add_argument('--type', choices=['all', 'dragon_tiger', 'daily_quotes'], 
                       default='all', help='同步类型')
    
    args = parser.parse_args()
    
    if args.command == 'scheduler':
        success = run_scheduler()
    elif args.command == 'sync':
        success = run_manual_sync(args.date, args.type)
    elif args.command == 'status':
        show_status()
        success = True
    else:
        parser.print_help()
        success = False
    
    return 0 if success else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
