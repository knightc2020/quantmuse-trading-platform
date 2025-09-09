# -*- coding: utf-8 -*-

from iFinDPy import *
from datetime import datetime
import pandas as pd
import time as _time
import json
from threading import Thread,Lock,Semaphore
import requests

sem = Semaphore(5)  # 此变量用于控制最大并发数

# 登录函数
def thslogindemo():
    # 输入用户的帐号和密码
    thsLogin = THS_iFinDLogin("接口账号","接口密码")
    print(thsLogin)
    if thsLogin in {0, -201}:
        print('登录成功')
    else:
        print('登录失败')

def datepool_basicdata_demo():
    # 通过专题报表函数的板块成分报表和基础数据函数，提取全部A股在2025-05-14日的日不复权收盘价
    data_codes = THS_DR("p03291","date=20250514;blockname=001005010;iv_type=allcontract","p03291_f001:Y,p03291_f002:Y,p03291_f003:Y,p03291_f004:Y")
    if data_codes.errorcode != 0:
        print('error:{}'.format(data_codes.errmsg))
    else:
        seccode_codes_list = data_codes.data['p03291_f002'].tolist()
        data_result = THS_BD(seccode_codes_list, 'ths_close_price_stock', '2025-05-14,100')
        if data_result.errorcode != 0:
            print('error:{}'.format(data_result.errmsg))
        else:
            data_df = data_result.data
            print(data_df)

def datapool_realtime_demo():
    # 通过板块成分报表和实时行情函数，提取上证50的全部股票的最新价数据,并将其导出为csv文件
    today_str = datetime.today().strftime('%Y%m%d')
    print('today:{}'.format(today_str))
    data_sz50 = THS_DR("p03291","date="+today_str+";blockname=001005260;iv_type=allcontract","p03291_f001:Y,p03291_f002:Y,p03291_f003:Y,p03291_f004:Y")
    if data_sz50.errorcode != 0:
        print('error:{}'.format(data_sz50.errmsg))
    else:
        seccode_sz50_list = data_sz50.data['p03291_f002'].tolist()
        data_result = THS_RQ(seccode_sz50_list,'latest')
        if data_result.errorcode != 0:
            print('error:{}'.format(data_result.errmsg))
        else:
            data_df = data_result.data
            print(data_df)
            data_df.to_csv('realtimedata_{}.csv'.format(today_str))

def iwencai_demo():
    # 演示如何通过不消耗流量的自然语言语句调用常用数据
    print('输出资金流向数据')
    data_wencai_zjlx = THS_WC('主力资金流向', 'stock')
    if data_wencai_zjlx.errorcode != 0:
        print('error:{}'.format(data_wencai_zjlx.errmsg))
    else:
        print(data_wencai_zjlx.data)

    print('输出股性评分数据')
    data_wencai_xny = THS_WC('股性评分', 'stock')
    if data_wencai_xny.errorcode != 0:
        print('error:{}'.format(data_wencai_xny.errmsg))
    else:
        print(data_wencai_xny.data)

def work(codestr,lock,indilist):
    sem.acquire()
    stockdata = THS_HF(codestr, ';'.join(indilist),'','2025-05-14 09:15:00', '2025-05-14 15:30:00','format:json')
    if stockdata.errorcode != 0:
        print('error:{}'.format(stockdata.errmsg))
        sem.release()
    else:
        print(stockdata.data)
        lock.acquire()
        with open('test1.txt', 'a') as f:
            f.write(str(stockdata.data) + '\n')
        lock.release()
        sem.release()

def multiThread_demo():
    # 本函数为通过高频序列函数,演示如何使用多线程加速数据提取的示例,本例中通过将所有A股分100组,最大线程数量sem进行提取
    # 用户可以根据自身场景进行修改
    today_str = datetime.today().strftime('%Y%m%d')
    print('today:{}'.format(today_str))
    data_alla = THS_DR("p03291","date="+today_str+";blockname=001005010;iv_type=allcontract","p03291_f001:Y,p03291_f002:Y,p03291_f003:Y,p03291_f004:Y")
    if data_alla.errorcode != 0:
        print('error:{}'.format(data_alla.errmsg))
    else:
        stock_list = data_alla.data['p03291_f002'].tolist()

    indi_list = ['close', 'high', 'low', 'volume']
    lock = Lock()

    btime = datetime.now()
    l = []
    for eachlist in [stock_list[i:i + int(len(stock_list) / 10)] for i in
                     range(0, len(stock_list), int(len(stock_list) / 10))]:
        nowstr = ','.join(eachlist)
        p = Thread(target=work, args=(nowstr, lock, indi_list))
        l.append(p)

    for p in l:
        p.start()
    for p in l:
        p.join()
    etime = datetime.now()
    print(etime-btime)

pd.options.display.width = 320
pd.options.display.max_columns = None


def reportDownload():
    df = THS_ReportQuery('300033.SZ','beginrDate:2021-08-01;endrDate:2021-08-31;reportType:901','reportDate:Y,thscode:Y,secName:Y,ctime:Y,reportTitle:Y,pdfURL:Y,seq:Y').data
    print(df)
    for i in range(len(df)):
        pdfName = df.iloc[i,4]+str(df.iloc[i,6])+'.pdf'
        pdfURL = df.iloc[i,5]
        r = requests.get(pdfURL)
        with open(pdfName,'wb+') as f:
            f.write(r.content)


def main():
    # 本脚本为数据接口通用场景的实例,可以通过取消注释下列示例函数来观察效果

    # 登录函数
    thslogindemo()
    # 通过专题报表的板块成分函数和基础数据函数，提取全部A股的全部股票在2025-05-14日的日不复权收盘价
    datepool_basicdata_demo()
    #通过专题报表的板块成分函数和实时行情函数，提取上证50的全部股票的最新价数据,并将其导出为csv文件
    # datapool_realtime_demo()
    # 演示如何通过不消耗流量的自然语言语句调用常用数据
    # iwencai_demo()
    # 本函数为通过高频序列函数,演示如何使用多线程加速数据提取的示例,本例中通过将所有A股分100组,最大线程数量sem进行提取
    # multiThread_demo()
    # 本函数演示如何使用公告函数提取满足条件的公告，并下载其pdf
    # reportDownload()

if __name__ == '__main__':
    main()
时点数据应用示例（试用版正式版适用）
简介
演示如何提取财务指标的时点数据、如何利用辅助功能更好的处理时点数据的应用场景、如何在日期序列中根据自定义日期序列提取数据。

示例代码
python
from iFinDPy import *
import pandas as pd

pd.options.display.max_columns = None
pd.set_option('display.float_format', lambda x: '%.4f' % x)


loginResult = THS_iFinDLogin('zhanghao','mima')
print(loginResult)

def historyReportDateTest():
    # 提取股票不同日期的财报数据，避免回测财务模型受未来数据干扰
    dateList = THS_DateQuery('SSE','dateType:0,period:D,dateFormat:0','2019-10-20','2019-10-30')['tables']['time']
    for date in dateList:
        result = THS_BD('300029.SZ', 'ths_np_atoopc_pit_stock', '{},20190930,1'.format(date))
        print(date,result.data)

    # 使用日期序列函数来实现同样效果
    result = THS_DS('300029.SZ', 'ths_np_atoopc_pit_stock', '20190930,1', 'Fill:Blank', '2019-10-20', '2019-10-30')
    print(result.data)

def reportChange():
    # 使用财报变更日期指标和自定义日期序列函数提取股票的财报变更记录
    result = THS_BD('000892.SZ', 'ths_report_changedate_pit_stock', '2018-12-31,2020-11-25,604,1,20171231')
    changeDateList = result.data.iloc[0]['ths_report_changedate_pit_stock']
    print(changeDateList)

    changeRecord = THS_DS('000892.SZ', 'ths_total_assets_pit_stock', '20181231,1', 'date_sequence:{}'.format(changeDateList), '', '').data
    print(changeRecord)

def calepsttm(x):
    curDate = x['time']
    reportDateNow = x['ths_history_reportdate_pit_stock']
    year = int(reportDateNow[:4])
    datestr = reportDateNow[-4:]
    reportDateLast12 = str(year-1)+'1231'
    reportDateLastEnd = str(year-1)+datestr
    if datestr == '1231':
        np_ttm = THS_BD('300029.SZ','ths_np_atoopc_pit_stock','{},{},1'.format(curDate,reportDateNow)).data.iloc[0]['ths_np_atoopc_pit_stock']
    else:
        npThisYear = THS_BD('300029.SZ','ths_np_atoopc_pit_stock','{},{},1'.format(curDate,reportDateNow)).data.iloc[0]['ths_np_atoopc_pit_stock']
        npLastYear1 = THS_BD('300029.SZ', 'ths_np_atoopc_pit_stock', '{},{},1'.format(curDate, reportDateLast12)).data.iloc[0]['ths_np_atoopc_pit_stock']
        npLastYear2 = THS_BD('300029.SZ', 'ths_np_atoopc_pit_stock', '{},{},1'.format(curDate, reportDateLastEnd)).data.iloc[0]['ths_np_atoopc_pit_stock']
        np_ttm = npThisYear + npLastYear1 - npLastYear2
    shareNum = THS_BD('300029.SZ','ths_total_shares_stock',curDate).data.iloc[0]['ths_total_shares_stock']
    epsttm = np_ttm/shareNum
    return epsttm


def epsttm():
    # 当前ttm的提取
    result_before = THS_DS('300029.SZ', 'ths_eps_ttm_stock', '101', 'Fill:Blank', '2019-10-20', '2019-10-30')
    if result_before.errorcode != 0:
        print('error {} happen'.format(result_before.errmsg))
    else:
        print(result_before.data)
    # 使用新的时点数据自行计算ttm
    result_after = THS_DS('300029.SZ','ths_history_reportdate_pit_stock','608,1,0@104,2','Fill:Blank','2019-10-20','2019-10-30')
    if result_after.errorcode != 0:
        print('error {} happen'.format(result_after.errmsg))
    else:
        result_df = result_after.data
        result_df['epsttm'] = result_df.apply(calepsttm,axis=1)
        print(result_df)

def exceed100test():
    dateList = THS_DateQuery('SSE', 'dateType:0,period:D,dateFormat:0', '2018-10-20', '2019-10-30')['tables']['time']
    changeRecord = THS_DS('000892.SZ', 'ths_np_atoopc_pit_stock', '20171231,1',
                          'date_sequence:{}'.format(','.join(dateList)), '', '')
    print(changeRecord)

def duplicatedatetest():
    # 自定义序列函数支持不同的日期格式
    changeRecord = THS_DS('000892.SZ', 'ths_np_atoopc_pit_stock', '20171231,1',
                          'date_sequence:2018-05-01,20200601,2020-08-01', '', '')
    print(changeRecord)

def main():
    historyReportDateTest()
    # reportChange()
    # epsttm()
    # exceed100test()
    # duplicatedatetest()

if __name__ == '__main__':
    main()
大跌后指数表现情况案例
简介
分析股市大跌5%之后一个月，一个季度和一年后的数据表现。

示例代码
python
import pandas as pd
from datetime import datetime
from iFinDPy import *


thsLogin = THS_iFinDLogin("iFind账号","iFind账号密码")

index_list = ['000001.SH','399001.SZ','399006.SZ']
result = pd.DataFrame()
today =datetime.today().strftime('%Y-%m-%d')

for index in index_list: 
    data_js = THS_DateSerial(index,'ths_pre_close_index;ths_open_price_index;ths_close_price_index;ths_high_price_index',';;;',\
                             'Days:Tradedays,Fill:Previous,Interval:D,block:history','2000-01-01',today,True)
    data_df = THS_Trans2DataFrame(data_js)
    data_df['close_chg'] = data_df['ths_close_price_index'] / data_df['ths_pre_close_index'] * 100 - 100
    result_pd = data_df[(data_df['close_chg'] < -5)]
    date_list = result_pd['time'].tolist()
    print('{}收盘在-5%的交易日有{}'.format(index,str(date_list)))
    for date in date_list:
        date_after_1month = THS_DateOffset('SSE','dateType:1,period:D,offset:30,dateFormat:0,output:singledate',date)['tables']['time'][0]
        date_after_3month = THS_DateOffset('SSE','dateType:1,period:D,offset:90,dateFormat:0,output:singledate',date)['tables']['time'][0]
        date_after_1year = THS_DateOffset('SSE','dateType:1,period:D,offset:365,dateFormat:0,output:singledate',date)['tables']['time'][0]
        if date > (datetime.today() + timedelta(days=-365)).strftime('%Y-%m-%d'):
            continue
        index_close_date = THS_BasicData(index,'ths_close_price_index',date)['tables'][0]['table']['ths_close_price_index'][0]
        index_close_date_after_1month = THS_BasicData(index,'ths_close_price_index',date_after_1month)['tables'][0]['table']['ths_close_price_index'][0]
        index_close_date_after_3month = THS_BasicData(index,'ths_close_price_index',date_after_3month)['tables'][0]['table']['ths_close_price_index'][0]
        index_close_date_after_1year = THS_BasicData(index,'ths_close_price_index',date_after_1year)['tables'][0]['table']['ths_close_price_index'][0]
        result = result.append(pd.DataFrame([index,date,index_close_date,index_close_date_after_1month,index_close_date_after_3month,index_close_date_after_1year]).T)
result.columns = ['指数代码','大跌日','大跌日点数','一个月后点数','三个月后点数','一年后点数']
result = result.set_index('指数代码')
result['大跌一个月后涨跌幅'] = result['一个月后点数']/result['大跌日点数'] *100 -100
result['大跌三个月后涨跌幅'] = result['三个月后点数']/result['大跌日点数'] *100 -100
result['大跌一年后涨跌幅'] = result['一年后点数']/result['大跌日点数'] *100 -100
result
HTTP接口应用案例(python环境)
简介
演示在Python环境使用HTTP接口提取各函数数据。

示例代码
python
import requests
import json
import time
import pandas as pd

# 取消panda科学计数法,保留4位有效小数位.
pd.set_option('float_format', lambda x: '%.2f' % x)
# 设置中文对齐,数值等宽对齐.
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 500)

# Token accessToken 及权限校验机制
getAccessTokenUrl = 'https://quantapi.51ifind.com/api/v1/get_access_token'
# 获取refresh_token需下载Windows版本接口包解压，打开超级命令-工具-refresh_token查询
refreshtoken = '此处填写refresh_token'
getAccessTokenHeader = {"Content-Type": "application/json", "refresh_token": refreshtoken}
getAccessTokenResponse = requests.post(url=getAccessTokenUrl, headers=getAccessTokenHeader)
accessToken = json.loads(getAccessTokenResponse.content)['data']['access_token']
print(accessToken)

thsHeaders = {"Content-Type": "application/json", "access_token": accessToken}


# 高频序列：获取分钟数据
def high_frequency():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/high_frequency'
    thsPara = {"codes":
                   "000001.SZ",
               "indicators":
                   "open,high,low,close,volume,amount,changeRatio",
               "starttime":
                   "2022-07-05 09:15:00",
               "endtime":
                   "2022-07-05 15:15:00"}
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 实时行情：循环获取最新行情数据
def real_time():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/real_time_quotation'
    thsPara = {"codes": "300033.SZ", "indicators": "latest"}
    while True:
        thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
        data = json.loads(thsResponse.content)
        result = pd.json_normalize(data['tables'])
        result = result.drop(columns=['pricetype'])
        result = result.apply(lambda x: x.explode().astype(str).groupby(level=0).agg(", ".join))
        print(result)
        # do your thing here
        time.sleep(3)
        pass


# 历史行情：获取历史的日频行情数据
def history_quotes():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/cmd_history_quotation'
    thsPara = {"codes":
                   "000001.SZ,600000.SH",
               "indicators":
                   "open,high,low,close",
               "startdate":
                   "2021-07-05",
               "enddate":
                   "2022-07-05",
               "functionpara":
                   {"Fill": "Blank"}
               }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 基础数据：获取证券基本信息、财务指标、盈利预测、日频行情等数据
def basic_data():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/basic_data_service'
    thsPara = {"codes":
                   "300033.SZ,600000.SH",
               "indipara":
                   [
                       {
                           "indicator":
                               "ths_regular_report_actual_dd_stock",
                           "indiparams":
                               ["104"]
                       },
                       {
                           "indicator":
                               "ths_total_shares_stock",
                           "indiparams":
                               ["20220705"]
                       }
                   ]
               }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 日期序列：与基础数据指标相同，可以同时获取多日数据
def date_serial():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/date_sequence'
    thsPara = {"codes":
                   "000001.SZ,600000.SH",
               "startdate":
                   "20220605",
               "enddate":
                   "20220705",
               "functionpara":
                   {"Fill": "Blank"},
               "indipara":
                   [
                       {
                           "indicator":
                               "ths_close_price_stock",
                           "indiparams":
                               ["", "100", ""]
                       },
                       {"indicator":
                            "ths_total_shares_stock",
                        "indiparams":
                            [""]
                        }
                   ]
               }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    data = json.loads(thsResponse.content)
    print(data)


# 专题报表，示例提取全部A股代码，更多报表数据使用超级命令工具查看
def data_pool():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/data_pool'
    thsPara = {
        "reportname": "p03425",
        "functionpara": {
            "date": "20220706",
            "blockname": "001005010",
            "iv_type": "allcontract"
        },
        "outputpara": "p03291_f001,p03291_f002,p03291_f003,p03291_f004"
    }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 经济数据库
def edb():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/edb_service'
    thsPara = {"indicators":
                   "G009035746",
               "startdate":
                   "2022-04-01",
               "enddate":
                   "2022-05-01"}
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 日内快照：tick数据
def snap_shot():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/snap_shot'
    thsPara = {
        "codes": "000001.SZ",
        "indicators": "open,high,low,latest,bid1,ask1,bidSize1,askSize1",
        "starttime": "2022-07-06 09:15:00",
        "endtime": "2022-07-06 15:15:00"
    }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 公告函数
def report_query():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/report_query'
    thsPara = {
        "codes": "000001.SZ,600000.SH",
        "functionpara": {
            "reportType": "901"
        },
        "beginrDate": "2021-01-01",
        "endrDate": "2022-07-06",
        "outputpara": "reportDate:Y,thscode:Y,secName:Y,ctime:Y,reportTitle:Y,pdfURL:Y,seq:Y"
    }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 智能选股
def WCQuery():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/smart_stock_picking'
    thsPara = {
        "searchstring": "涨跌幅",
        "searchtype": "stock"
    }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 日期查询函数、日期偏移函数：根据交易所查询交易日
def date_offset():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/get_trade_dates'
    thsPara = {"marketcode": "212001",
               "functionpara":
                   {"dateType": "0",
                    "period": "D",
                    "offset": "-10",
                    "dateFormat": "0",
                    "output": "sequencedate"},
               "startdate":
                   "2022-07-05"}
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


def main():
    # 实时行情
    real_time()
    # 基础数据
    # basic_data()
    # 日期序列
    # date_serial()
    # 专题报表
    # data_pool()
    # 历史行情
    # history_quotes()
    # 高频序列
    # high_frequency()
    # 经济数据库
    # edb()
    # 日内快照
    # snap_shot()
    # 公告函数
    # report_query()
    # 智能选股
    # WCQuery()
    # 日期查询函数
    # date_query()
    # 日期偏移函数
    # date_offset()


if __name__ == '__main__':
    main()