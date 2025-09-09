#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线单元测试：验证席位明细解析与清洗（不依赖 iFinD / 网络）
"""

import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_service.data_sync import DataSynchronizer


def build_mock_seat_df():
    # 模拟一行包含多席位，使用“|”分隔
    return pd.DataFrame([
        {
            'ths_stock_code_stock': '000001.SZ',
            'ths_stock_short_name_stock': '平安银行',
            'ths_lhb_seat_name_stock': '机构专用|华泰深圳益田路|银河上海长宁',
            'ths_lhb_seat_type_stock': '机构|游资|游资',
            'ths_lhb_buy_amount_seat_stock': '1200000|800000|500000',
            'ths_lhb_sell_amount_seat_stock': '600000|200000|100000',
            'trade_date': '2025-09-05',
        }
    ])


def main():
    sync = DataSynchronizer()
    raw = build_mock_seat_df()
    print('原始席位数据列:', list(raw.columns))
    seat_df = sync.transform_data(raw, 'seat_daily')
    print('转换后 seat_daily 列:', list(seat_df.columns))
    print(seat_df)
    assert 'seat_name' in seat_df.columns and len(seat_df) >= 1, 'seat_daily 转换失败'
    print('席位离线转换验证完成 ✅')


if __name__ == '__main__':
    main()

