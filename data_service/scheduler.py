#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器
每天晚上8:00自动下载交易数据
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import threading
import json
import os

from .data_sync import DataSynchronizer
from .tonghuashun_client import TonghuasunDataClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataScheduler:
    """数据调度器"""
    
    def __init__(self, config_file: str = None):
        """初始化调度器"""
        self.config_file = config_file or 'data_sync_config.json'
        self.config = self._load_config()
        self.data_sync = DataSynchronizer()
        self.is_running = False
        self.scheduler_thread = None
        
        # 设置调度任务
        self._setup_schedule()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'daily_sync_time': '20:00',  # 每天8点执行
            'weekend_sync': False,       # 是否在周末执行
            'retry_times': 3,           # 失败重试次数
            'retry_interval': 300,      # 重试间隔(秒)
            'batch_size': 50,           # 股票批处理大小
            'sync_days_back': 5,        # 向前同步天数(防止遗漏)
            'enable_dragon_tiger': True, # 是否同步龙虎榜
            'enable_daily_quotes': True, # 是否同步日线
            'log_level': 'INFO',
            'notification': {
                'enable': False,
                'webhook_url': '',
                'email': ''
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"配置文件加载成功: {self.config_file}")
            else:
                # 创建默认配置文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                    logger.info(f"创建默认配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"配置文件处理失败: {e}")
        
        return default_config
    
    def _setup_schedule(self):
        """设置调度任务"""
        sync_time = self.config['daily_sync_time']
        
        if self.config['weekend_sync']:
            # 每天执行
            schedule.every().day.at(sync_time).do(self._daily_sync_job)
            logger.info(f"已设置每日{sync_time}数据同步任务(包含周末)")
        else:
            # 仅工作日执行
            schedule.every().monday.at(sync_time).do(self._daily_sync_job)
            schedule.every().tuesday.at(sync_time).do(self._daily_sync_job)
            schedule.every().wednesday.at(sync_time).do(self._daily_sync_job)
            schedule.every().thursday.at(sync_time).do(self._daily_sync_job)
            schedule.every().friday.at(sync_time).do(self._daily_sync_job)
            logger.info(f"已设置工作日{sync_time}数据同步任务")
        
        # 添加手动触发的立即同步任务
        # schedule.every(10).seconds.do(self._health_check)  # 可选的健康检查
    
    def _daily_sync_job(self):
        """每日数据同步任务"""
        job_start_time = datetime.now()
        logger.info(f"开始执行每日数据同步任务: {job_start_time}")
        
        try:
            # 检查连接状态
            if not self.data_sync.check_connection():
                logger.error("数据连接检查失败，跳过本次同步")
                return
            
            # 计算同步日期范围
            sync_date = self._get_sync_date()
            sync_dates = self._get_sync_date_range(sync_date)
            
            success_results = {
                'dragon_tiger': False,
                'daily_quotes': False
            }
            
            # 同步龙虎榜数据
            if self.config['enable_dragon_tiger']:
                logger.info("开始同步龙虎榜数据")
                for date_str in sync_dates:
                    if self._sync_with_retry('dragon_tiger', date_str):
                        success_results['dragon_tiger'] = True
                        break
            
            # 同步日线数据
            if self.config['enable_daily_quotes']:
                logger.info("开始同步日线数据")
                stock_codes = self._get_stock_list()
                if stock_codes:
                    for date_str in sync_dates:
                        if self._sync_with_retry('daily_quotes', date_str, stock_codes):
                            success_results['daily_quotes'] = True
                            break
            
            # 记录任务结果
            job_end_time = datetime.now()
            duration = job_end_time - job_start_time
            
            result_summary = {
                'timestamp': job_end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'sync_dates': sync_dates,
                'results': success_results,
                'success': any(success_results.values())
            }
            
            self._log_job_result(result_summary)
            
            # 发送通知
            if self.config['notification']['enable']:
                self._send_notification(result_summary)
                
        except Exception as e:
            logger.error(f"每日同步任务执行异常: {e}")
            self._send_error_notification(str(e))
    
    def _get_sync_date(self) -> str:
        """获取需要同步的日期"""
        # 获取最新交易日
        today = datetime.now()
        
        # 如果是周末，获取上周五的数据
        if today.weekday() == 5:  # 周六
            sync_date = today - timedelta(days=1)
        elif today.weekday() == 6:  # 周日
            sync_date = today - timedelta(days=2)
        else:
            # 工作日，如果是周一，可能需要获取周五的数据
            if today.weekday() == 0 and today.hour < 20:  # 周一晚8点前
                sync_date = today - timedelta(days=3)  # 上周五
            else:
                sync_date = today
        
        return sync_date.strftime('%Y-%m-%d')
    
    def _get_sync_date_range(self, target_date: str) -> List[str]:
        """获取同步日期范围（包含回补）"""
        dates = []
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # 向前回补几天，防止遗漏
        for i in range(self.config['sync_days_back']):
            date_dt = target_dt - timedelta(days=i)
            # 跳过周末
            if date_dt.weekday() < 5:  # 0-4是周一到周五
                dates.append(date_dt.strftime('%Y-%m-%d'))
        
        return sorted(dates, reverse=True)  # 从最新日期开始
    
    def _get_stock_list(self) -> Optional[List[str]]:
        """获取需要同步的股票列表"""
        try:
            ths_client = TonghuasunDataClient()
            return ths_client.get_stock_list('all')
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return None
    
    def _sync_with_retry(self, 
                        sync_type: str, 
                        date_str: str, 
                        stock_codes: List[str] = None) -> bool:
        """带重试的数据同步"""
        retry_times = self.config['retry_times']
        retry_interval = self.config['retry_interval']
        
        for attempt in range(retry_times):
            try:
                if sync_type == 'dragon_tiger':
                    success = self.data_sync.sync_dragon_tiger_data(date_str, date_str)
                elif sync_type == 'daily_quotes' and stock_codes:
                    success = self.data_sync.sync_daily_quotes(stock_codes, date_str, date_str)
                else:
                    logger.warning(f"未知同步类型: {sync_type}")
                    return False
                
                if success:
                    logger.info(f"{sync_type}数据同步成功: {date_str}")
                    return True
                else:
                    logger.warning(f"{sync_type}数据同步失败: {date_str}，尝试{attempt + 1}/{retry_times}")
                    
            except Exception as e:
                logger.error(f"{sync_type}数据同步异常: {e}，尝试{attempt + 1}/{retry_times}")
            
            # 等待重试
            if attempt < retry_times - 1:
                time.sleep(retry_interval)
        
        logger.error(f"{sync_type}数据同步最终失败: {date_str}")
        return False
    
    def _log_job_result(self, result: Dict[str, Any]):
        """记录任务结果"""
        try:
            # 写入日志文件
            log_file = f"sync_log_{datetime.now().strftime('%Y%m')}.json"
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = []
            
            log_data.append(result)
            
            # 只保留最近100条记录
            if len(log_data) > 100:
                log_data = log_data[-100:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            # 控制台输出
            status = "✓" if result['success'] else "✗"
            logger.info(f"任务结果 {status}: 耗时{result['duration_seconds']:.1f}秒, "
                       f"龙虎榜{'✓' if result['results']['dragon_tiger'] else '✗'}, "
                       f"日线{'✓' if result['results']['daily_quotes'] else '✗'}")
            
        except Exception as e:
            logger.error(f"记录任务结果失败: {e}")
    
    def _send_notification(self, result: Dict[str, Any]):
        """发送通知"""
        # 这里可以集成邮件、钉钉、企业微信等通知方式
        pass
    
    def _send_error_notification(self, error_msg: str):
        """发送错误通知"""
        logger.error(f"同步任务出现错误，需要人工检查: {error_msg}")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.is_running = True
        
        def run_scheduler():
            logger.info("数据同步调度器已启动")
            while self.is_running:
                schedule.run_pending()
                time.sleep(30)  # 每30秒检查一次
            logger.info("数据同步调度器已停止")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"调度器启动成功，下次执行时间: {schedule.next_run()}")
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("调度器已停止")
    
    def run_manual_sync(self, sync_date: str = None) -> Dict[str, Any]:
        """手动触发数据同步"""
        if not sync_date:
            sync_date = self._get_sync_date()
        
        logger.info(f"手动触发数据同步: {sync_date}")
        
        # 暂时停止自动调度，避免冲突
        was_running = self.is_running
        if was_running:
            self.stop()
        
        try:
            # 执行同步
            self._daily_sync_job()
            
            # 获取同步状态
            status = self.data_sync.get_sync_status()
            
            return {
                'success': True,
                'sync_date': sync_date,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"手动同步失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 恢复自动调度
            if was_running:
                self.start()
    
    def get_next_run_time(self) -> Optional[str]:
        """获取下次执行时间"""
        next_run = schedule.next_run()
        return next_run.isoformat() if next_run else None
    
    def get_job_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取任务执行历史"""
        try:
            current_month = datetime.now().strftime('%Y%m')
            log_file = f"sync_log_{current_month}.json"
            
            if not os.path.exists(log_file):
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # 过滤最近N天的记录
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_logs = []
            for log_entry in log_data:
                log_time = datetime.fromisoformat(log_entry['timestamp'])
                if log_time >= cutoff_date:
                    recent_logs.append(log_entry)
            
            return sorted(recent_logs, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"获取任务历史失败: {e}")
            return []

# 全局调度器实例
_scheduler = None

def get_data_scheduler() -> DataScheduler:
    """获取数据调度器实例（单例模式）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DataScheduler()
    return _scheduler