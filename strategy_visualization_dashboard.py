#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游资跟投策略结果可视化仪表板
基于Streamlit构建的交互式分析界面
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os
from supabase import create_client
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="游资跟投策略分析仪表板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_supabase_client():
    """获取Supabase客户端"""
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        st.error("请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")
        return None
    
    return create_client(url, key)

@st.cache_data(ttl=300)  # 5分钟缓存
def load_dragon_tiger_data():
    """加载龙虎榜数据"""
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table('seat_daily').select("*").order('trade_date', desc=True).limit(10000).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            numeric_columns = ['net_amt', 'buy_amt', 'sell_amt']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return pd.DataFrame()

def analyze_hotmoney_performance(data, min_trades=5):
    """分析游资表现"""
    if data.empty:
        return pd.DataFrame()
    
    # 游资表现分析
    hotmoney_stats = data.groupby('seat_name').agg({
        'net_amt': ['count', 'sum', 'mean', 'std'],
        'code': 'nunique',
        'trade_date': ['min', 'max']
    }).round(2)
    
    hotmoney_stats.columns = ['交易次数', '总净买入', '平均净买入', '净买入标准差', '涉及股票数', '最早交易日', '最晚交易日']
    
    # 计算胜率
    hotmoney_stats['胜率'] = (data.groupby('seat_name')['net_amt'].apply(lambda x: (x > 0).mean()) * 100).round(1)
    
    # 计算活跃天数
    hotmoney_stats['活跃天数'] = data.groupby('seat_name')['trade_date'].nunique()
    
    # 综合评分算法
    hotmoney_stats['评分'] = (
        np.log1p(hotmoney_stats['交易次数']) * 5 +
        (hotmoney_stats['总净买入'] / hotmoney_stats['总净买入'].max()) * 40 +
        np.log1p(hotmoney_stats['涉及股票数']) * 8 +
        (hotmoney_stats['胜率'] / 100) * 10 +
        np.log1p(hotmoney_stats['活跃天数']) * 2
    ).round(2)
    
    # 筛选条件
    qualified = hotmoney_stats[
        (hotmoney_stats['交易次数'] >= min_trades) & 
        (hotmoney_stats['总净买入'] > 0)
    ].sort_values('评分', ascending=False)
    
    return qualified.reset_index()

def generate_investment_signals(data, hotmoney_performance, top_n=10, min_net_buy=5000000):
    """生成投资信号"""
    if data.empty or hotmoney_performance.empty:
        return []
    
    # 选择Top N 游资
    top_hotmoney = hotmoney_performance.head(top_n)
    
    # 获取最近30天数据
    recent_date = data['trade_date'].max()
    start_date = recent_date - timedelta(days=30)
    recent_data = data[data['trade_date'] >= start_date]
    
    signals = []
    
    for _, hotmoney in top_hotmoney.iterrows():
        seat_name = hotmoney['seat_name']
        score = hotmoney['评分']
        
        # 获取该游资的大额买入
        hotmoney_trades = recent_data[
            (recent_data['seat_name'] == seat_name) & 
            (recent_data['net_amt'] >= min_net_buy)
        ].sort_values('trade_date', ascending=False)
        
        # 取最近3笔大额买入
        for _, trade in hotmoney_trades.head(3).iterrows():
            signals.append({
                'stock_code': trade['code'],
                'seat_name': seat_name,
                'net_amount': trade['net_amt'],
                'trade_date': trade['trade_date'].strftime('%Y-%m-%d'),
                'score': score,
                'weight': min(0.05, trade['net_amt'] / 100000000)
            })
    
    # 去重并排序
    unique_signals = {}
    for signal in signals:
        stock = signal['stock_code']
        if stock not in unique_signals or signal['score'] > unique_signals[stock]['score']:
            unique_signals[stock] = signal
    
    final_signals = list(unique_signals.values())
    final_signals.sort(key=lambda x: x['score'], reverse=True)
    
    return final_signals

def get_stock_current_price(stock_code):
    """获取股票当前价格"""
    try:
        # 转换股票代码格式
        if '.SH' in stock_code:
            ticker = stock_code.replace('.SH', '.SS')
        elif '.SZ' in stock_code:
            ticker = stock_code.replace('.SZ', '.SZ')
        elif '.BJ' in stock_code:
            # 北交所股票可能需要特殊处理
            return None
        else:
            return None
            
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        
        if not hist.empty:
            return {
                'current_price': hist['Close'].iloc[-1],
                'change_pct': ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1] * 100)
            }
        return None
    except:
        return None

def main():
    """主函数"""
    
    # 标题和简介
    st.title("🎯 游资跟投策略分析仪表板")
    st.markdown("---")
    
    # 侧边栏配置
    st.sidebar.header("📊 分析参数设置")
    
    min_trades = st.sidebar.slider("最小交易次数", 3, 20, 5)
    min_net_buy = st.sidebar.slider("最小净买入额 (万元)", 100, 5000, 500) * 10000
    top_n_hotmoney = st.sidebar.slider("Top N 游资", 5, 20, 10)
    
    # 数据加载
    with st.spinner("正在加载龙虎榜数据..."):
        data = load_dragon_tiger_data()
    
    if data.empty:
        st.error("无法加载数据，请检查数据库连接")
        return
    
    # 基础数据统计
    st.header("📈 数据概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总记录数", f"{len(data):,}")
    with col2:
        st.metric("游资数量", f"{data['seat_name'].nunique():,}")
    with col3:
        st.metric("股票数量", f"{data['code'].nunique():,}")
    with col4:
        recent_days = (data['trade_date'].max() - data['trade_date'].min()).days
        st.metric("数据跨度 (天)", recent_days)
    
    # 游资表现分析
    st.header("🏆 游资表现分析")
    hotmoney_performance = analyze_hotmoney_performance(data, min_trades)
    
    if not hotmoney_performance.empty:
        # Top 游资排行榜
        st.subheader(f"Top {min(20, len(hotmoney_performance))} 游资排行榜")
        
        display_df = hotmoney_performance.head(20).copy()
        display_df['seat_name'] = display_df['seat_name'].apply(lambda x: x[:30] + "..." if len(x) > 30 else x)
        display_df['总净买入'] = display_df['总净买入'].apply(lambda x: f"{x/1e8:.2f}亿")
        display_df['平均净买入'] = display_df['平均净买入'].apply(lambda x: f"{x/1e4:.0f}万")
        
        st.dataframe(
            display_df[['seat_name', '评分', '胜率', '交易次数', '总净买入', '平均净买入', '涉及股票数', '活跃天数']],
            use_container_width=True
        )
        
        # 游资表现可视化
        col1, col2 = st.columns(2)
        
        with col1:
            # 评分分布
            fig_score = px.histogram(
                hotmoney_performance.head(50), 
                x='评分', 
                nbins=20,
                title="游资评分分布",
                labels={'评分': '综合评分', 'count': '游资数量'}
            )
            fig_score.update_layout(showlegend=False)
            st.plotly_chart(fig_score, use_container_width=True)
        
        with col2:
            # 胜率vs交易次数散点图
            fig_scatter = px.scatter(
                hotmoney_performance.head(50),
                x='交易次数',
                y='胜率',
                size='总净买入',
                color='评分',
                hover_data=['seat_name'],
                title="胜率 vs 交易频率",
                labels={'胜率': '胜率 (%)', '交易次数': '交易次数'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 投资信号生成
    st.header("🎯 投资信号分析")
    
    signals = generate_investment_signals(data, hotmoney_performance, top_n_hotmoney, min_net_buy)
    
    if signals:
        st.success(f"成功生成 {len(signals)} 个投资信号")
        
        # 投资信号表格
        signals_df = pd.DataFrame(signals)
        signals_df['权重'] = signals_df['weight'].apply(lambda x: f"{x:.2%}")
        signals_df['净买入(万)'] = signals_df['net_amount'].apply(lambda x: f"{x/1e4:.0f}")
        signals_df['游资简称'] = signals_df['seat_name'].apply(lambda x: x[:20] + "..." if len(x) > 20 else x)
        
        st.subheader("投资信号详情")
        display_signals = signals_df[['stock_code', '权重', '净买入(万)', '游资简称', 'trade_date', 'score']].head(20)
        display_signals.columns = ['股票代码', '建议权重', '净买入(万)', '游资', '交易日期', '游资评分']
        st.dataframe(display_signals, use_container_width=True)
        
        # 权重分布饼图
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                signals_df.head(10),
                values='weight',
                names='stock_code',
                title="Top 10 投资信号权重分布"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 按游资分组的信号数量
            signal_by_hotmoney = signals_df.groupby('游资简称').size().reset_index(name='信号数量').sort_values('信号数量', ascending=False)
            fig_bar = px.bar(
                signal_by_hotmoney.head(10),
                x='信号数量',
                y='游资简称',
                orientation='h',
                title="各游资贡献的信号数量"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # 实时股价检查
        st.subheader("📊 实时股价监控")
        
        if st.button("获取实时股价", type="primary"):
            progress_bar = st.progress(0)
            stock_prices = {}
            
            # 使用多线程获取股价
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(get_stock_current_price, signal['stock_code']): signal['stock_code'] 
                          for signal in signals[:10]}
                
                for i, future in enumerate(as_completed(futures)):
                    stock_code = futures[future]
                    try:
                        result = future.result()
                        if result:
                            stock_prices[stock_code] = result
                    except Exception as e:
                        st.warning(f"获取 {stock_code} 股价失败: {e}")
                    
                    progress_bar.progress((i + 1) / len(futures))
            
            if stock_prices:
                price_data = []
                for signal in signals[:10]:
                    if signal['stock_code'] in stock_prices:
                        price_info = stock_prices[signal['stock_code']]
                        price_data.append({
                            '股票代码': signal['stock_code'],
                            '当前价格': f"{price_info['current_price']:.2f}",
                            '涨跌幅': f"{price_info['change_pct']:.2f}%",
                            '建议权重': f"{signal['weight']:.2%}",
                            '游资评分': f"{signal['score']:.1f}"
                        })
                
                if price_data:
                    st.dataframe(pd.DataFrame(price_data), use_container_width=True)
    else:
        st.warning("未生成有效投资信号，可能需要调整参数")
    
    # 市场趋势分析
    st.header("📊 市场趋势分析")
    
    # 按日期统计交易活跃度
    daily_activity = data.groupby(data['trade_date'].dt.date).agg({
        'net_amt': 'sum',
        'code': 'nunique',
        'seat_name': 'nunique'
    }).reset_index()
    daily_activity.columns = ['日期', '总净买入', '涉及股票数', '活跃游资数']
    
    # 最近30天趋势
    recent_30_days = daily_activity.tail(30)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_trend = px.line(
            recent_30_days,
            x='日期',
            y='总净买入',
            title="最近30天净买入趋势"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with col2:
        fig_activity = px.line(
            recent_30_days,
            x='日期',
            y='活跃游资数',
            title="最近30天游资活跃度"
        )
        st.plotly_chart(fig_activity, use_container_width=True)
    
    # 策略总结
    st.header("📋 策略总结")
    
    if signals and not hotmoney_performance.empty:
        total_weight = sum(signal['weight'] for signal in signals)
        avg_score = np.mean([signal['score'] for signal in signals])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总配置权重", f"{total_weight:.2%}")
        with col2:
            st.metric("平均游资评分", f"{avg_score:.1f}")
        with col3:
            st.metric("信号股票数", len(signals))
        
        st.info(f"""
        **策略要点总结:**
        - 基于 {len(hotmoney_performance)} 个合格游资的历史表现
        - 生成 {len(signals)} 个投资信号，总权重 {total_weight:.2%}
        - 平均游资评分 {avg_score:.1f}，表明选择的游资质量较高
        - 建议定期更新数据并重新评估信号有效性
        """)
    
    # 免责声明
    st.markdown("---")
    st.warning("""
    **免责声明:** 
    本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
    请根据自身风险承受能力谨慎决策。
    """)

if __name__ == "__main__":
    main()