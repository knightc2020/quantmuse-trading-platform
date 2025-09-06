#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantMuse 龙虎榜分析平台
基于Supabase数据库的A股龙虎榜深度分析
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_service'))

from supabase_client import get_supabase_client

# 页面配置
st.set_page_config(
    page_title="QuantMuse 龙虎榜分析",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff6b35;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #ff6b35, #f7931e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .dragon-card {
        background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);
    }
    
    .stat-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ff6b35;
        margin: 0.5rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        color: #856404;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """主函数"""
    
    # 页面标题
    st.markdown('<h1 class="main-header">🐉 QuantMuse 龙虎榜分析平台</h1>', unsafe_allow_html=True)
    
    # 初始化Supabase客户端
    with st.spinner("正在连接数据库..."):
        client = get_supabase_client()
    
    # 检查连接状态
    if not client.is_connected():
        st.error("❌ 数据库连接失败！请检查配置。")
        st.markdown("""
        **配置步骤：**
        1. 创建 `.env` 文件
        2. 添加以下配置：
        ```
        SUPABASE_URL=your_supabase_project_url
        SUPABASE_KEY=your_supabase_anon_key
        ```
        3. 或在 Streamlit Cloud 中配置 secrets
        """)
        return
    
    # 测试连接
    if client.test_connection():
        st.markdown('<div class="success-box">✅ 数据库连接成功！</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ 数据库连接异常，某些功能可能不可用。</div>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## 📊 分析设置")
        
        # 数据类型选择
        data_type = st.selectbox(
            "数据类型",
            ['seat', 'inst', 'flow'],
            format_func=lambda x: {
                'seat': '🎯 游资席位',
                'inst': '🏢 机构席位', 
                'flow': '📈 交易流向'
            }[x],
            index=0,
            help="选择要分析的龙虎榜数据类型"
        )
        
        # 时间范围选择
        analysis_period = st.selectbox(
            "分析时间范围",
            [7, 15, 30, 60, 90],
            index=2,
            format_func=lambda x: f"最近 {x} 天"
        )
        
        # 数据展示数量
        display_limit = st.selectbox(
            "显示数据量",
            [50, 100, 200, 500],
            index=1
        )
        
        st.markdown("---")
        
        # 分析模块选择
        st.markdown("## 🔍 分析模块")
        show_summary = st.checkbox("数据概览", value=True)
        show_seats = st.checkbox("活跃席位分析", value=True)
        show_stocks = st.checkbox("热门股票分析", value=True)
        show_raw_data = st.checkbox("原始数据查看", value=False)
    
    # 主内容区域
    col1, col2, col3 = st.columns([1, 1, 1])
    
    # 数据概览
    if show_summary:
        with st.spinner(f"正在加载{data_type}数据概览..."):
            summary = client.get_dragon_tiger_summary(days=analysis_period, table_type=data_type)
            
            if summary:
                with col1:
                    st.markdown('<div class="dragon-card">', unsafe_allow_html=True)
                    st.markdown("### 📊 数据概览")
                    st.metric("总记录数", f"{summary.get('总记录数', 0):,}")
                    st.metric("涉及股票", f"{summary.get('涉及股票数', 0):,}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="dragon-card">', unsafe_allow_html=True)
                    st.markdown("### 📅 时间范围")
                    if summary.get('最新日期'):
                        st.write(f"**最新**: {summary['最新日期']}")
                    if summary.get('最早日期'):
                        st.write(f"**最早**: {summary['最早日期']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col3:
                    st.markdown('<div class="dragon-card">', unsafe_allow_html=True)
                    st.markdown("### 🏢 席位统计")
                    if data_type == 'seat':
                        st.metric("游资席位", f"{summary.get('游资席位数', 0):,}")
                    elif data_type == 'inst':
                        st.metric("机构席位", f"{summary.get('机构席位数', 0):,}")
                    else:
                        st.metric("股票数量", f"{summary.get('股票名称数', 0):,}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning(f"无法获取{data_type}数据概览")
    
    # 活跃席位分析
    if show_seats and data_type in ['seat', 'inst']:
        st.markdown("---")
        seat_title = "🎯 活跃游资分析" if data_type == 'seat' else "🏢 活跃机构分析"
        st.markdown(f"## {seat_title}")
        
        with st.spinner(f"正在分析活跃{data_type}..."):
            top_seats = client.get_top_seats(days=analysis_period, top_n=20, table_type=data_type)
            
            if top_seats is not None and not top_seats.empty:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 席位上榜次数图表
                    fig = px.bar(
                        x=top_seats.index[:10], 
                        y=top_seats['上榜次数'][:10],
                        title=f"最近{analysis_period}天活跃席位排行",
                        labels={'x': '席位名称', 'y': '上榜次数'},
                        color=top_seats['上榜次数'][:10],
                        color_continuous_scale='Oranges'
                    )
                    fig.update_layout(
                        xaxis_tickangle=-45,
                        height=400,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("### 📈 Top 10 席位")
                    for i, (seat, row) in enumerate(top_seats.head(10).iterrows()):
                        net_buy = row.get('净买入金额(万)', 0)
                        net_buy_str = f"净买入 {net_buy:.1f}万" if net_buy != 0 else ""
                        st.markdown(f"""
                        <div class="stat-card">
                        <strong>{i+1}. {seat}</strong><br>
                        上榜 {row['上榜次数']} 次<br>
                        涉及 {row['涉及股票数']} 只股票<br>
                        {net_buy_str}
                        </div>
                        """, unsafe_allow_html=True)
                
                # 完整席位数据表
                with st.expander("📋 查看完整席位数据"):
                    st.dataframe(top_seats, use_container_width=True)
            else:
                st.warning(f"暂无{data_type}席位数据")
    
    # 热门股票分析  
    if show_stocks:
        st.markdown("---")
        st.markdown("## 📈 热门股票分析")
        
        with st.spinner("正在分析热门股票..."):
            recent_stocks = client.get_recent_stocks(days=min(analysis_period, 15))
            
            if recent_stocks is not None and not recent_stocks.empty:
                # 股票上榜频次统计
                stock_freq = recent_stocks['股票代码'].value_counts().head(20)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 股票上榜次数图表
                    fig = px.bar(
                        x=stock_freq.index,
                        y=stock_freq.values,
                        title="最热门股票（按上榜次数）",
                        labels={'x': '股票代码', 'y': '上榜次数'},
                        color=stock_freq.values,
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("### 🔥 热门股票")
                    for i, (stock, count) in enumerate(stock_freq.head(10).items()):
                        # 获取股票名称
                        stock_name = recent_stocks[recent_stocks['股票代码'] == stock]['股票名称'].iloc[0]
                        st.markdown(f"""
                        <div class="stat-card">
                        <strong>{i+1}. {stock}</strong><br>
                        {stock_name}<br>
                        上榜 {count} 次
                        </div>
                        """, unsafe_allow_html=True)
                
                # 最近上榜股票列表
                with st.expander("📋 查看最近上榜股票"):
                    st.dataframe(
                        recent_stocks.head(50), 
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.warning("暂无股票数据")
    
    # 原始数据查看
    if show_raw_data:
        st.markdown("---")
        st.markdown("## 📋 原始数据")
        
        with st.expander("🔍 查看原始龙虎榜数据", expanded=False):
            with st.spinner("正在加载原始数据..."):
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=analysis_period)).strftime('%Y-%m-%d')
                
                raw_data = client.get_dragon_tiger_data(
                    start_date=start_date,
                    end_date=end_date,
                    limit=display_limit
                )
                
                if raw_data is not None and not raw_data.empty:
                    st.markdown(f"**数据范围**: {start_date} 至 {end_date}")
                    st.markdown(f"**记录数量**: {len(raw_data):,} 条")
                    
                    # 显示数据
                    st.dataframe(raw_data, use_container_width=True)
                    
                    # 下载按钮
                    csv = raw_data.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下载数据(CSV)",
                        data=csv,
                        file_name=f"dragon_tiger_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("暂无原始数据")
    
    # 页面底部
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
    <p>🐉 QuantMuse 龙虎榜分析平台 | 基于 Supabase 数据库</p>
    <p>数据来源: A股龙虎榜历史数据 (2015-至今)</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()