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
        self.is_logged_in = False
        self.user_id = user_id or os.getenv("THS_USER_ID")
        self.password = password or os.getenv("THS_PASSWORD")
        
        # 初始化限流器 - 每分钟最多30个请求
        self.rate_limiter = RateLimiter(max_requests=30, time_window=60)
        
        self._initialize_client()
    
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
            if result == 0:
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
            return self.login()
        return True
    
    def get_dragon_tiger_data(self, 
                             start_date: str, 
                             end_date: str = None,
                             stock_codes: List[str] = None) -> Optional[pd.DataFrame]:
        """
        获取龙虎榜数据
        
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
            # 使用THS_DataPool获取龙虎榜数据
            # 参考API文档中的数据池查询功能
            
            # 构建查询条件
            if stock_codes:
                stock_condition = ','.join(stock_codes)
            else:
                stock_condition = ''
            
            # 龙虎榜相关指标
            indicators = [
                'ths_lhb_buy_amount_stock',      # 龙虎榜买入金额
                'ths_lhb_sell_amount_stock',     # 龙虎榜卖出金额
                'ths_lhb_net_buy_amount_stock',  # 龙虎榜净买入金额
                'ths_lhb_turnover_ratio_stock',  # 龙虎榜成交占比
                'ths_lhb_reason_stock'           # 上榜原因
            ]
            
            # 席位相关数据
            seat_indicators = [
                'ths_lhb_seat_name_stock',       # 席位名称
                'ths_lhb_seat_type_stock',       # 席位类型
                'ths_lhb_buy_amount_seat_stock', # 席位买入金额
                'ths_lhb_sell_amount_seat_stock' # 席位卖出金额
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
                    
                    # 获取龙虎榜股票列表
                    result = self.THS.THS_DataPool(
                        'block',
                        date_str,
                        'date:' + date_str,
                        'ths_stock_short_name_stock,ths_stock_code_stock,' + ','.join(indicators)
                    )
                    
                    if result[0] == 0 and result[1] is not None:
                        daily_data = pd.DataFrame(result[1])
                        daily_data['trade_date'] = date_str
                        all_data.append(daily_data)
                        logger.info(f"获取{date_str}龙虎榜数据成功，{len(daily_data)}条记录")
                    
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
                logger.warning("未获取到龙虎榜数据")
                return None
                
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return None
    
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
            # 使用THS_HistoryQuotes获取历史行情数据
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
            
            all_data = []
            
            # 分批处理股票代码，避免单次请求过多
            batch_size = 20  # 减小批次大小，降低服务器压力
            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i + batch_size]
                
                for code in batch_codes:
                    try:
                        # 限流控制
                        self.rate_limiter.acquire()
                        
                        result = self.THS.THS_HistoryQuotes(
                            code,
                            ','.join(indicators),
                            '',  # jsonparam parameter
                            start_date,
                            end_date
                        )
                        
                        if result[0] == 0 and result[1] is not None:
                            stock_data = pd.DataFrame(result[1])
                            stock_data['stock_code'] = code
                            all_data.append(stock_data)
                            logger.debug(f"获取{code}日线数据成功")
                        
                        # 添加延时避免请求过于频繁  
                        time.sleep(0.1)  # 增加延时到100ms
                        
                    except Exception as e:
                        logger.warning(f"获取{code}日线数据失败: {e}")
                
                logger.info(f"完成第{i//batch_size + 1}批股票数据获取")
                
                # 批次间额外延时，避免连续高频请求
                if i + batch_size < len(stock_codes):
                    time.sleep(2)  # 批次间间隔2秒
            
            if all_data:
                df = pd.concat(all_data, ignore_index=True)
                logger.info(f"共获取日线数据 {len(df)} 条")
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
            # 使用THS_DataPool获取股票列表
            if market == 'all':
                condition = 'date:' + datetime.now().strftime('%Y-%m-%d')
            elif market == 'sz':
                condition = 'date:' + datetime.now().strftime('%Y-%m-%d') + ';exchange:SZSE'
            elif market == 'sh':
                condition = 'date:' + datetime.now().strftime('%Y-%m-%d') + ';exchange:SSE'
            else:
                condition = 'date:' + datetime.now().strftime('%Y-%m-%d')
            
            # 限流控制
            self.rate_limiter.acquire()
            
            result = self.THS.THS_DataPool(
                'stock',
                datetime.now().strftime('%Y-%m-%d'),
                condition,
                'ths_stock_code_stock'
            )
            
            if result[0] == 0 and result[1] is not None:
                df = pd.DataFrame(result[1])
                stock_codes = df['ths_stock_code_stock'].tolist()
                logger.info(f"获取股票列表成功，共{len(stock_codes)}只股票")
                return stock_codes
            else:
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