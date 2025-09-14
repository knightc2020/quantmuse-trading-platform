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
from .tonghuashun_client import TonghuasunDataClient, get_tonghuashun_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSynchronizer:
    """数据同步器"""
    
    def __init__(self):
        """初始化数据同步器"""
        self.supabase_client = SupabaseDataClient()
        # 统一使用全局同花顺客户端，避免重复登录导致 -201
        self.ths_client = get_tonghuashun_client()
        
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
                    'trade_date': 'trade_date',
                    'code': 'code',
                    'time': 'trade_date',
                    'stock_code': 'code',
                    # 官方/实时与历史常见字段（若存在则映射）
                    'preClose': 'pre_close',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'amount': 'amount',
                    'turn': 'turnover_ratio',
                    'turnoverRatio': 'turnover_ratio',
                    'pctChg': 'pct_chg',
                    'change': 'change',
                    'changeRatio': 'change_ratio',
                    'upperLimit': 'upper_limit',
                    'downLimit': 'lower_limit',
                    'riseDayCount': 'rise_day_count',
                    'suspensionFlag': 'suspension_flag',
                    'tradeStatus': 'trade_status',
                    'avgPrice': 'avg_price',
                    'pe_ttm': 'pe_ttm',
                    'pb': 'pb',
                    'total_mv': 'total_mv',
                    'mv': 'mv',
                    # THS_BD 官方基础函数补充映射
                    'ths_pre_close_stock': 'pre_close',
                    'ths_open_price_stock': 'open',
                    'ths_high_price_stock': 'high',
                    'ths_low_stock': 'low',
                    'ths_close_price_stock': 'close',
                    'ths_avg_price_stock': 'avg_price',
                    'ths_max_up_stock': 'upper_limit',
                    'ths_max_down_stock': 'lower_limit',
                    'ths_chg_ratio_stock': 'change_ratio',
                    'ths_chg_stock': 'change',
                    'ths_vol_stock': 'volume',
                    'ths_vol_btin_stock': 'volume_btin',
                    'ths_amt_btin_stock': 'amount_btin',
                    'ths_trans_num_stock': 'trans_num',
                    'ths_amt_stock': 'amount',
                    'ths_vol_after_trading_stock': 'post_volume',
                    'ths_trans_num_after_trading_stock': 'post_trans_num',
                    'ths_amt_after_trading_stock': 'post_amount',
                    'ths_turnover_ratio_stock': 'turnover_ratio',
                    'ths_vaild_turnover_stock': 'valid_turnover_ratio',
                    'ths_swing_stock': 'swing',
                    'ths_relative_issue_price_chg_stock': 'rel_issue_chg',
                    'ths_relative_issue_price_chg_ratio_stock': 'rel_issue_chg_ratio',
                    'ths_relative_chg_ratio_stock': 'rel_market_chg_ratio',
                    'ths_trading_status_stock': 'trade_status',
                    'ths_continuous_suspension_days_stock': 'suspension_days',
                    'ths_suspen_reason_stock': 'suspension_reason',
                    'ths_af_stock': 'adj_factor',
                    'ths_af2_stock': 'adj_factor2',
                    'ths_up_and_down_status_stock': 'limit_status',
                    'ths_last_td_date_stock': 'last_trade_date',
                    'ths_specified_datenearly_td_date_stock': 'nearest_trade_date',
                    'ths_ahshare_premium_rate_stock': 'ah_premium_rate'
                },
                'calculated_fields': {}
            }
        }
    
    def check_connection(self) -> bool:
        """检查连接状态"""
        supabase_ok = self.supabase_client.is_connected()
        # 主动确保同花顺登录，包含重试
        ths_ok = False
        if self.ths_client:
            try:
                ths_ok = self.ths_client._ensure_login()
            except Exception:
                ths_ok = False
        
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

            # 处理重名列：优先使用靠后的列（通常为 THS_BD 指标），
            # 同时用前列在后列为空时进行补齐，避免信息丢失
            try:
                cols = list(df_transformed.columns)
                dup_names = [c for c in cols if cols.count(c) > 1]
                for name in sorted(set(dup_names)):
                    # 取所有同名列，按出现顺序从左到右
                    sub = df_transformed.loc[:, [c == name for c in df_transformed.columns]]
                    # 让靠后的列优先：前向填充后取最后一列
                    combined = sub.ffill(axis=1).iloc[:, -1]
                    df_transformed[name] = combined
                if dup_names:
                    # 删除多余同名列，只保留最后一个（已写入合并结果）
                    df_transformed = df_transformed.loc[:, ~df_transformed.columns.duplicated(keep='last')]
            except Exception as e:
                logger.warning(f"去重合并列失败，将继续后续清洗: {e}")
            
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
            for dcol in ['trade_date','last_trade_date','nearest_trade_date']:
                if dcol in df_clean.columns:
                    ser = pd.to_datetime(df_clean[dcol], errors='coerce').dt.strftime('%Y-%m-%d')
                    # 将无效日期转换为 None（避免写库时出现 'NaT' 字符串）
                    ser = ser.replace('NaT', None)
                    df_clean[dcol] = ser
            
            # 处理数值字段
            numeric_fields = ['buy_amt', 'sell_amt', 'net_amt', 'lhb_buy', 'lhb_sell', 'lhb_net_buy',
                             'pre_close', 'open', 'high', 'low', 'close', 'volume', 'amount',
                             'amount_btin', 'volume_btin', 'trans_num', 'post_volume', 'post_trans_num', 'post_amount',
                             'turnover_ratio', 'valid_turnover_ratio', 'pct_chg', 'change', 'change_ratio',
                             'upper_limit', 'lower_limit', 'rise_day_count', 'avg_price', 'swing',
                             'rel_issue_chg', 'rel_issue_chg_ratio', 'rel_market_chg_ratio',
                             'pe_ttm', 'pb', 'total_mv', 'mv', 'adj_factor', 'adj_factor2', 'ah_premium_rate']
            
            for field in numeric_fields:
                if field in df_clean.columns:
                    df_clean[field] = pd.to_numeric(df_clean[field], errors='coerce')
                    df_clean[field] = df_clean[field].fillna(0)

            # 强制为整数的字段，避免传入"0.0"导致 bigint 解析失败
            integer_fields = [
                'volume', 'volume_btin', 'trans_num', 'post_volume', 'post_trans_num',
                'rise_day_count', 'suspension_days'
            ]
            for field in integer_fields:
                if field in df_clean.columns:
                    try:
                        # 一律向最近整数取整后转为 Python int，确保 JSON 为整数
                        df_clean[field] = pd.to_numeric(df_clean[field], errors='coerce').fillna(0).round().astype('int64')
                    except Exception:
                        # 退化路径：逐元素转换
                        df_clean[field] = df_clean[field].apply(lambda x: int(float(str(x))) if pd.notnull(x) and str(x).strip() != '' else 0)
            
            # 处理字符串字段
            text_fields = ['code', 'name', 'seat_name', 'seat_type', 'reason', 'trade_status', 'suspension_reason', 'limit_status']
            for field in text_fields:
                if field in df_clean.columns:
                    df_clean[field] = df_clean[field].astype(str).fillna('')

            # 布尔字段
            if 'suspension_flag' in df_clean.columns:
                def _to_bool(x):
                    s = str(x).strip().lower()
                    if s in ('1', 'true', 't', 'yes', 'y'):
                        return True
                    if s in ('0', 'false', 'f', 'no', 'n'):
                        return False
                    try:
                        return bool(float(s))
                    except Exception:
                        return False
                df_clean['suspension_flag'] = df_clean['suspension_flag'].apply(_to_bool)
            
            # 去除重复记录
            if table_type == 'seat_daily':
                # 如果缺少 seat_name 列，则退化为按 trade_date+code 去重，避免 KeyError
                if 'seat_name' in df_clean.columns:
                    df_clean = df_clean.drop_duplicates(subset=['trade_date', 'code', 'seat_name'], keep='last')
                else:
                    logger.warning('seat_daily 数据缺少 seat_name 列，按 trade_date+code 去重并跳过席位明细写入')
                    df_clean = df_clean.drop_duplicates(subset=['trade_date', 'code'], keep='last')
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
        # 设置 upsert 冲突键，确保后续补丁可覆盖早期仅 code/trade_date 的空记录
        conflict_keys = {
            'seat_daily': 'trade_date,code,seat_name',
            'trade_flow': 'trade_date,code',
            'daily_quotes': 'trade_date,code'
        }.get(table_type, None)
        
        try:
            # 兜底处理：将所有 NaN/NaT 替换为 None，避免 JSON 序列化失败
            try:
                df = df.where(pd.notnull(df), None)
            except Exception:
                pass
            # 转换DataFrame为字典列表
            records = df.to_dict('records')
            
            # 分批写入，避免单次请求过大
            batch_size = 1000
            total_records = len(records)
            success_count = 0
            
            for i in range(0, total_records, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    table = self.supabase_client.client.table(target_table)
                    result = None
                    # 优先使用带 on_conflict 的 upsert，以覆盖旧的空值记录
                    try:
                        if conflict_keys:
                            result = table.upsert(
                                batch,
                                on_conflict=conflict_keys,
                                ignore_duplicates=False,  # 强制合并而非忽略
                                default_to_null=False     # 未提供的列不置为 NULL
                            ).execute()
                        else:
                            result = table.upsert(batch).execute()
                    except TypeError:
                        # 兼容旧版 supabase-py 参数名
                        try:
                            if conflict_keys:
                                result = table.upsert(
                                    batch,
                                    on_conflict=conflict_keys
                                ).execute()
                            else:
                                result = table.upsert(batch).execute()
                        except Exception as ie:
                            raise ie
                    
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
            # 获取同花顺数据（拆分为：席位明细 + 交易流向）
            flow_raw = self.ths_client.get_dragon_tiger_data(start_date, end_date)
            seat_raw = self.ths_client.get_dragon_tiger_seat_data(start_date, end_date)
            
            if (flow_raw is None or flow_raw.empty) and (seat_raw is None or seat_raw.empty):
                logger.warning("未获取到任何龙虎榜数据")
                return False
            
            # 分别处理席位数据和交易流向数据
            success = True
            
            # 处理席位数据
            if seat_raw is not None and not seat_raw.empty:
                seat_data = self.transform_data(seat_raw, 'seat_daily')
                if not seat_data.empty and 'seat_name' in seat_data.columns:
                    success &= self.write_to_supabase(seat_data, 'seat_daily')
                else:
                    logger.info('席位数据转换后无 seat_name 列，跳过 seat_daily 表写入')
            
            # 处理交易流向数据  
            if flow_raw is not None and not flow_raw.empty:
                flow_data = self.transform_data(flow_raw, 'trade_flow')
                if not flow_data.empty and (
                    ('lhb_buy' in flow_data.columns) or
                    ('lhb_sell' in flow_data.columns) or
                    ('lhb_net_buy' in flow_data.columns)
                ):
                    success &= self.write_to_supabase(flow_data, 'trade_flow')
                else:
                    logger.warning('trade_flow 关键字段缺失，跳过 trade_flow 表写入')
            
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
