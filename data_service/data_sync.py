#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步模块
处理同花顺数据写入Supabase数据库
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

from .supabase_client import SupabaseDataClient
from .tonghuashun_client import TonghuasunDataClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSynchronizer:
    """数据同步器"""
    
    def __init__(self):
        """初始化数据同步器"""
        self.supabase_client = SupabaseDataClient()
        self.ths_client = TonghuasunDataClient()
        
        # 表字段映射配置
        self.table_mappings = {
            'seat_daily': {
                'target_table': 'seat_daily',
                'field_mapping': {
                    'trade_date': 'trade_date',
                    'ths_stock_code_stock': 'code',
                    'ths_stock_short_name_stock': 'name',
                    'ths_lhb_seat_name_stock': 'seat_name',
                    'ths_lhb_seat_type_stock': 'seat_type',
                    'ths_lhb_buy_amount_seat_stock': 'buy_amt',
                    'ths_lhb_sell_amount_seat_stock': 'sell_amt',
                    'ths_lhb_reason_stock': 'reason'
                },
                'calculated_fields': {
                    'net_amt': lambda row: (row.get('buy_amt', 0) or 0) - (row.get('sell_amt', 0) or 0)
                }
            },
            'trade_flow': {
                'target_table': 'trade_flow',
                'field_mapping': {
                    'trade_date': 'trade_date',
                    'ths_stock_code_stock': 'code',
                    'ths_stock_short_name_stock': 'name',
                    'ths_lhb_buy_amount_stock': 'lhb_buy',
                    'ths_lhb_sell_amount_stock': 'lhb_sell',
                    'ths_lhb_net_buy_amount_stock': 'lhb_net_buy',
                    'ths_lhb_turnover_ratio_stock': 'lhb_turnover_ratio',
                    'ths_lhb_reason_stock': 'reason'
                },
                'calculated_fields': {}
            },
            'daily_quotes': {
                'target_table': 'daily_quotes',
                'field_mapping': {
                    'time': 'trade_date',
                    'stock_code': 'code',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'amount': 'amount',
                    'turn': 'turnover',
                    'pctChg': 'pct_chg',
                    'avgPrice': 'avg_price',
                    'pe_ttm': 'pe_ttm',
                    'pb': 'pb',
                    'total_mv': 'total_mv'
                },
                'calculated_fields': {}
            }
        }
    
    def check_connection(self) -> bool:
        """检查连接状态"""
        supabase_ok = self.supabase_client.is_connected()
        ths_ok = self.ths_client.is_logged_in if self.ths_client else False
        
        logger.info(f"Supabase连接状态: {'✓' if supabase_ok else '✗'}")
        logger.info(f"同花顺连接状态: {'✓' if ths_ok else '✗'}")
        
        return supabase_ok and ths_ok
    
    def get_last_sync_date(self, table_type: str) -> Optional[str]:
        """获取最后同步日期"""
        try:
            table_map = {
                'dragon_tiger': 'seat_daily',
                'daily_quotes': 'daily_quotes'
            }
            
            table_name = table_map.get(table_type, 'seat_daily')
            
            result = self.supabase_client.client.table(table_name)\
                .select('trade_date')\
                .order('trade_date', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                last_date = result.data[0]['trade_date']
                logger.info(f"{table_name}表最后同步日期: {last_date}")
                return last_date
            else:
                logger.warning(f"{table_name}表暂无数据")
                return None
                
        except Exception as e:
            logger.error(f"获取最后同步日期失败: {e}")
            return None
    
    def transform_data(self, df: pd.DataFrame, table_type: str) -> pd.DataFrame:
        """数据格式转换"""
        if df is None or df.empty:
            return df
        
        if table_type not in self.table_mappings:
            logger.error(f"未知表类型: {table_type}")
            return df
        
        mapping_config = self.table_mappings[table_type]
        field_mapping = mapping_config['field_mapping']
        calculated_fields = mapping_config['calculated_fields']
        
        try:
            # 重命名字段
            df_transformed = df.copy()
            
            # 只保留映射中存在的字段
            available_fields = {}
            for source_field, target_field in field_mapping.items():
                if source_field in df_transformed.columns:
                    available_fields[source_field] = target_field
                else:
                    logger.debug(f"源字段 {source_field} 不存在于数据中")
            
            df_transformed = df_transformed[list(available_fields.keys())].copy()
            df_transformed = df_transformed.rename(columns=available_fields)
            
            # 计算派生字段
            for calc_field, calc_func in calculated_fields.items():
                try:
                    df_transformed[calc_field] = df_transformed.apply(calc_func, axis=1)
                except Exception as e:
                    logger.warning(f"计算字段 {calc_field} 失败: {e}")
            
            # 数据类型转换和清理
            df_transformed = self._clean_data(df_transformed, table_type)
            
            logger.info(f"数据转换完成，转换后字段: {list(df_transformed.columns)}")
            return df_transformed
            
        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            return df
    
    def _clean_data(self, df: pd.DataFrame, table_type: str) -> pd.DataFrame:
        """数据清理和类型转换"""
        try:
            df_clean = df.copy()
            
            # 处理日期字段
            if 'trade_date' in df_clean.columns:
                df_clean['trade_date'] = pd.to_datetime(df_clean['trade_date']).dt.strftime('%Y-%m-%d')
            
            # 处理数值字段
            numeric_fields = ['buy_amt', 'sell_amt', 'net_amt', 'lhb_buy', 'lhb_sell', 'lhb_net_buy',
                             'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'pct_chg',
                             'avg_price', 'pe_ttm', 'pb', 'total_mv']
            
            for field in numeric_fields:
                if field in df_clean.columns:
                    df_clean[field] = pd.to_numeric(df_clean[field], errors='coerce')
                    df_clean[field] = df_clean[field].fillna(0)
            
            # 处理字符串字段
            text_fields = ['code', 'name', 'seat_name', 'seat_type', 'reason']
            for field in text_fields:
                if field in df_clean.columns:
                    df_clean[field] = df_clean[field].astype(str).fillna('')
            
            # 去除重复记录
            if table_type == 'seat_daily':
                df_clean = df_clean.drop_duplicates(subset=['trade_date', 'code', 'seat_name'], keep='last')
            elif table_type == 'trade_flow':
                df_clean = df_clean.drop_duplicates(subset=['trade_date', 'code'], keep='last')
            elif table_type == 'daily_quotes':
                df_clean = df_clean.drop_duplicates(subset=['trade_date', 'code'], keep='last')
            
            logger.info(f"数据清理完成，清理后记录数: {len(df_clean)}")
            return df_clean
            
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            return df
    
    def write_to_supabase(self, df: pd.DataFrame, table_type: str) -> bool:
        """写入数据到Supabase"""
        if df is None or df.empty:
            logger.warning("没有数据需要写入")
            return True
        
        if table_type not in self.table_mappings:
            logger.error(f"未知表类型: {table_type}")
            return False
        
        target_table = self.table_mappings[table_type]['target_table']
        
        try:
            # 转换DataFrame为字典列表
            records = df.to_dict('records')
            
            # 分批写入，避免单次请求过大
            batch_size = 1000
            total_records = len(records)
            success_count = 0
            
            for i in range(0, total_records, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    result = self.supabase_client.client.table(target_table).upsert(batch).execute()
                    
                    if result.data:
                        success_count += len(batch)
                        logger.info(f"成功写入第{i//batch_size + 1}批数据到{target_table}表，{len(batch)}条记录")
                    else:
                        logger.error(f"第{i//batch_size + 1}批数据写入失败")
                        
                except Exception as e:
                    logger.error(f"第{i//batch_size + 1}批数据写入异常: {e}")
                    continue
            
            success_rate = success_count / total_records if total_records > 0 else 0
            logger.info(f"数据写入完成，成功率: {success_rate:.2%} ({success_count}/{total_records})")
            
            return success_rate > 0.9  # 90%成功率视为成功
            
        except Exception as e:
            logger.error(f"数据写入失败: {e}")
            return False
    
    def sync_dragon_tiger_data(self, start_date: str, end_date: str = None) -> bool:
        """同步龙虎榜数据"""
        logger.info(f"开始同步龙虎榜数据: {start_date} 到 {end_date or start_date}")
        
        try:
            # 获取同花顺数据
            ths_data = self.ths_client.get_dragon_tiger_data(start_date, end_date)
            
            if ths_data is None or ths_data.empty:
                logger.warning("未获取到龙虎榜数据")
                return False
            
            # 分别处理席位数据和交易流向数据
            success = True
            
            # 处理席位数据
            seat_data = self.transform_data(ths_data, 'seat_daily')
            if not seat_data.empty:
                success &= self.write_to_supabase(seat_data, 'seat_daily')
            
            # 处理交易流向数据  
            flow_data = self.transform_data(ths_data, 'trade_flow')
            if not flow_data.empty:
                success &= self.write_to_supabase(flow_data, 'trade_flow')
            
            return success
            
        except Exception as e:
            logger.error(f"龙虎榜数据同步失败: {e}")
            return False
    
    def sync_daily_quotes(self, stock_codes: List[str], start_date: str, end_date: str = None) -> bool:
        """同步日线数据"""
        logger.info(f"开始同步日线数据: {len(stock_codes)}只股票，{start_date} 到 {end_date or start_date}")
        
        try:
            # 获取同花顺数据
            ths_data = self.ths_client.get_daily_data(stock_codes, start_date, end_date)
            
            if ths_data is None or ths_data.empty:
                logger.warning("未获取到日线数据")
                return False
            
            # 数据转换
            quotes_data = self.transform_data(ths_data, 'daily_quotes')
            
            if quotes_data.empty:
                logger.warning("转换后的日线数据为空")
                return False
            
            # 写入数据库
            return self.write_to_supabase(quotes_data, 'daily_quotes')
            
        except Exception as e:
            logger.error(f"日线数据同步失败: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态报告"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'connections': {
                'supabase': self.supabase_client.is_connected(),
                'tonghuashun': self.ths_client.is_logged_in if self.ths_client else False
            },
            'last_sync_dates': {},
            'table_stats': {}
        }
        
        # 获取各表最后同步日期
        for table_type in ['dragon_tiger', 'daily_quotes']:
            status['last_sync_dates'][table_type] = self.get_last_sync_date(table_type)
        
        # 获取表统计信息
        try:
            for table_type in ['seat', 'flow']:
                summary = self.supabase_client.get_dragon_tiger_summary(table_type=table_type)
                if summary:
                    status['table_stats'][table_type] = summary
        except Exception as e:
            logger.warning(f"获取表统计信息失败: {e}")
        
        return status

# 全局同步器实例
_data_sync = None

def get_data_synchronizer() -> DataSynchronizer:
    """获取数据同步器实例（单例模式）"""
    global _data_sync
    if _data_sync is None:
        _data_sync = DataSynchronizer()
    return _data_sync