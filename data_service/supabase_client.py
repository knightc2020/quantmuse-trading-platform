#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase数据库客户端
用于连接和操作龙虎榜等A股数据
"""

import os
import pandas as pd
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import streamlit as st
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseDataClient:
    """Supabase数据客户端"""
    
    def __init__(self):
        """初始化Supabase客户端"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Supabase连接"""
        try:
            # 优先从Streamlit secrets获取配置
            if hasattr(st, 'secrets') and 'supabase' in st.secrets:
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["key"]
            else:
                # 从环境变量获取配置
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                logger.warning("Supabase配置未找到，请设置环境变量或Streamlit secrets")
                return
            
            self.client: Client = create_client(url, key)
            logger.info("Supabase客户端初始化成功")
            
        except Exception as e:
            logger.error(f"Supabase客户端初始化失败: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """检查是否连接成功"""
        return self.client is not None
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        if not self.client:
            return False
        
        try:
            # 尝试执行一个简单查询，使用实际存在的表
            result = self.client.table('seat_daily').select('*').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    # 龙虎榜数据查询方法
    def get_dragon_tiger_data(self, 
                             start_date: str = None, 
                             end_date: str = None,
                             stock_code: str = None,
                             limit: int = 1000,
                             table_type: str = 'seat') -> Optional[pd.DataFrame]:
        """
        获取龙虎榜数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD) 
            stock_code: 股票代码
            limit: 返回记录数限制
            table_type: 数据类型 ('seat'游资席位, 'inst'机构席位, 'flow'交易流向)
        
        Returns:
            pandas.DataFrame or None
        """
        if not self.client:
            logger.error("Supabase客户端未初始化")
            return None
        
        try:
            # 根据类型选择不同的表
            table_map = {
                'seat': 'seat_daily',      # 游资席位数据
                'inst': 'inst_flow',       # 机构席位数据  
                'flow': 'trade_flow'       # 交易流向数据
            }
            
            table_name = table_map.get(table_type, 'seat_daily')
            query = self.client.table(table_name).select('*')
            
            # 添加日期过滤
            if start_date:
                query = query.gte('trade_date', start_date)
            if end_date:
                query = query.lte('trade_date', end_date)
            
            # 添加股票代码过滤
            if stock_code:
                query = query.eq('code', stock_code)
            
            # 限制返回数量并按日期降序排列
            query = query.limit(limit).order('trade_date', desc=True)
            
            result = query.execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                logger.info(f"获取{table_name}数据 {len(df)} 条")
                return df
            else:
                logger.warning(f"未找到匹配的{table_name}数据")
                return None
                
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return None
    
    def get_dragon_tiger_summary(self, days: int = 30, table_type: str = 'seat') -> Optional[Dict]:
        """
        获取龙虎榜数据概要统计
        
        Args:
            days: 统计最近几天的数据
            table_type: 数据类型 ('seat', 'inst', 'flow')
            
        Returns:
            dict: 包含统计信息的字典
        """
        # 先获取表中最新的日期
        try:
            table_map = {'seat': 'seat_daily', 'inst': 'inst_flow', 'flow': 'trade_flow'}
            table_name = table_map.get(table_type, 'seat_daily')
            
            latest_result = self.client.table(table_name).select('trade_date').order('trade_date', desc=True).limit(1).execute()
            
            if latest_result.data and latest_result.data[0]['trade_date']:
                # 使用数据库中的最新日期作为结束日期
                end_date = latest_result.data[0]['trade_date']
                # 向前推算指定天数作为开始日期
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                start_datetime = end_datetime - timedelta(days=days)
                start_date = start_datetime.strftime('%Y-%m-%d')
            else:
                # 回退到原来的逻辑
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
        except Exception:
            # 如果获取最新日期失败，使用默认逻辑
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = self.get_dragon_tiger_data(start_date=start_date, end_date=end_date, table_type=table_type)
        
        if df is None or df.empty:
            return None
        
        try:
            summary = {
                "总记录数": len(df),
                "涉及股票数": df['code'].nunique() if 'code' in df.columns else 0,
                "最新日期": df['trade_date'].max() if 'trade_date' in df.columns else None,
                "最早日期": df['trade_date'].min() if 'trade_date' in df.columns else None,
                "数据字段": list(df.columns),
                "数据类型": table_type,
            }
            
            # 根据表类型统计不同信息
            if table_type == 'seat' and 'seat_name' in df.columns:
                summary["游资席位数"] = df['seat_name'].nunique()
                summary["总买入金额"] = df['buy_amt'].sum() if 'buy_amt' in df.columns else 0
                summary["总卖出金额"] = df['sell_amt'].sum() if 'sell_amt' in df.columns else 0
            elif table_type == 'inst' and 'inst_name' in df.columns:
                summary["机构席位数"] = df['inst_name'].nunique()
                summary["总买入金额"] = df['buy_amt'].sum() if 'buy_amt' in df.columns else 0
                summary["总卖出金额"] = df['sell_amt'].sum() if 'sell_amt' in df.columns else 0
            elif table_type == 'flow' and 'name' in df.columns:
                summary["股票名称数"] = df['name'].nunique()
                summary["龙虎榜总买入"] = df['lhb_buy'].sum() if 'lhb_buy' in df.columns else 0
                summary["龙虎榜总卖出"] = df['lhb_sell'].sum() if 'lhb_sell' in df.columns else 0
            
            return summary
            
        except Exception as e:
            logger.error(f"生成概要统计失败: {e}")
            return None
    
    def get_top_seats(self, days: int = 30, top_n: int = 10, table_type: str = 'seat') -> Optional[pd.DataFrame]:
        """
        获取最活跃的交易席位
        
        Args:
            days: 统计最近几天
            top_n: 返回前N名
            table_type: 数据类型 ('seat'游资席位, 'inst'机构席位)
            
        Returns:
            pandas.DataFrame: 席位统计信息
        """
        # 获取实际的数据日期范围
        try:
            table_map = {'seat': 'seat_daily', 'inst': 'inst_flow', 'flow': 'trade_flow'}
            table_name = table_map.get(table_type, 'seat_daily')
            
            latest_result = self.client.table(table_name).select('trade_date').order('trade_date', desc=True).limit(1).execute()
            
            if latest_result.data and latest_result.data[0]['trade_date']:
                end_date = latest_result.data[0]['trade_date']
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                start_datetime = end_datetime - timedelta(days=days)
                start_date = start_datetime.strftime('%Y-%m-%d')
            else:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        except Exception:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = self.get_dragon_tiger_data(start_date=start_date, end_date=end_date, table_type=table_type)
        
        if df is None or df.empty:
            return None
        
        try:
            # 根据数据类型选择不同的席位字段
            if table_type == 'seat' and 'seat_name' in df.columns:
                seat_column = 'seat_name'
            elif table_type == 'inst' and 'inst_name' in df.columns:
                seat_column = 'inst_name'
            else:
                logger.warning(f"表类型 {table_type} 中没有找到席位字段")
                return None
            
            # 统计各席位的上榜次数和涉及股票数
            seat_stats = df.groupby(seat_column).agg({
                'code': ['count', 'nunique'],
                'buy_amt': 'sum' if 'buy_amt' in df.columns else 'count',
                'sell_amt': 'sum' if 'sell_amt' in df.columns else 'count',
                'net_amt': 'sum' if 'net_amt' in df.columns else 'count'
            }).round(2)
            
            seat_stats.columns = ['上榜次数', '涉及股票数', '总买入金额(万)', '总卖出金额(万)', '净买入金额(万)']
            
            # 转换为万元
            for col in ['总买入金额(万)', '总卖出金额(万)', '净买入金额(万)']:
                if col in seat_stats.columns:
                    seat_stats[col] = seat_stats[col] / 10000
            
            # 按上榜次数排序
            seat_stats = seat_stats.sort_values('上榜次数', ascending=False)
            
            return seat_stats.head(top_n)
            
        except Exception as e:
            logger.error(f"获取活跃席位失败: {e}")
            return None
    
    def get_recent_stocks(self, days: int = 5) -> Optional[pd.DataFrame]:
        """
        获取最近上榜的股票
        
        Args:
            days: 最近几天
            
        Returns:
            pandas.DataFrame: 最近上榜股票信息
        """
        # 获取实际的数据日期范围
        try:
            latest_result = self.client.table('trade_flow').select('trade_date').order('trade_date', desc=True).limit(1).execute()
            
            if latest_result.data and latest_result.data[0]['trade_date']:
                end_date = latest_result.data[0]['trade_date']
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                start_datetime = end_datetime - timedelta(days=days)
                start_date = start_datetime.strftime('%Y-%m-%d')
            else:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        except Exception:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 优先使用trade_flow表，包含更完整的股票信息
        df = self.get_dragon_tiger_data(start_date=start_date, end_date=end_date, limit=200, table_type='flow')
        
        if df is None or df.empty:
            # 备用：使用seat_daily表
            df = self.get_dragon_tiger_data(start_date=start_date, end_date=end_date, limit=200, table_type='seat')
        
        if df is None or df.empty:
            return None
        
        try:
            if 'name' in df.columns:  # trade_flow表
                # 按股票代码和日期聚合
                stock_summary = df.groupby(['code', 'trade_date']).agg({
                    'name': 'first',
                    'close': 'first' if 'close' in df.columns else 'count',
                    'pct_chg': 'first' if 'pct_chg' in df.columns else 'count',
                    'lhb_net_buy': 'sum' if 'lhb_net_buy' in df.columns else 'count',
                    'reason': 'first' if 'reason' in df.columns else 'count'
                }).reset_index()
                
                stock_summary.columns = ['股票代码', '交易日期', '股票名称', '收盘价', '涨跌幅(%)', '净买入(万)', '上榜原因']
                
            else:  # seat_daily表
                # 按股票代码和日期聚合
                stock_summary = df.groupby(['code', 'trade_date']).agg({
                    'name': 'first' if 'name' in df.columns else 'count',
                    'seat_name': 'count',  # 上榜席位数量
                    'net_amt': 'sum' if 'net_amt' in df.columns else 'count'
                }).reset_index()
                
                stock_summary.columns = ['股票代码', '交易日期', '股票名称', '席位数量', '总净额(万)']
            
            # 转换金额单位为万元
            for col in stock_summary.columns:
                if '万' in col and col != '股票名称':
                    stock_summary[col] = stock_summary[col] / 10000
            
            stock_summary = stock_summary.sort_values('交易日期', ascending=False)
            
            return stock_summary
            
        except Exception as e:
            logger.error(f"获取最近上榜股票失败: {e}")
            return None

# 创建全局客户端实例
@st.cache_resource
def get_supabase_client() -> SupabaseDataClient:
    """获取Supabase客户端实例（缓存）"""
    return SupabaseDataClient()