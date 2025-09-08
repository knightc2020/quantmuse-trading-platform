#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统状态检查工具
检查数据库连接、API状态、数据完整性等
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from data_service.data_sync import get_data_synchronizer
from data_service.tonghuashun_client import get_tonghuashun_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemStatusChecker:
    """系统状态检查器"""
    
    def __init__(self):
        """初始化检查器"""
        self.data_sync = get_data_synchronizer()
        self.ths_client = get_tonghuashun_client()
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """检查环境变量配置"""
        required_vars = [
            'THS_USER_ID',
            'THS_PASSWORD', 
            'SUPABASE_URL',
            'SUPABASE_KEY'
        ]
        
        status = {
            'all_configured': True,
            'missing_vars': [],
            'configured_vars': []
        }
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                status['configured_vars'].append(var)
            else:
                status['missing_vars'].append(var)
                status['all_configured'] = False
        
        return status
    
    def check_database_connection(self) -> Dict[str, Any]:
        """检查数据库连接状态"""
        status = {
            'connected': False,
            'tables_accessible': {},
            'error': None
        }
        
        try:
            # 检查基本连接
            connected = self.data_sync.supabase_client.is_connected()
            status['connected'] = connected
            
            if connected:
                # 检查各表访问状态
                tables_to_check = ['seat_daily', 'money_flow', 'inst_flow', 'trade_flow']
                
                for table in tables_to_check:
                    try:
                        result = self.data_sync.supabase_client.client.table(table)\
                            .select('*')\
                            .limit(1)\
                            .execute()
                        
                        status['tables_accessible'][table] = {
                            'accessible': True,
                            'has_data': len(result.data) > 0
                        }
                        
                    except Exception as e:
                        status['tables_accessible'][table] = {
                            'accessible': False,
                            'error': str(e)[:100]
                        }
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def check_tonghuashun_connection(self) -> Dict[str, Any]:
        """检查同花顺API连接状态"""
        status = {
            'logged_in': False,
            'api_functional': False,
            'error': None
        }
        
        try:
            # 检查登录状态
            status['logged_in'] = self.ths_client.is_logged_in
            
            if status['logged_in']:
                # 简单API功能测试
                try:
                    # 尝试获取股票列表（限制数量避免过度调用）
                    stock_codes = self.ths_client.get_stock_list('sh')  # 只获取上海股票
                    if stock_codes and len(stock_codes) > 0:
                        status['api_functional'] = True
                        status['test_result'] = f"成功获取{len(stock_codes)}只股票代码"
                    else:
                        status['api_functional'] = False
                        status['test_result'] = "股票列表为空"
                        
                except Exception as e:
                    status['api_functional'] = False
                    status['test_result'] = f"API测试失败: {str(e)[:100]}"
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def check_data_completeness(self, days: int = 7) -> Dict[str, Any]:
        """检查最近几天的数据完整性"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        status = {
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'trading_days_checked': 0,
            'complete_days': 0,
            'incomplete_days': [],
            'table_stats': {}
        }
        
        try:
            tables_to_check = ['seat_daily', 'trade_flow', 'money_flow', 'inst_flow']
            
            # 检查每个工作日的数据
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:  # 工作日
                    date_str = current_date.strftime('%Y-%m-%d')
                    status['trading_days_checked'] += 1
                    
                    day_complete = True
                    day_details = {'date': date_str, 'missing_tables': []}
                    
                    for table in tables_to_check:
                        try:
                            result = self.data_sync.supabase_client.client.table(table)\
                                .select('*', count='exact')\
                                .eq('trade_date', date_str)\
                                .execute()
                            
                            count = result.count if result.count else 0
                            
                            if table not in status['table_stats']:
                                status['table_stats'][table] = {'total_records': 0, 'days_with_data': 0}
                            
                            status['table_stats'][table]['total_records'] += count
                            
                            if count > 0:
                                status['table_stats'][table]['days_with_data'] += 1
                            else:
                                day_complete = False
                                day_details['missing_tables'].append(table)
                                
                        except Exception as e:
                            day_complete = False
                            day_details['missing_tables'].append(f"{table}(error)")
                    
                    if day_complete:
                        status['complete_days'] += 1
                    else:
                        status['incomplete_days'].append(day_details)
                
                current_date += timedelta(days=1)
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def get_system_summary(self) -> Dict[str, Any]:
        """获取系统状态综合报告"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'environment': None,
            'database': None,
            'tonghuashun': None,
            'data_completeness': None,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # 检查环境变量
            summary['environment'] = self.check_environment_variables()
            if not summary['environment']['all_configured']:
                summary['issues'].append(f"缺少环境变量: {summary['environment']['missing_vars']}")
                summary['recommendations'].append("请设置缺失的环境变量")
            
            # 检查数据库
            summary['database'] = self.check_database_connection()
            if not summary['database']['connected']:
                summary['issues'].append("数据库连接失败")
                summary['recommendations'].append("检查Supabase配置和网络连接")
            
            # 检查同花顺API
            summary['tonghuashun'] = self.check_tonghuashun_connection()
            if not summary['tonghuashun']['logged_in']:
                summary['issues'].append("同花顺API未登录")
                summary['recommendations'].append("检查同花顺用户名密码，确保iFinD终端已启动")
            elif not summary['tonghuashun']['api_functional']:
                summary['issues'].append("同花顺API功能测试失败")
                summary['recommendations'].append("检查API权限和网络连接")
            
            # 检查数据完整性
            summary['data_completeness'] = self.check_data_completeness(7)
            completeness_rate = 0
            if summary['data_completeness']['trading_days_checked'] > 0:
                completeness_rate = summary['data_completeness']['complete_days'] / summary['data_completeness']['trading_days_checked']
            
            if completeness_rate < 0.8:  # 完整性低于80%
                summary['issues'].append(f"数据完整性较低: {completeness_rate:.1%}")
                summary['recommendations'].append("建议运行历史数据同步补齐缺失数据")
            
            # 确定总体状态
            if len(summary['issues']) == 0:
                summary['overall_status'] = 'healthy'
            elif any('连接' in issue or '登录' in issue for issue in summary['issues']):
                summary['overall_status'] = 'critical'
            else:
                summary['overall_status'] = 'warning'
                
        except Exception as e:
            summary['overall_status'] = 'error'
            summary['error'] = str(e)
        
        return summary
    
    def print_status_report(self):
        """打印格式化的状态报告"""
        summary = self.get_system_summary()
        
        print("="*70)
        print("               QuantMuse 系统状态报告")
        print("="*70)
        print(f"检查时间: {summary['timestamp'][:19]}")
        
        # 总体状态
        status_symbols = {
            'healthy': '✓ 正常',
            'warning': '⚠ 警告', 
            'critical': '✗ 严重',
            'error': '✗ 错误',
            'unknown': '? 未知'
        }
        
        status_text = status_symbols.get(summary['overall_status'], summary['overall_status'])
        print(f"总体状态: {status_text}")
        print()
        
        # 环境变量检查
        env = summary.get('environment', {})
        print("环境变量配置:")
        if env.get('all_configured'):
            print("  ✓ 所有必需的环境变量已配置")
        else:
            print(f"  ✗ 缺少环境变量: {', '.join(env.get('missing_vars', []))}")
        print()
        
        # 数据库连接
        db = summary.get('database', {})
        print("数据库连接:")
        if db.get('connected'):
            print("  ✓ Supabase 连接正常")
            
            tables = db.get('tables_accessible', {})
            for table, info in tables.items():
                if info['accessible']:
                    data_status = "有数据" if info['has_data'] else "无数据"
                    print(f"    ✓ {table}: 可访问 ({data_status})")
                else:
                    print(f"    ✗ {table}: 访问失败")
        else:
            print("  ✗ 数据库连接失败")
            if db.get('error'):
                print(f"    错误: {db['error'][:100]}")
        print()
        
        # 同花顺API
        ths = summary.get('tonghuashun', {})
        print("同花顺 API:")
        if ths.get('logged_in'):
            print("  ✓ iFinD 登录成功")
            if ths.get('api_functional'):
                print("  ✓ API 功能正常")
                print(f"    测试结果: {ths.get('test_result', 'N/A')}")
            else:
                print("  ✗ API 功能测试失败")
                print(f"    测试结果: {ths.get('test_result', 'N/A')}")
        else:
            print("  ✗ iFinD 未登录或连接失败")
        print()
        
        # 数据完整性
        data = summary.get('data_completeness', {})
        print("数据完整性 (近7天):")
        if 'error' not in data:
            complete_rate = data['complete_days'] / max(data['trading_days_checked'], 1)
            print(f"  检查了 {data['trading_days_checked']} 个交易日")
            print(f"  完整天数: {data['complete_days']} ({complete_rate:.1%})")
            
            if data['incomplete_days']:
                print(f"  不完整天数: {len(data['incomplete_days'])}")
                for day in data['incomplete_days'][:3]:  # 只显示前3天
                    missing = ', '.join(day['missing_tables'])
                    print(f"    {day['date']}: 缺少 {missing}")
                
                if len(data['incomplete_days']) > 3:
                    print(f"    ... 还有 {len(data['incomplete_days']) - 3} 天")
            
            print("  各表统计:")
            for table, stats in data.get('table_stats', {}).items():
                coverage = stats['days_with_data'] / max(data['trading_days_checked'], 1)
                print(f"    {table}: {stats['total_records']} 条记录, {coverage:.1%} 覆盖率")
        else:
            print(f"  ✗ 数据完整性检查失败: {data.get('error', 'Unknown error')}")
        print()
        
        # 问题和建议
        if summary['issues']:
            print("发现的问题:")
            for i, issue in enumerate(summary['issues'], 1):
                print(f"  {i}. {issue}")
            print()
        
        if summary['recommendations']:
            print("建议操作:")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"  {i}. {rec}")
            print()
        
        print("="*70)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='系统状态检查工具')
    parser.add_argument('--format', choices=['report', 'json'], default='report',
                       help='输出格式: report(报告格式), json(JSON格式)')
    
    args = parser.parse_args()
    
    checker = SystemStatusChecker()
    
    try:
        if args.format == 'json':
            import json
            summary = checker.get_system_summary()
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            checker.print_status_report()
        
        return 0
        
    except Exception as e:
        logger.error(f"状态检查失败: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)