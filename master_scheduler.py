#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主调度器 - 每晚8:00执行数据同步任务
统一管理日线数据和龙虎榜数据的自动下载
"""

import os
import sys
import logging
import schedule
import time
from datetime import datetime, timedelta
import threading
import json

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from daily_data_sync import DailyDataSyncer
from dragon_tiger_sync import DragonTigerSyncer

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('master_scheduler.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class MasterScheduler:
    """主调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.daily_syncer = DailyDataSyncer()
        self.dragon_syncer = DragonTigerSyncer()
        self.is_running = False
        self.scheduler_thread = None
        
        # 任务执行历史
        self.execution_log = []
        
    def log_execution(self, task_name: str, success: bool, duration: float, details: dict = None):
        """记录任务执行情况"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'task': task_name,
            'success': success,
            'duration_seconds': round(duration, 2),
            'details': details or {}
        }
        
        self.execution_log.append(log_entry)
        
        # 只保留最近100条记录
        if len(self.execution_log) > 100:
            self.execution_log = self.execution_log[-100:]
        
        # 保存到文件
        try:
            with open(f'scheduler_log_{datetime.now().strftime("%Y%m")}.json', 'w', encoding='utf-8') as f:
                json.dump(self.execution_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存执行日志失败: {e}")
    
    def daily_sync_job(self):
        """每日数据同步任务"""
        job_start_time = datetime.now()
        logger.info("="*60)
        logger.info(f"开始执行每日数据同步任务: {job_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        overall_success = True
        task_results = {}
        
        try:
            # 1. 同步龙虎榜数据
            logger.info("第1步: 同步龙虎榜数据")
            dragon_start = time.time()
            
            try:
                dragon_success = self.dragon_syncer.run_daily_sync()
                dragon_duration = time.time() - dragon_start
                
                task_results['dragon_tiger'] = {
                    'success': dragon_success,
                    'duration': dragon_duration
                }
                
                if dragon_success:
                    logger.info(f"✓ 龙虎榜数据同步成功 (耗时: {dragon_duration:.1f}秒)")
                else:
                    logger.error(f"✗ 龙虎榜数据同步失败 (耗时: {dragon_duration:.1f}秒)")
                    overall_success = False
                    
            except Exception as e:
                dragon_duration = time.time() - dragon_start
                logger.error(f"✗ 龙虎榜数据同步异常: {e} (耗时: {dragon_duration:.1f}秒)")
                task_results['dragon_tiger'] = {'success': False, 'duration': dragon_duration, 'error': str(e)}
                overall_success = False
            
            # 等待间隔，避免API请求过于密集
            time.sleep(10)
            
            # 2. 同步日线数据
            logger.info("第2步: 同步日线数据")
            daily_start = time.time()
            
            try:
                daily_success = self.daily_syncer.run_daily_sync()
                daily_duration = time.time() - daily_start
                
                task_results['daily_quotes'] = {
                    'success': daily_success,
                    'duration': daily_duration
                }
                
                if daily_success:
                    logger.info(f"✓ 日线数据同步成功 (耗时: {daily_duration:.1f}秒)")
                else:
                    logger.error(f"✗ 日线数据同步失败 (耗时: {daily_duration:.1f}秒)")
                    overall_success = False
                    
            except Exception as e:
                daily_duration = time.time() - daily_start
                logger.error(f"✗ 日线数据同步异常: {e} (耗时: {daily_duration:.1f}秒)")
                task_results['daily_quotes'] = {'success': False, 'duration': daily_duration, 'error': str(e)}
                overall_success = False
            
            # 3. 生成同步报告
            job_end_time = datetime.now()
            total_duration = (job_end_time - job_start_time).total_seconds()
            
            logger.info("="*60)
            logger.info("每日数据同步任务完成")
            logger.info(f"开始时间: {job_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"结束时间: {job_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"总耗时: {total_duration:.1f}秒")
            logger.info(f"总体状态: {'成功' if overall_success else '部分失败'}")
            
            for task_name, result in task_results.items():
                status = "✓" if result['success'] else "✗"
                logger.info(f"  {task_name}: {status} ({result['duration']:.1f}秒)")
            
            logger.info("="*60)
            
            # 记录执行历史
            self.log_execution(
                'daily_sync_job',
                overall_success,
                total_duration,
                task_results
            )
            
            # 如果有失败，可以在这里添加通知机制
            if not overall_success:
                self.send_failure_notification(task_results)
                
        except Exception as e:
            job_end_time = datetime.now()
            total_duration = (job_end_time - job_start_time).total_seconds()
            
            logger.error(f"每日数据同步任务发生严重异常: {e}")
            logger.error(f"任务异常终止，总耗时: {total_duration:.1f}秒")
            
            self.log_execution(
                'daily_sync_job',
                False,
                total_duration,
                {'error': str(e)}
            )
    
    def send_failure_notification(self, task_results: dict):
        """发送失败通知"""
        # 这里可以集成邮件、钉钉、企业微信等通知方式
        logger.warning("数据同步存在失败项目，需要人工检查:")
        for task_name, result in task_results.items():
            if not result['success']:
                error_msg = result.get('error', '未知错误')
                logger.warning(f"  {task_name}: {error_msg}")
    
    def health_check(self):
        """健康检查任务"""
        try:
            # 检查数据连接状态
            daily_connected = self.daily_syncer.data_sync.check_connection()
            dragon_connected = self.dragon_syncer.data_sync.check_connection()
            
            if daily_connected and dragon_connected:
                logger.debug("健康检查通过：所有连接正常")
            else:
                logger.warning(f"健康检查警告：连接状态异常 (日线:{daily_connected}, 龙虎榜:{dragon_connected})")
                
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
    
    def setup_schedule(self):
        """设置调度任务"""
        # 每天晚上8:00执行数据同步
        schedule.every().day.at("20:00").do(self.daily_sync_job)
        
        # 每小时执行健康检查（可选）
        schedule.every().hour.do(self.health_check)
        
        logger.info("调度任务设置完成:")
        logger.info("  每日数据同步: 20:00")
        logger.info("  健康检查: 每小时")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.setup_schedule()
        self.is_running = True
        
        def run_scheduler():
            logger.info("主调度器启动成功")
            logger.info(f"下次执行时间: {schedule.next_run()}")
            
            while self.is_running:
                schedule.run_pending()
                time.sleep(30)  # 每30秒检查一次
                
            logger.info("主调度器已停止")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("调度器已停止")
    
    def manual_sync(self, sync_type: str = 'all') -> bool:
        """手动触发同步任务"""
        logger.info(f"手动触发同步任务: {sync_type}")
        
        try:
            if sync_type == 'all':
                self.daily_sync_job()
                return True
            elif sync_type == 'dragon_tiger':
                success = self.dragon_syncer.run_daily_sync()
                logger.info(f"龙虎榜数据手动同步结果: {'成功' if success else '失败'}")
                return success
            elif sync_type == 'daily_quotes':
                success = self.daily_syncer.run_daily_sync()
                logger.info(f"日线数据手动同步结果: {'成功' if success else '失败'}")
                return success
            else:
                logger.error(f"未知同步类型: {sync_type}")
                return False
                
        except Exception as e:
            logger.error(f"手动同步失败: {e}")
            return False
    
    def get_execution_summary(self, days: int = 7) -> dict:
        """获取执行摘要"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        recent_executions = [
            log for log in self.execution_log
            if datetime.fromisoformat(log['timestamp']) >= cutoff_time
        ]
        
        if not recent_executions:
            return {'message': f'过去{days}天没有执行记录'}
        
        total_executions = len(recent_executions)
        successful_executions = len([log for log in recent_executions if log['success']])
        
        summary = {
            'period': f'过去{days}天',
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': f'{successful_executions/total_executions*100:.1f}%',
            'recent_executions': recent_executions[-5:]  # 最近5次执行
        }
        
        return summary

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='主数据调度器')
    parser.add_argument('command', 
                       choices=['start', 'manual', 'status'],
                       help='执行命令: start(启动调度器), manual(手动同步), status(查看状态)')
    parser.add_argument('--type', 
                       choices=['all', 'dragon_tiger', 'daily_quotes'], 
                       default='all',
                       help='手动同步类型')
    parser.add_argument('--days', type=int, default=7, help='状态查询天数')
    
    args = parser.parse_args()
    
    scheduler = MasterScheduler()
    
    try:
        if args.command == 'start':
            logger.info("启动主调度器...")
            scheduler.start()
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("收到停止信号")
                scheduler.stop()
                
        elif args.command == 'manual':
            logger.info(f"手动执行同步任务: {args.type}")
            success = scheduler.manual_sync(args.type)
            return 0 if success else 1
            
        elif args.command == 'status':
            summary = scheduler.get_execution_summary(args.days)
            
            print(f"\n=== 调度器执行状态 ({summary.get('period', 'N/A')}) ===")
            
            if 'message' in summary:
                print(summary['message'])
            else:
                print(f"总执行次数: {summary['total_executions']}")
                print(f"成功次数: {summary['successful_executions']}")
                print(f"成功率: {summary['success_rate']}")
                
                if summary['recent_executions']:
                    print("\n最近执行记录:")
                    for execution in summary['recent_executions']:
                        status = "✓" if execution['success'] else "✗"
                        timestamp = execution['timestamp'][:16]  # 只显示到分钟
                        print(f"  {timestamp} {status} {execution['task']} ({execution['duration_seconds']}秒)")
            
            return 0
            
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)