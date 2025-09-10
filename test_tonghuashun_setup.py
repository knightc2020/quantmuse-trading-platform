#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺数据获取模块测试脚本
验证基本功能和连接状态
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment():
    """测试环境配置"""
    print("=== 环境配置测试 ===")
    
    # 检查环境变量
    required_vars = ['THS_USER_ID', 'THS_PASSWORD', 'SUPABASE_URL', 'SUPABASE_KEY']
    for var in required_vars:
        value = os.getenv(var)
        status = "✓" if value else "✗"
        display_value = "***" if value and 'PASSWORD' in var or 'KEY' in var else value
        print(f"{status} {var}: {display_value or '未设置'}")
    
    print()

def test_supabase_connection():
    """测试Supabase连接"""
    print("=== Supabase连接测试 ===")
    
    try:
        from data_service.supabase_client import SupabaseDataClient
        
        client = SupabaseDataClient()
        
        if client.is_connected():
            print("✓ Supabase客户端初始化成功")
            
            # 测试连接
            if client.test_connection():
                print("✓ 数据库连接测试通过")
                
                # 获取数据概要
                summary = client.get_dragon_tiger_summary(days=30)
                if summary:
                    print(f"✓ 数据查询测试通过")
                    print(f"  - 最近30天记录数: {summary.get('总记录数', 0)}")
                    print(f"  - 涉及股票数: {summary.get('涉及股票数', 0)}")
                    print(f"  - 最新日期: {summary.get('最新日期', 'N/A')}")
                else:
                    print("⚠ 数据查询无结果")
            else:
                print("✗ 数据库连接测试失败")
        else:
            print("✗ Supabase客户端初始化失败")
            
    except Exception as e:
        print(f"✗ Supabase测试异常: {e}")
    
    print()

def test_tonghuashun_connection():
    """测试同花顺连接"""
    print("=== 同花顺连接测试 ===")
    
    try:
        # 首先检查是否有iFinD包
        try:
            import iFinDPy as THS
            print("✓ iFinDPy包导入成功")
        except ImportError:
            print("✗ iFinDPy包未安装")
            print("  请安装同花顺iFinD终端并配置Python环境")
            return
        
        from data_service.tonghuashun_client import TonghuasunDataClient
        
        client = TonghuasunDataClient()
        
        if client.is_logged_in:
            print("✓ 同花顺登录成功")
            
            # 测试获取股票列表（少量数据）
            try:
                stock_codes = client.get_stock_list('sh')  # 仅上交所股票
                if stock_codes and len(stock_codes) > 0:
                    print(f"✓ 股票列表获取成功，上交所股票数: {len(stock_codes)}")
                else:
                    print("⚠ 股票列表为空")
            except Exception as e:
                print(f"⚠ 股票列表获取异常: {e}")
            
            # 测试获取龙虎榜数据（最近一天）
            try:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                dragon_data = client.get_dragon_tiger_data(yesterday)
                if dragon_data is not None and len(dragon_data) > 0:
                    print(f"✓ 龙虎榜数据获取成功，{yesterday}: {len(dragon_data)}条记录")
                else:
                    print(f"⚠ {yesterday}无龙虎榜数据")
            except Exception as e:
                print(f"⚠ 龙虎榜数据获取异常: {e}")
                
        else:
            print("✗ 同花顺登录失败")
            print("  请检查THS_USER_ID和THS_PASSWORD环境变量")
            
    except Exception as e:
        print(f"✗ 同花顺测试异常: {e}")
    
    print()

def test_data_sync():
    """测试数据同步功能"""
    print("=== 数据同步功能测试 ===")
    
    try:
        from data_service.data_sync import DataSynchronizer
        
        sync = DataSynchronizer()
        
        # 检查连接状态
        if sync.check_connection():
            print("✓ 数据同步器初始化成功")
            
            # 获取同步状态
            status = sync.get_sync_status()
            print("✓ 同步状态获取成功:")
            
            for table_type, last_date in status['last_sync_dates'].items():
                print(f"  - {table_type}: {last_date or '无数据'}")
            
            print("⚠ 实际数据同步测试跳过（避免大量API调用）")
            
        else:
            print("✗ 数据同步器连接检查失败")
            
    except Exception as e:
        print(f"✗ 数据同步测试异常: {e}")
    
    print()

def test_scheduler():
    """测试调度器功能"""
    print("=== 调度器功能测试 ===")
    
    try:
        from data_service.scheduler import DataScheduler
        
        scheduler = DataScheduler()
        print("✓ 调度器初始化成功")
        
        # 检查配置
        print(f"  - 同步时间: {scheduler.config['daily_sync_time']}")
        print(f"  - 周末同步: {scheduler.config['weekend_sync']}")
        print(f"  - 重试次数: {scheduler.config['retry_times']}")
        
        next_run = scheduler.get_next_run_time()
        if next_run:
            print(f"  - 下次运行: {next_run}")
        
        print("⚠ 实际调度启动测试跳过")
        
    except Exception as e:
        print(f"✗ 调度器测试异常: {e}")
    
    print()

def main():
    """主测试函数"""
    print("开始同花顺数据获取模块测试...")
    print("="*50)
    
    # 逐个测试各个模块
    test_environment()
    test_supabase_connection()
    test_tonghuashun_connection()
    test_data_sync()
    test_scheduler()
    
    print("="*50)
    print("测试完成！")
    print("\n使用说明:")
    print("1. 启动调度器: python run_data_sync.py scheduler")
    print("2. 手动同步: python run_data_sync.py sync --date 2025-09-08")
    print("3. 查看状态: python run_data_sync.py status")

if __name__ == '__main__':
    main()