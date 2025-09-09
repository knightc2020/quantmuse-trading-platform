#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺iFinD数据获取客户端
用于补齐龙虎榜和日线数据
"""

import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
import time
import json
import threading
from collections import deque
from dotenv import load_dotenv
from collections import OrderedDict

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """API请求频率限制器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口大小(秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def acquire(self) -> bool:
        """获取请求许可"""
        with self.lock:
            now = time.time()
            
            # 清除过期请求记录
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()
            
            # 检查是否可以发起请求
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            else:
                # 计算等待时间
                wait_time = self.time_window - (now - self.requests[0]) + 0.1
                logger.warning(f"API请求频率限制，等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
                return self.acquire()  # 递归重试

class TonghuasunDataClient:
    """同花顺数据客户端"""
    
    def __init__(self, user_id: str = None, password: str = None):
        """初始化同花顺客户端"""
        self.client = None
        # 确保THS属性总是存在，避免导入失败时属性缺失
        self.THS = None
        self.is_logged_in = False
        self.user_id = user_id or os.getenv("THS_USER_ID")
        self.password = password or os.getenv("THS_PASSWORD")
        # 登录重试与退避参数
        try:
            self.max_retries = int(os.getenv("THS_MAX_RETRIES", "3"))
        except Exception:
            self.max_retries = 3
        self._base_retry_delay = 1.0  # 秒
        
        # 限流与节流参数（可用环境变量覆盖）
        try:
            rl_max = int(os.getenv("THS_RL_MAX_REQUESTS", "30"))
        except Exception:
            rl_max = 30
        try:
            rl_window = int(os.getenv("THS_RL_WINDOW", "60"))
        except Exception:
            rl_window = 60
        try:
            self.call_interval = float(os.getenv("THS_CALL_INTERVAL", "2.2"))  # 单次调用间隔秒数
        except Exception:
            self.call_interval = 2.2
        try:
            self.batch_interval = float(os.getenv("THS_BATCH_INTERVAL", "2.0"))  # 批次间隔秒数
        except Exception:
            self.batch_interval = 2.0

        # 初始化限流器
        self.rate_limiter = RateLimiter(max_requests=rl_max, time_window=rl_window)
        
        self._initialize_client()

    # -------------------- 通用结果解析工具 --------------------
    @staticmethod
    def _ensure_list_of_dicts(obj: Any) -> List[Dict[str, Any]]:
        if obj is None:
            return []
        try:
            import pandas as pd  # type: ignore
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict('records')
        except Exception:
            pass
        if isinstance(obj, list):
            # 允许列表元素为 dict 或可转换
            rows = []
            for it in obj:
                if isinstance(it, dict):
                    rows.append(it)
                else:
                    rows.append({'value': it})
            return rows
        if isinstance(obj, dict):
            return [obj]
        # 标量
        return [{'value': obj}]

    @staticmethod
    def _try_json_loads(text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except Exception:
            return None

    @staticmethod
    def _decode_bytes(b: bytes) -> str:
        for enc in ('utf-8', 'gbk', 'gb2312', 'latin1'):
            try:
                return b.decode(enc, errors='ignore')
            except Exception:
                continue
        return b.decode('utf-8', errors='ignore')

    def _parse_ths_result(self, res: Any) -> (Optional[int], List[Dict[str, Any]]):
        """尽量适配不同版本/形态的 iFinD 返回，统一为 (code, rows[list[dict]])."""
        # 经典 (code, data) 形式
        if isinstance(res, (list, tuple)):
            code = None
            data = []
            if len(res) > 0:
                try:
                    code = int(res[0])
                except Exception:
                    code = None
            if len(res) > 1:
                data = self._ensure_list_of_dicts(res[1])
            return code, data

        # 字节串 -> 尝试 JSON 解析
        if isinstance(res, (bytes, bytearray)):
            text = self._decode_bytes(bytes(res))
            obj = self._try_json_loads(text)
            if isinstance(obj, dict):
                return self._parse_ths_result(obj)
            # 无法解析当空
            return None, []

        # 字符串 -> 尝试 JSON 解析
        if isinstance(res, str):
            obj = self._try_json_loads(res.strip())
            if isinstance(obj, dict):
                return self._parse_ths_result(obj)
            return None, []

        # 映射对象（dict/OrderedDict）
        if isinstance(res, (dict, OrderedDict)):
            # 常见键名兜底
            code = None
            for k in ('errorcode', 'ErrCode', 'code', 'return', 'retCode', 'retcode'):
                if k in res:
                    try:
                        code = int(res[k])
                    except Exception:
                        code = None
                    break
            # 可能的数据键
            for dk in ('tables', 'data', 'result', 'rows', 'list', 'items'):
                if dk in res and isinstance(res[dk], (list, dict)):
                    return code, self._ensure_list_of_dicts(res[dk])
            # 一些实现将数据放在第一层（键值对即一行）
            if res:
                return code, [res]
            return code, []

        # 其他未知类型
        return None, []

    @staticmethod
    def _maybe_json_list(val: Any) -> Any:
        """If val is a JSON list in string form, parse to Python list; else return as is."""
        if isinstance(val, str):
            s = val.strip()
            if s.startswith('[') and s.endswith(']'):
                try:
                    obj = json.loads(s)
                    return obj
                except Exception:
                    return val
        return val

    def _normalize_history_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize history quotes result to one row per time point.

        Some iFinD returns pack each column as a list in a single row (time, open, ... are lists).
        Detect that pattern and expand so that each list element becomes a separate row.
        """
        try:
            if df is None or df.empty:
                return df
            # If multiple rows already, assume normalized
            if len(df) > 1:
                return df

            row = df.iloc[0]
            # Detect list-like cells
            list_cols = {}
            scalar_cols = {}
            max_len = 0
            for col in df.columns:
                val = self._maybe_json_list(row.get(col))
                if isinstance(val, list):
                    list_cols[col] = val
                    max_len = max(max_len, len(val))
                else:
                    scalar_cols[col] = val

            # If no list-like columns found, return as is
            if not list_cols:
                return df

            # Build expanded rows
            records: List[Dict[str, Any]] = []
            for i in range(max_len):
                rec: Dict[str, Any] = {}
                # list columns: pick ith if available else None
                for c, arr in list_cols.items():
                    rec[c] = arr[i] if i < len(arr) else None
                # scalar columns: broadcast
                for c, v in scalar_cols.items():
                    rec[c] = v
                # Flatten inner 'table' structure if present (common in iFinD results)
                if 'table' in rec and isinstance(rec['table'], (dict,)):
                    try:
                        tbl = rec.pop('table')
                        # table may itself have lists; prefer scalar per-row values
                        for k, v in tbl.items():
                            if isinstance(v, list):
                                # pick ith element if aligned, else None
                                rec[k] = v[i] if i < len(v) else None
                            else:
                                rec[k] = v
                    except Exception:
                        # if cannot flatten, keep as-is
                        pass
                records.append(rec)

            expanded = pd.DataFrame(records)
            return expanded
        except Exception as e:
            logger.warning(f"历史数据归一化失败，使用原始数据: {e}")
            return df

    def _align_history_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Best-effort align history quotes columns to expected names used downstream.

        Expected output columns: time, stock_code, open, high, low, close, volume,
        amount, turn, pctChg, avgPrice, pe_ttm, pb, total_mv
        """
        try:
            cols_map: Dict[str, str] = {}
            lower_map = {c.lower(): c for c in df.columns}

            def find_col(candidates: List[str]) -> Optional[str]:
                # exact lower match first
                for key in candidates:
                    if key in lower_map:
                        return lower_map[key]
                # substring match
                for key in candidates:
                    for lc, orig in lower_map.items():
                        if key in lc:
                            return orig
                return None

            # time column
            if 'time' not in df.columns:
                tcol = find_col(['time', 'trade_date', 'date', 'datetime'])
                if tcol:
                    cols_map[tcol] = 'time'

            # stock code column
            if 'stock_code' not in df.columns:
                ccol = find_col(['stock_code', 'code', 'thscode', 'seccode', 'security_code'])
                if ccol:
                    cols_map[ccol] = 'stock_code'

            synonyms = {
                'open': ['open', 'open_price', 'ths_open_price_stock'],
                'high': ['high', 'high_price', 'ths_high_price_stock'],
                'low': ['low', 'low_price', 'ths_low_price_stock'],
                'close': ['close', 'close_price', 'ths_close_price_stock', 'price'],
                'volume': ['volume', 'vol', 'turnover_volume'],
                'amount': ['amount', 'amt', 'turnover_amount'],
                'turn': ['turn', 'turnover', 'turnoverratio', 'turnover_ratio'],
                'turnoverRatio': ['turnoverratio', 'turnover_ratio', 'turn'],
                'pctChg': ['pctchg', 'changeratio', 'change_pct', 'pct_chg', 'change_ratio'],
                'avgPrice': ['avgprice', 'average', 'averageprice'],
                'pe_ttm': ['pe_ttm', 'pettm'],
                'pb': ['pb', 'pb_ratio'],
                'total_mv': ['total_mv', 'marketvalue', 'total_market_cap', 'mv_total'],
                'preClose': ['preclose', 'pre_close'],
                'change': ['change', 'chg'],
                'changeRatio': ['changeratio', 'pctchg', 'pct_chg'],
                'upperLimit': ['upperlimit', 'up_limit'],
                'downLimit': ['downlimit', 'low_limit', 'lower_limit'],
                'riseDayCount': ['risedaycount'],
                'suspensionFlag': ['suspensionflag', 'susp_flag', 'suspended'],
                'tradeStatus': ['tradestatus', 'status'],
                'mv': ['mv', 'float_mv', 'circulation_mv']
            }

            for target, cands in synonyms.items():
                if target in df.columns:
                    continue
                found = find_col(cands)
                if found:
                    cols_map[found] = target

            if cols_map:
                df = df.rename(columns=cols_map)
            return df
        except Exception as e:
            logger.warning(f"列名对齐失败，使用原始列名: {e}")
            return df
    
    def _initialize_client(self):
        """初始化iFinD客户端"""
        try:
            # 导入iFinD Python包
            import iFinDPy as THS
            self.THS = THS
            logger.info("iFinD Python包导入成功")
        except ImportError as e:
            logger.error(f"iFinD Python包导入失败: {e}")
            logger.error("请确保已安装同花顺iFinD终端并配置Python环境")
            return
        
        # 尝试登录
        if self.user_id and self.password:
            self.login()
    
    def login(self) -> bool:
        """登录iFinD"""
        if not self.THS:
            logger.error("iFinD客户端未初始化")
            return False
        
        if not self.user_id or not self.password:
            logger.error("请设置THS_USER_ID和THS_PASSWORD环境变量")
            return False
        
        try:
            result = self.THS.THS_iFinDLogin(self.user_id, self.password)
            # 官方示例：0 与 -201 都视为可用登录态
            if result in (0, -201):
                self.is_logged_in = True
                logger.info("同花顺iFinD登录成功")
                return True
            else:
                logger.error(f"同花顺iFinD登录失败，错误码: {result}")
                return False
        except Exception as e:
            logger.error(f"登录过程中发生异常: {e}")
            return False
    
    def logout(self):
        """登出iFinD"""
        if self.THS and self.is_logged_in:
            try:
                self.THS.THS_iFinDLogout()
                self.is_logged_in = False
                logger.info("已登出同花顺iFinD")
            except Exception as e:
                logger.error(f"登出时发生异常: {e}")
    
    def _ensure_login(self) -> bool:
        """确保已登录"""
        if not self.is_logged_in:
            # 带重试的登录
            attempt = 0
            while attempt < self.max_retries:
                attempt += 1
                if self.login():
                    return True
                # 指数退避
                delay = self._base_retry_delay * (2 ** (attempt - 1))
                logger.warning(f"登录失败，第{attempt}次重试，{delay:.1f}s 后重试...")
                time.sleep(delay)
            logger.error("多次登录失败，放弃本次操作")
            return False
        return True
    
    def get_dragon_tiger_data(self, 
                             start_date: str, 
                             end_date: str = None,
                             stock_codes: List[str] = None) -> Optional[pd.DataFrame]:
        """
        获取龙虎榜数据（按股票的交易流向汇总数据）
        注：本方法当前聚焦交易流向（trade_flow）相关字段；席位明细另行实现。
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD，默认为开始日期
            stock_codes: 股票代码列表，默认全市场
            
        Returns:
            DataFrame: 龙虎榜数据
        """
        if not self._ensure_login():
            return None
        
        if not end_date:
            end_date = start_date
        
        try:
            # 首选：使用 THS_DataPool('stock', ...) 获取按股票维度的龙虎榜交易流向数据
            
            # 构建查询条件
            if stock_codes:
                stock_condition = ','.join(stock_codes)
            else:
                stock_condition = ''
            
            # 龙虎榜交易流向相关指标（按股票维度）
            indicators = [
                'ths_lhb_buy_amount_stock',      # 龙虎榜买入金额
                'ths_lhb_sell_amount_stock',     # 龙虎榜卖出金额
                'ths_lhb_net_buy_amount_stock',  # 龙虎榜净买入金额
                'ths_lhb_turnover_ratio_stock',  # 龙虎榜成交占比
                'ths_lhb_reason_stock'           # 上榜原因
            ]
            
            all_data = []
            
            # 按日期逐日获取数据
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            while current_date <= end_dt:
                date_str = current_date.strftime('%Y-%m-%d')
                
                try:
                    # 限流控制
                    self.rate_limiter.acquire()
                    
                    # 逐个尝试不同过滤器（提升兼容性）
                    filters_to_try = [
                        f'date:{date_str}',
                        f'date:{date_str};exchange:SSE',
                        f'date:{date_str};exchange:SZSE',
                    ]
                    # 兼容不带连字符格式
                    compact_date = current_date.strftime('%Y%m%d')
                    filters_to_try += [
                        f'date:{compact_date}',
                        f'date:{compact_date};exchange:SSE',
                        f'date:{compact_date};exchange:SZSE',
                    ]

                    got = False
                    for filt in filters_to_try:
                        # time 参数多种尝试：空/标准日期/紧凑日期
                        for t in ['', date_str, compact_date]:
                            try:
                                raw = self.THS.THS_DataPool(
                                    'stock',
                                    t,
                                    filt,
                                    'ths_stock_short_name_stock,ths_stock_code_stock,' + ','.join(indicators)
                                )
                                code, rows_data = self._parse_ths_result(raw)
                                rtype = type(raw).__name__
                                rows = len(rows_data)
                                logger.info(f"THS_DataPool(stock) {date_str} time='{t or 'EMPTY'}' filter='{filt}' => type={rtype}, code={code}, rows={rows}")
                                if code == 0 and rows > 0:
                                    daily_data = pd.DataFrame(rows_data)
                                    daily_data['trade_date'] = date_str
                                    all_data.append(daily_data)
                                    logger.info(f"获取{date_str}龙虎榜数据成功，{len(daily_data)}条记录 (time={t or 'EMPTY'}, filter={filt})")
                                    got = True
                                    break
                            except Exception as ie:
                                logger.warning(f"THS_DataPool 调用异常: time='{t or 'EMPTY'}', filter='{filt}', err={ie}")
                        if got:
                            break
                    if not got:
                        logger.warning(f"{date_str} 未从数据池获取到龙虎榜流向数据")
                    
                    # 添加延时避免请求过于频繁
                    time.sleep(0.2)  # 增加延时到200ms
                    
                except Exception as e:
                    logger.warning(f"获取{date_str}数据失败: {e}")
                
                current_date += timedelta(days=1)
            
            if all_data:
                df = pd.concat(all_data, ignore_index=True)
                logger.info(f"共获取龙虎榜数据 {len(df)} 条")
                return df
            else:
                logger.warning("未获取到龙虎榜数据，回退至 THS_DR + THS_BD 路径")
                # 回退：通过专题报表获取A股列表后，使用 THS_BD 批量提取 LHB 指标
                try:
                    fallback_df = self._fetch_lhb_via_bd(start_date, end_date, stock_codes)
                    if fallback_df is not None and not fallback_df.empty:
                        logger.info(f"回退路径共获取龙虎榜数据 {len(fallback_df)} 条")
                        return fallback_df
                except Exception as fe:
                    logger.error(f"回退路径失败: {fe}")
                return None
                
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return None

    def get_dragon_tiger_seat_data(self,
                                   start_date: str,
                                   end_date: str = None,
                                   stock_codes: List[str] = None) -> Optional[pd.DataFrame]:
        """
        获取龙虎榜席位明细数据（按股票+席位维度展开）

        尝试通过 THS_DataPool('stock') 获取席位相关列，并进行行展开。
        注：实际返回格式可能因权限/版本存在差异，已做尽量兼容的解析与兜底。

        Returns:
            DataFrame: 列包含 trade_date, ths_stock_code_stock, ths_stock_short_name_stock,
                       ths_lhb_seat_name_stock, ths_lhb_seat_type_stock,
                       ths_lhb_buy_amount_seat_stock, ths_lhb_sell_amount_seat_stock
        """
        if not self._ensure_login():
            return None

        if not end_date:
            end_date = start_date

        seat_cols = [
            'ths_lhb_seat_name_stock',
            'ths_lhb_seat_type_stock',
            'ths_lhb_buy_amount_seat_stock',
            'ths_lhb_sell_amount_seat_stock'
        ]

        all_seat_rows: List[Dict[str, Any]] = []

        try:
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            while current_date <= end_dt:
                date_str = current_date.strftime('%Y-%m-%d')
                try:
                    self.rate_limiter.acquire()
                    compact_date = current_date.strftime('%Y%m%d')
                    filters_to_try = [
                        f'date:{date_str}',
                        f'date:{date_str};exchange:SSE',
                        f'date:{date_str};exchange:SZSE',
                        f'date:{compact_date}',
                        f'date:{compact_date};exchange:SSE',
                        f'date:{compact_date};exchange:SZSE',
                    ]

                    got = False
                    for filt in filters_to_try:
                        for t in ['', date_str, compact_date]:
                            try:
                                raw = self.THS.THS_DataPool(
                                    'stock',
                                    t,
                                    filt,
                                    'ths_stock_short_name_stock,ths_stock_code_stock,' + ','.join(seat_cols)
                                )
                                code, rows_data = self._parse_ths_result(raw)
                                rtype = type(raw).__name__
                                rows = len(rows_data)
                                logger.info(f"THS_DataPool(stock-seat) {date_str} time='{t or 'EMPTY'}' filter='{filt}' => type={rtype}, code={code}, rows={rows}")
                                if code == 0 and rows > 0:
                                    daily_df = pd.DataFrame(rows_data)
                                    if daily_df.empty:
                                        break
                                    daily_df['trade_date'] = date_str
                                    # 逐行解析席位列
                                    for _, r in daily_df.iterrows():
                                        stock_code = r.get('ths_stock_code_stock')
                                        stock_name = r.get('ths_stock_short_name_stock')

                                        seat_name_v = r.get('ths_lhb_seat_name_stock')
                                        seat_type_v = r.get('ths_lhb_seat_type_stock')
                                        seat_buy_v = r.get('ths_lhb_buy_amount_seat_stock')
                                        seat_sell_v = r.get('ths_lhb_sell_amount_seat_stock')

                                        names = self._to_list(seat_name_v)
                                        types = self._to_list(seat_type_v)
                                        buys = self._to_list(seat_buy_v)
                                        sells = self._to_list(seat_sell_v)

                                        n = min(len(names), len(types), len(buys), len(sells))
                                        for i in range(n):
                                            all_seat_rows.append({
                                                'trade_date': date_str,
                                                'ths_stock_code_stock': stock_code,
                                                'ths_stock_short_name_stock': stock_name,
                                                'ths_lhb_seat_name_stock': names[i],
                                                'ths_lhb_seat_type_stock': types[i],
                                                'ths_lhb_buy_amount_seat_stock': self._to_float(buys[i]),
                                                'ths_lhb_sell_amount_seat_stock': self._to_float(sells[i]),
                                            })
                                    got = True
                                    break
                            except Exception as ie:
                                logger.warning(f"THS_DataPool 调用异常(席位): time='{t or 'EMPTY'}', filter='{filt}', err={ie}")
                        if got:
                            break
                    if not got:
                        logger.warning(f"{date_str} 未从数据池获取到席位明细数据")
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning(f"获取{date_str}席位数据失败: {e}")
                current_date += timedelta(days=1)

            if all_seat_rows:
                seat_df = pd.DataFrame(all_seat_rows)
                logger.info(f"共获取席位明细 {len(seat_df)} 条")
                return seat_df
            else:
                logger.info("未获取到席位明细数据，回退至 THS_DR + THS_BD 路径(席位)")
                try:
                    seat_df = self._fetch_lhb_seat_via_bd(start_date, end_date, stock_codes)
                    if seat_df is not None and not seat_df.empty:
                        logger.info(f"回退席位路径共获取席位明细 {len(seat_df)} 条")
                        return seat_df
                except Exception as fe:
                    logger.error(f"回退席位路径失败: {fe}")
                return None

        except Exception as e:
            logger.error(f"获取席位明细失败: {e}")
            return None

    @staticmethod
    def _to_list(value: Any) -> List[Any]:
        """将可能的席位字段值转换为列表，支持标量/分隔字符串/JSON字符串/列表。"""
        if value is None:
            return []
        # 已是列表
        if isinstance(value, list):
            return value
        # Pandas/Numpy 标量
        try:
            import numpy as np  # 仅用于类型判断
            if isinstance(value, (np.generic,)):
                value = value.item()
        except Exception:
            pass
        # JSON 字符串
        if isinstance(value, str):
            s = value.strip()
            if s.startswith('[') and s.endswith(']'):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            # 用常见分隔符切分
            for sep in ['|', ';', ',', '，', '、']:
                if sep in s:
                    parts = [p.strip() for p in s.split(sep) if p.strip() != '']
                    return parts
            # 单一字符串视为单元素列表
            return [s]
        # 其他标量
        return [value]

    @staticmethod
    def _to_float(v: Any) -> float:
        try:
            if v is None:
                return 0.0
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v).replace(',', '').strip()
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    # -------------------- 基于官方示例的 DR/BD 辅助方法 --------------------
    def _call_DR(self, report: str, funcpara: str, outpara: str) -> Optional[pd.DataFrame]:
        try:
            dr = getattr(self.THS, 'THS_DR', None)
            if dr is None:
                logger.warning('THS_DR 不可用')
                return None
            res = dr(report, funcpara, outpara)
            # 优先官方新对象：errorcode/data
            if hasattr(res, 'errorcode'):
                if getattr(res, 'errorcode', -1) != 0:
                    logger.warning(f"THS_DR 错误: {getattr(res, 'errmsg', '')}")
                    return None
                data = getattr(res, 'data', None)
                return data if isinstance(data, pd.DataFrame) else None
            # 其他形态解析
            code, rows = self._parse_ths_result(res)
            if code == 0 and rows:
                return pd.DataFrame(rows)
            return None
        except Exception as e:
            logger.error(f"THS_DR 调用失败: {e}")
            return None

    def _call_BD(self, codes: Union[str, List[str]], indicators: str, param: str) -> Optional[pd.DataFrame]:
        try:
            bd = getattr(self.THS, 'THS_BD', None)
            if bd is None:
                # 兼容早期接口名 THS_BasicData
                bd = getattr(self.THS, 'THS_BasicData', None)
            if bd is None:
                logger.warning('THS_BD/THS_BasicData 不可用')
                return None
            res = bd(codes, indicators, param)
            if hasattr(res, 'errorcode'):
                if getattr(res, 'errorcode', -1) != 0:
                    logger.debug(f"THS_BD 错误: {getattr(res, 'errmsg', '')} param={param}")
                    return None
                data = getattr(res, 'data', None)
                # 新接口：data 即 DataFrame
                if isinstance(data, pd.DataFrame) and not data.empty:
                    return data
                # 早期接口：tables -> 转DF
                try:
                    from iFinDPy import THS_Trans2DataFrame  # type: ignore
                    df = THS_Trans2DataFrame(res)
                    return df if isinstance(df, pd.DataFrame) and not df.empty else None
                except Exception:
                    pass
                return None
            # 其他形态解析
            code, rows = self._parse_ths_result(res)
            if code == 0 and rows:
                return pd.DataFrame(rows)
            return None
        except Exception as e:
            logger.debug(f"THS_BD 调用异常: {e} param={param}")
            return None

    def _get_all_a_share_codes(self, trade_date: str) -> Optional[List[str]]:
        # 使用 p03291 板块成分报表获取全A股代码（001005010）
        date_compact = datetime.strptime(trade_date, '%Y-%m-%d').strftime('%Y%m%d')
        funcpara = f"date={date_compact};blockname=001005010;iv_type=allcontract"
        outpara = "p03291_f001:Y,p03291_f002:Y,p03291_f003:Y,p03291_f004:Y"
        df = self._call_DR("p03291", funcpara, outpara)
        if df is None or df.empty:
            logger.warning('未能通过 THS_DR 获取A股代码')
            return None
        # 官方示例：p03291_f002 为代码列
        code_col = 'p03291_f002'
        if code_col not in df.columns:
            logger.warning(f'THS_DR 返回缺少列 {code_col}，实际列: {list(df.columns)}')
            return None
        codes = df[code_col].dropna().astype(str).tolist()
        logger.info(f"THS_DR 获取到A股代码数: {len(codes)}")
        return codes

    def _bd_try_params(self, codes: List[str], indicators: str, date_str: str, batch_size: int = 200) -> Optional[pd.DataFrame]:
        # 尝试多种参数风格
        param_candidates = [
            f"{date_str},100",  # 官方示例风格
            date_str,
            datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d') + ",100",
            datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d'),
        ]
        all_parts = []
        for param in param_candidates:
            all_parts.clear()
            for i in range(0, len(codes), batch_size):
                sub = codes[i:i+batch_size]
                df = self._call_BD(sub, indicators, param)
                if df is not None and not df.empty:
                    all_parts.append(df)
                time.sleep(0.1)
            if all_parts:
                return pd.concat(all_parts, ignore_index=True)
        return None

    def _fetch_lhb_via_bd(self, start_date: str, end_date: Optional[str], stock_codes: Optional[List[str]]) -> Optional[pd.DataFrame]:
        # 仅按日抓取（与上游一致）
        date_str = start_date
        codes = stock_codes or self._get_all_a_share_codes(date_str)
        if not codes:
            return None
        # LHB 流向指标集合（按股票）
        indicators = 'ths_lhb_buy_amount_stock,ths_lhb_sell_amount_stock,ths_lhb_net_buy_amount_stock,ths_lhb_turnover_ratio_stock,ths_lhb_reason_stock'
        df = self._bd_try_params(codes, indicators, date_str)
        if df is None or df.empty:
            logger.info('THS_BD 流向回退无数据')
            return None
        # 统一代码/名称列名
        if 'thscode' in df.columns and 'ths_stock_code_stock' not in df.columns:
            df = df.rename(columns={'thscode': 'ths_stock_code_stock'})
        if 'secName' in df.columns and 'ths_stock_short_name_stock' not in df.columns:
            df = df.rename(columns={'secName': 'ths_stock_short_name_stock'})
        df['trade_date'] = date_str
        return df

    def _fetch_lhb_seat_via_bd(self, start_date: str, end_date: Optional[str], stock_codes: Optional[List[str]]) -> Optional[pd.DataFrame]:
        date_str = start_date
        codes = stock_codes or self._get_all_a_share_codes(date_str)
        if not codes:
            return None
        # 席位指标集合（按股票）
        indicators = 'ths_lhb_seat_name_stock,ths_lhb_seat_type_stock,ths_lhb_buy_amount_seat_stock,ths_lhb_sell_amount_seat_stock'
        df = self._bd_try_params(codes, indicators, date_str)
        if df is None or df.empty:
            logger.info('THS_BD 席位回退无数据')
            return None
        if 'thscode' in df.columns and 'ths_stock_code_stock' not in df.columns:
            df = df.rename(columns={'thscode': 'ths_stock_code_stock'})
        if 'secName' in df.columns and 'ths_stock_short_name_stock' not in df.columns:
            df = df.rename(columns={'secName': 'ths_stock_short_name_stock'})
        df['trade_date'] = date_str
        return df
    
    def get_daily_data(self, 
                       stock_codes: List[str],
                       start_date: str,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取股票日线数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD，默认为今天
            
        Returns:
            DataFrame: 日线数据
        """
        if not self._ensure_login():
            return None
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 使用THS_HistoryQuotes获取历史行情数据（兼容多返回形态、多jsonparam参数）
            indicators = [
                'open',           # 开盘价
                'high',           # 最高价  
                'low',            # 最低价
                'close',          # 收盘价
                'volume',         # 成交量
                'amount',         # 成交额
                'turn',           # 换手率
                'pctChg',         # 涨跌幅
                'avgPrice',       # 均价
                'pe_ttm',         # 市盈率TTM
                'pb',             # 市净率
                'total_mv'        # 总市值
            ]

            def _call_hq_one(code: str, s_date: str, e_date: str) -> Optional[pd.DataFrame]:
                try:
                    hq = getattr(self.THS, 'THS_HistoryQuotes', None)
                    if hq is None:
                        logger.error('THS_HistoryQuotes 不可用')
                        return None
                    jsonparam_candidates = ['', 'Fill:Blank', 'period:D,Fill:Blank', 'format:json', 'period:D']
                    # 日期两种格式轮询
                    try:
                        start_compact = datetime.strptime(s_date, '%Y-%m-%d').strftime('%Y%m%d')
                        end_compact = datetime.strptime(e_date, '%Y-%m-%d').strftime('%Y%m%d') if e_date else start_compact
                    except Exception:
                        start_compact, end_compact = s_date, (e_date or s_date)
                    date_pairs = [
                        (s_date, e_date),
                        (start_compact, end_compact),
                    ]
                    for jp in jsonparam_candidates:
                        try:
                            # 轮询不同日期格式
                            got = None
                            for sd, ed in date_pairs:
                                raw = hq(code, ','.join(indicators), jp, sd, ed)
                                # 新版对象：errorcode/data
                                if hasattr(raw, 'errorcode'):
                                    if getattr(raw, 'errorcode', -1) != 0:
                                        continue
                                    data = getattr(raw, 'data', None)
                                    if isinstance(data, pd.DataFrame) and not data.empty:
                                        return data
                                    # 早期对象：使用 THS_Trans2DataFrame
                                    try:
                                        from iFinDPy import THS_Trans2DataFrame  # type: ignore
                                        df = THS_Trans2DataFrame(raw)
                                        if isinstance(df, pd.DataFrame) and not df.empty:
                                            return df
                                    except Exception:
                                        pass
                                    continue
                                # 其他形态：使用通用解析器
                                code0, rows = self._parse_ths_result(raw)
                                if code0 == 0 and rows:
                                    return pd.DataFrame(rows)
                        except Exception:
                            continue
                    return None
                except Exception as ie:
                    logger.warning(f"THS_HistoryQuotes 调用异常: {ie}")
                    return None

            all_data = []

            # 将长区间切片（按年）以避免长时间阻塞
            def _slice_years(s: str, e: str) -> List[tuple]:
                slices = []
                s_dt = datetime.strptime(s, '%Y-%m-%d')
                e_dt = datetime.strptime(e, '%Y-%m-%d')
                cur_start = s_dt
                while cur_start <= e_dt:
                    cur_end = min(datetime(cur_start.year, 12, 31), e_dt)
                    slices.append((cur_start.strftime('%Y-%m-%d'), cur_end.strftime('%Y-%m-%d')))
                    cur_start = cur_end + timedelta(days=1)
                return slices

            # 分批处理股票代码，避免单次请求过多
            batch_size = 10  # 再降低批次，减压
            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i + batch_size]

                for code in batch_codes:
                    code_frames = []
                    for s_seg, e_seg in _slice_years(start_date, end_date):
                        # 限流控制
                        self.rate_limiter.acquire()
                        seg_df = _call_hq_one(code, s_seg, e_seg)
                        if seg_df is not None and not seg_df.empty:
                            # 归一化至一行一时点
                            seg_df = self._normalize_history_df(seg_df)
                            code_frames.append(seg_df)
                        else:
                            logger.debug(f"{code} 无数据片段 {s_seg}~{e_seg}")
                        time.sleep(self.call_interval)
                    if code_frames:
                        df_one = pd.concat(code_frames, ignore_index=True)
                        if 'stock_code' not in df_one.columns:
                            df_one['stock_code'] = code
                        all_data.append(df_one)
                        logger.info(f"获取{code}区间日线成功: {len(df_one)} 行")
                    else:
                        logger.warning(f"获取{code}日线数据失败（所有片段空）")

                logger.info(f"完成第{i//batch_size + 1}批股票数据获取")
                if i + batch_size < len(stock_codes):
                    time.sleep(self.batch_interval)

            if all_data:
                df = pd.concat(all_data, ignore_index=True)
                df = self._align_history_columns(df)
                logger.info(f"共获取日线数据 {len(df)} 条，列: {list(df.columns)}")
                return df
            else:
                logger.warning("未获取到日线数据")
                return None

        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            return None
    
    def get_stock_list(self, market: str = 'all') -> Optional[List[str]]:
        """
        获取股票代码列表
        
        Args:
            market: 市场类型 'all'/'sz'/'sh'
        
        Returns:
            List[str]: 股票代码列表
        """
        if not self._ensure_login():
            return None
        try:
            # 优先走官方 DR 报表：全A股 001005010
            if market == 'all':
                codes = self._get_all_a_share_codes(datetime.now().strftime('%Y-%m-%d'))
                if codes:
                    return codes
                # 回退到 DataPool
            # 使用 DataPool 回退（分市场可选）
            condition = 'date:' + datetime.now().strftime('%Y-%m-%d')
            if market == 'sz':
                condition += ';exchange:SZSE'
            elif market == 'sh':
                condition += ';exchange:SSE'
            self.rate_limiter.acquire()
            raw = self.THS.THS_DataPool('stock', datetime.now().strftime('%Y-%m-%d'), condition, 'ths_stock_code_stock')
            code, rows = self._parse_ths_result(raw)
            if code == 0 and rows:
                df = pd.DataFrame(rows)
                if 'ths_stock_code_stock' in df.columns:
                    stock_codes = df['ths_stock_code_stock'].dropna().astype(str).tolist()
                    logger.info(f"获取股票列表成功，共{len(stock_codes)}只股票")
                    return stock_codes
            logger.error("获取股票列表失败")
            return None
        except Exception as e:
            logger.error(f"获取股票列表异常: {e}")
            return None
    
    def __del__(self):
        """析构函数，确保登出"""
        self.logout()

# 全局客户端实例
_ths_client = None

def get_tonghuashun_client() -> TonghuasunDataClient:
    """获取同花顺客户端实例（单例模式）"""
    global _ths_client
    if _ths_client is None:
        _ths_client = TonghuasunDataClient()
    return _ths_client
