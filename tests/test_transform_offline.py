#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线单元测试：验证龙虎榜数据映射与清洗逻辑（不依赖 iFinD / 网络）
"""

import pandas as pd
import os
import sys

# 让脚本可直接从仓库根目录运行
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_service.data_sync import DataSynchronizer


def build_mock_trade_flow_df():
    """构造模拟的 THS_DataPool('stock') 返回数据（交易流向维度）。"""
    data = [
        {
            'ths_stock_code_stock': '000001.SZ',
            'ths_stock_short_name_stock': '平安银行',
            'ths_lhb_buy_amount_stock': 1200000.0,
            'ths_lhb_sell_amount_stock': 800000.0,
            'ths_lhb_net_buy_amount_stock': 400000.0,
            'ths_lhb_turnover_ratio_stock': 0.12,
            'ths_lhb_reason_stock': '日涨幅偏离值达7%的证券',
            'trade_date': '2025-09-05',
        },
        {
            'ths_stock_code_stock': '000002.SZ',
            'ths_stock_short_name_stock': '万 科Ａ',
            'ths_lhb_buy_amount_stock': 500000.0,
            'ths_lhb_sell_amount_stock': 600000.0,
            'ths_lhb_net_buy_amount_stock': -100000.0,
            'ths_lhb_turnover_ratio_stock': 0.08,
            'ths_lhb_reason_stock': '日价格振幅达到15%的前五只证券',
            'trade_date': '2025-09-05',
        },
    ]
    return pd.DataFrame(data)


def main():
    sync = DataSynchronizer()

    df = build_mock_trade_flow_df()
    print('原始模拟数据列:', list(df.columns))

    # 转换为 trade_flow 表结构
    flow_df = sync.transform_data(df, 'trade_flow')
    print('转换后 trade_flow 列:', list(flow_df.columns))
    print(flow_df.head())

    # seat_daily 转换应被安全处理（因无 seat 字段）且不会抛错
    seat_df = sync.transform_data(df, 'seat_daily')
    print('转换后 seat_daily 列(可能仅有基础列):', list(seat_df.columns))
    print(seat_df.head())

    # 清洗行为校验：不应出现异常
    assert 'code' in flow_df.columns and 'trade_date' in flow_df.columns, 'trade_flow 关键列缺失'
    assert all(col in flow_df.columns for col in ['lhb_buy', 'lhb_sell', 'lhb_net_buy']), 'trade_flow 金额列缺失'

    # 对 seat_daily，由于没有 seat_name，应不用于写入，但 transform/clean 不应报错
    # 此处仅验证不会抛异常
    print('离线转换验证完成 ✅')


if __name__ == '__main__':
    main()

