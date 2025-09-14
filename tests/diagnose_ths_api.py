#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺 LHB 诊断脚本：
1) 打印 THS_DataPool 返回的类型/码/行数（多种 time/filter 组合）
2) 用 THS_BasicData 针对单只股票+日期探测 LHB 指标是否可取
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_service.tonghuashun_client import get_tonghuashun_client


def probe_datapool(date_str: str):
    client = get_tonghuashun_client()
    if not client._ensure_login():
        print('登录失败')
        return

    THS = client.THS
    compact_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')
    filters = [
        f'date:{date_str}',
        f'date:{date_str};exchange:SSE',
        f'date:{date_str};exchange:SZSE',
        f'date:{compact_date}',
        f'date:{compact_date};exchange:SSE',
        f'date:{compact_date};exchange:SZSE',
    ]
    fields = 'ths_stock_short_name_stock,ths_stock_code_stock,' + ','.join([
        'ths_lhb_buy_amount_stock',
        'ths_lhb_sell_amount_stock',
        'ths_lhb_net_buy_amount_stock',
        'ths_lhb_turnover_ratio_stock',
        'ths_lhb_reason_stock',
    ])

    print('\n==== THS_DataPool(stock) 探测 ====')
    for t in ['', date_str, compact_date]:
        for filt in filters:
            try:
                raw = THS.THS_DataPool('stock', t, filt, fields)
                rtype = type(raw).__name__
                code, rows_data = client._parse_ths_result(raw)
                rows = len(rows_data)
                print(f"time='{t or 'EMPTY'}', filter='{filt}' => type={rtype}, code={code}, rows={rows}")
                if code is None and rows == 0:
                    try:
                        import json
                        if isinstance(raw, (dict,)):
                            print('raw.keys:', list(raw.keys()))
                        elif isinstance(raw, (bytes, bytearray)):
                            txt = raw.decode('utf-8', errors='ignore')
                            print('raw(bytes) preview:', txt[:300])
                        elif isinstance(raw, str):
                            print('raw(str) preview:', raw[:300])
                    except Exception:
                        pass
                if code == 0 and rows > 0:
                    print('Sample row:', rows_data[0])
                    return
            except Exception as e:
                print(f"EXC: time='{t or 'EMPTY'}', filter='{filt}', err={e}")


def probe_basicdata(date_str: str):
    client = get_tonghuashun_client()
    if not client._ensure_login():
        print('登录失败')
        return

    THS = client.THS
    codes = ['000001.SZ', '600000.SH', '300750.SZ']
    inds = ','.join([
        'ths_lhb_buy_amount_stock',
        'ths_lhb_sell_amount_stock',
        'ths_lhb_net_buy_amount_stock',
        'ths_lhb_turnover_ratio_stock',
        'ths_lhb_reason_stock',
    ])
    jp = f'date:{date_str}'

    print('\n==== THS_BasicData 探测 ====')
    for code in codes:
        try:
            raw = THS.THS_BasicData(code, inds, jp)
            rtype = type(raw).__name__
            code0, rows_data = client._parse_ths_result(raw)
            rows = len(rows_data)
            print(f"BasicData {code} => type={rtype}, code={code0}, rows={rows}")
            if code0 is None and rows == 0:
                try:
                    if isinstance(raw, (dict,)):
                        print('raw.keys:', list(raw.keys()))
                except Exception:
                    pass
            if code0 == 0 and rows > 0:
                print('Sample row:', rows_data[0])
        except Exception as e:
            print(f"EXC BasicData {code}: {e}")


def main():
    # 默认用近一个交易日；可在命令行传入 YYYY-MM-DD
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    print('诊断日期:', date_str)
    probe_datapool(date_str)
    probe_basicdata(date_str)
    # 额外：基于官方示例的 DR/BD 路径探测
    try:
        client = get_tonghuashun_client()
        if client._ensure_login():
            print('\n==== THS_DR + THS_BD 探测 ====')
            codes = client._get_all_a_share_codes(date_str) or []
            print('A股代码数:', len(codes))
            if codes:
                sample = codes[:50]
                df_flow = client._call_BD(sample, 'ths_lhb_buy_amount_stock,ths_lhb_sell_amount_stock,ths_lhb_net_buy_amount_stock,ths_lhb_turnover_ratio_stock,ths_lhb_reason_stock', f'{date_str},100')
                print('BD-flow rows:', 0 if df_flow is None else len(df_flow))
                df_seat = client._call_BD(sample, 'ths_lhb_seat_name_stock,ths_lhb_seat_type_stock,ths_lhb_buy_amount_seat_stock,ths_lhb_sell_amount_seat_stock', f'{date_str},100')
                print('BD-seat rows:', 0 if df_seat is None else len(df_seat))
    except Exception as e:
        print('DR/BD 探测异常:', e)


if __name__ == '__main__':
    main()
