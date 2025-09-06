#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业级QuantMuse交易平台 - Web界面
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import time

# 页面配置
st.set_page_config(
    page_title="QuantMuse 量化交易平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    
    .sidebar-content {
        background-color: #f1f3f4;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .trading-signal {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    .signal-buy {
        background-color: #d4edda;
        border: 2px solid #28a745;
        color: #155724;
    }
    
    .signal-sell {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        color: #721c24;
    }
    
    .signal-hold {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        color: #856404;
    }
    
    .stSelectbox > div > div {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # 缓存5分钟
def get_stock_data(symbol, period="1mo"):
    """获取股票数据"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        info = ticker.info
        return data, info
    except Exception as e:
        st.error(f"获取数据失败: {str(e)}")
        return None, None

def calculate_technical_indicators(data):
    """计算技术指标"""
    # 移动平均线
    data['MA5'] = data['Close'].rolling(window=5).mean()
    data['MA20'] = data['Close'].rolling(window=20).mean()
    data['MA50'] = data['Close'].rolling(window=50).mean()
    
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = data['Close'].ewm(span=12).mean()
    exp2 = data['Close'].ewm(span=26).mean()
    data['MACD'] = exp1 - exp2
    data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
    
    # 布林带
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
    
    return data

def generate_trading_signal(data):
    """生成交易信号"""
    if len(data) < 50:
        return "数据不足", 0
    
    current_price = data['Close'].iloc[-1]
    ma5 = data['MA5'].iloc[-1]
    ma20 = data['MA20'].iloc[-1]
    rsi = data['RSI'].iloc[-1]
    macd = data['MACD'].iloc[-1]
    macd_signal = data['MACD_Signal'].iloc[-1]
    
    score = 0
    
    # MA信号
    if ma5 > ma20:
        score += 1
    else:
        score -= 1
    
    # RSI信号
    if rsi < 30:
        score += 1
    elif rsi > 70:
        score -= 1
    
    # MACD信号
    if macd > macd_signal:
        score += 1
    else:
        score -= 1
    
    # 价格相对布林带位置
    bb_upper = data['BB_Upper'].iloc[-1]
    bb_lower = data['BB_Lower'].iloc[-1]
    
    if current_price < bb_lower:
        score += 1
    elif current_price > bb_upper:
        score -= 1
    
    if score >= 2:
        return "强烈买入", score
    elif score == 1:
        return "买入", score
    elif score == -1:
        return "卖出", score
    elif score <= -2:
        return "强烈卖出", score
    else:
        return "观望", score

def create_price_chart(data, symbol):
    """创建价格图表"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=['价格走势', '成交量', 'RSI', 'MACD'],
        row_heights=[0.5, 0.2, 0.15, 0.15]
    )
    
    # 主价格图 - 蜡烛图
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='价格'
        ), row=1, col=1
    )
    
    # 移动平均线
    fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], 
                           name='MA5', line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], 
                           name='MA20', line=dict(color='blue', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], 
                           name='MA50', line=dict(color='red', width=1)), row=1, col=1)
    
    # 布林带
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], 
                           name='布林上轨', line=dict(color='gray', width=0.8, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], 
                           name='布林下轨', line=dict(color='gray', width=0.8, dash='dash')), row=1, col=1)
    
    # 成交量
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], 
                        name='成交量', marker_color='lightblue'), row=2, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], 
                           name='RSI', line=dict(color='purple')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7, row=3, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], 
                           name='MACD', line=dict(color='blue')), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'], 
                           name='信号线', line=dict(color='red')), row=4, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data['MACD_Histogram'], 
                        name='MACD柱', marker_color='gray'), row=4, col=1)
    
    fig.update_layout(
        title=f'{symbol} 技术分析图表',
        height=800,
        showlegend=True,
        template='plotly_white',
        font=dict(size=12)
    )
    
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig

def create_performance_metrics(data, info):
    """创建绩效指标"""
    if len(data) < 2:
        return {}
    
    current_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[0]
    high_52w = data['High'].max() if len(data) > 252 else data['High'].max()
    low_52w = data['Low'].min() if len(data) > 252 else data['Low'].min()
    
    # 计算收益率
    returns = data['Close'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(252)  # 年化波动率
    sharpe_ratio = (returns.mean() * 252) / volatility if volatility != 0 else 0
    
    metrics = {
        "当前价格": f"${current_price:.2f}",
        "涨跌幅": f"{((current_price/prev_price - 1) * 100):+.2f}%",
        "52周最高": f"${high_52w:.2f}",
        "52周最低": f"${low_52w:.2f}",
        "年化波动率": f"{volatility*100:.2f}%",
        "夏普比率": f"{sharpe_ratio:.2f}",
        "市值": info.get('marketCap', 'N/A'),
        "市盈率": f"{info.get('forwardPE', 'N/A')}",
    }
    
    return metrics

def main():
    """主界面"""
    # 标题
    st.markdown('<h1 class="main-header">QuantMuse 量化交易平台</h1>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 📊 交易设置")
        
        # 股票选择
        symbol = st.selectbox(
            "选择股票代码",
            ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META", "NFLX"],
            index=0
        )
        
        # 时间周期
        period = st.selectbox(
            "数据周期",
            ["1mo", "3mo", "6mo", "1y", "2y"],
            index=2
        )
        
        # 自动刷新
        auto_refresh = st.checkbox("自动刷新 (30秒)", value=False)
        
        if st.button("🔄 手动刷新"):
            st.cache_data.clear()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 主内容区
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # 获取数据
    with st.spinner("正在获取市场数据..."):
        data, info = get_stock_data(symbol, period)
    
    if data is None or data.empty:
        st.error("无法获取股票数据，请检查网络连接或稍后重试。")
        return
    
    # 计算技术指标
    data = calculate_technical_indicators(data)
    
    # 生成交易信号
    signal, score = generate_trading_signal(data)
    
    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    current_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100
    
    with col1:
        st.metric(
            "当前价格", 
            f"${current_price:.2f}",
            f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    
    with col2:
        st.metric("成交量", f"{data['Volume'].iloc[-1]:,.0f}")
    
    with col3:
        rsi_value = data['RSI'].iloc[-1]
        st.metric("RSI", f"{rsi_value:.1f}")
    
    with col4:
        # 交易信号显示
        signal_class = "signal-hold"
        if "买入" in signal:
            signal_class = "signal-buy"
        elif "卖出" in signal:
            signal_class = "signal-sell"
        
        st.markdown(f"""
        <div class="trading-signal {signal_class}">
            交易信号: {signal}
        </div>
        """, unsafe_allow_html=True)
    
    # 图表区域
    st.plotly_chart(create_price_chart(data, symbol), use_container_width=True)
    
    # 详细信息区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📈 技术分析摘要")
        
        # 技术指标表格
        tech_data = {
            "指标": ["MA5", "MA20", "MA50", "RSI", "MACD"],
            "当前值": [
                f"{data['MA5'].iloc[-1]:.2f}",
                f"{data['MA20'].iloc[-1]:.2f}",
                f"{data['MA50'].iloc[-1]:.2f}" if not pd.isna(data['MA50'].iloc[-1]) else "N/A",
                f"{data['RSI'].iloc[-1]:.1f}",
                f"{data['MACD'].iloc[-1]:.4f}"
            ],
            "信号": [
                "🔴" if current_price < data['MA5'].iloc[-1] else "🟢",
                "🔴" if current_price < data['MA20'].iloc[-1] else "🟢",
                "🔴" if pd.isna(data['MA50'].iloc[-1]) or current_price < data['MA50'].iloc[-1] else "🟢",
                "🔴" if rsi_value > 70 else "🟢" if rsi_value < 30 else "🟡",
                "🟢" if data['MACD'].iloc[-1] > data['MACD_Signal'].iloc[-1] else "🔴"
            ]
        }
        
        st.dataframe(pd.DataFrame(tech_data), use_container_width=True)
    
    with col2:
        st.markdown("### 📊 市场概况")
        
        # 绩效指标
        metrics = create_performance_metrics(data, info or {})
        for key, value in metrics.items():
            st.markdown(f"**{key}**: {value}")
    
    # 底部信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### ⚡ 实时状态")
        st.success("✅ 数据连接正常")
        st.info(f"📅 最后更新: {datetime.now().strftime('%H:%M:%S')}")
    
    with col2:
        st.markdown("### 📋 交易建议")
        st.markdown(f"**信号强度**: {abs(score)}/4")
        if score >= 2:
            st.success("📈 建议买入")
        elif score <= -2:
            st.error("📉 建议卖出")
        else:
            st.warning("⏸️ 建议观望")
    
    with col3:
        st.markdown("### ⚠️ 风险提示")
        st.markdown("""
        - 所有分析仅供参考
        - 投资有风险，入市需谨慎
        - 请根据自身风险承受能力投资
        """)

if __name__ == "__main__":
    main()