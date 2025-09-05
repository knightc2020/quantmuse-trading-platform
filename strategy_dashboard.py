#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantMuse 交易策略分析平台
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="QuantMuse 策略分析",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 样式
st.markdown("""
<style>
    .strategy-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    
    .performance-metric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .backtest-results {
        background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    
    .nav-button {
        background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
        border: none;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        cursor: pointer;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

class TradingStrategy:
    """基础交易策略类"""
    
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.signals = []
        self.performance = {}
    
    def generate_signals(self, data):
        """生成交易信号 - 需要在子类中实现"""
        raise NotImplementedError
    
    def backtest(self, data, initial_capital=10000, commission=0.001):
        """策略回测"""
        signals = self.generate_signals(data)
        
        portfolio = []
        cash = initial_capital
        position = 0
        trades = []
        
        for i, (date, signal) in enumerate(signals.items()):
            price = data.loc[date, 'Close']
            
            if signal == 1 and position == 0:  # 买入信号
                shares = int(cash / price * (1 - commission))
                if shares > 0:
                    cash -= shares * price * (1 + commission)
                    position = shares
                    trades.append({'date': date, 'action': 'BUY', 'price': price, 'shares': shares})
            
            elif signal == -1 and position > 0:  # 卖出信号
                cash += position * price * (1 - commission)
                trades.append({'date': date, 'action': 'SELL', 'price': price, 'shares': position})
                position = 0
            
            # 计算投资组合价值
            portfolio_value = cash + position * price
            portfolio.append({'date': date, 'value': portfolio_value, 'cash': cash, 'position': position})
        
        portfolio_df = pd.DataFrame(portfolio).set_index('date')
        trades_df = pd.DataFrame(trades)
        
        return portfolio_df, trades_df

class MomentumStrategy(TradingStrategy):
    """动量策略"""
    
    def __init__(self, short_window=10, long_window=30):
        super().__init__("动量策略", "基于短期和长期移动平均线的交叉信号")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        """生成动量交易信号"""
        signals = pd.Series(0, index=data.index)
        
        # 计算移动平均线
        short_ma = data['Close'].rolling(window=self.short_window).mean()
        long_ma = data['Close'].rolling(window=self.long_window).mean()
        
        # 生成信号
        signals[short_ma > long_ma] = 1  # 买入信号
        signals[short_ma < long_ma] = -1  # 卖出信号
        
        return signals

class RSIStrategy(TradingStrategy):
    """RSI策略"""
    
    def __init__(self, rsi_period=14, oversold=30, overbought=70):
        super().__init__("RSI策略", "基于相对强弱指数的超买超卖信号")
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, prices):
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data):
        """生成RSI交易信号"""
        signals = pd.Series(0, index=data.index)
        rsi = self.calculate_rsi(data['Close'])
        
        # 生成信号
        signals[rsi < self.oversold] = 1  # 超卖买入
        signals[rsi > self.overbought] = -1  # 超买卖出
        
        return signals

class MACDStrategy(TradingStrategy):
    """MACD策略"""
    
    def __init__(self, fast_period=12, slow_period=26, signal_period=9):
        super().__init__("MACD策略", "基于MACD指标的交叉信号")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate_macd(self, prices):
        """计算MACD"""
        fast_ema = prices.ewm(span=self.fast_period).mean()
        slow_ema = prices.ewm(span=self.slow_period).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        return macd_line, signal_line
    
    def generate_signals(self, data):
        """生成MACD交易信号"""
        signals = pd.Series(0, index=data.index)
        macd_line, signal_line = self.calculate_macd(data['Close'])
        
        # MACD上穿信号线买入，下穿信号线卖出
        signals[(macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))] = 1
        signals[(macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))] = -1
        
        return signals

def calculate_performance_metrics(portfolio_df, benchmark_returns=None):
    """计算策略绩效指标"""
    returns = portfolio_df['value'].pct_change().dropna()
    
    metrics = {
        '总收益率': f"{(portfolio_df['value'].iloc[-1] / portfolio_df['value'].iloc[0] - 1) * 100:.2f}%",
        '年化收益率': f"{(returns.mean() * 252) * 100:.2f}%",
        '年化波动率': f"{(returns.std() * np.sqrt(252)) * 100:.2f}%",
        '最大回撤': f"{((portfolio_df['value'] / portfolio_df['value'].expanding().max() - 1).min()) * 100:.2f}%",
        '夏普比率': f"{(returns.mean() / returns.std() * np.sqrt(252)):.2f}" if returns.std() != 0 else "N/A",
        '胜率': f"{(returns > 0).sum() / len(returns) * 100:.2f}%"
    }
    
    return metrics

def create_strategy_comparison_chart(results):
    """创建策略对比图表"""
    fig = go.Figure()
    
    for strategy_name, (portfolio_df, _) in results.items():
        # 计算累计收益率
        returns = (portfolio_df['value'] / portfolio_df['value'].iloc[0] - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=portfolio_df.index,
            y=returns,
            mode='lines',
            name=strategy_name,
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="策略收益率对比",
        xaxis_title="日期",
        yaxis_title="累计收益率 (%)",
        height=500,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig

def create_trades_chart(data, trades_df, strategy_name):
    """创建交易信号图表"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                       row_heights=[0.7, 0.3], subplot_titles=['价格和交易信号', '持仓'])
    
    # 价格线
    fig.add_trace(go.Scatter(
        x=data.index, y=data['Close'],
        mode='lines', name='收盘价',
        line=dict(color='blue')
    ), row=1, col=1)
    
    # 买入信号
    buy_trades = trades_df[trades_df['action'] == 'BUY']
    if not buy_trades.empty:
        fig.add_trace(go.Scatter(
            x=buy_trades['date'], y=buy_trades['price'],
            mode='markers', name='买入',
            marker=dict(symbol='triangle-up', size=10, color='green')
        ), row=1, col=1)
    
    # 卖出信号
    sell_trades = trades_df[trades_df['action'] == 'SELL']
    if not sell_trades.empty:
        fig.add_trace(go.Scatter(
            x=sell_trades['date'], y=sell_trades['price'],
            mode='markers', name='卖出',
            marker=dict(symbol='triangle-down', size=10, color='red')
        ), row=1, col=1)
    
    fig.update_layout(
        title=f"{strategy_name} 交易信号",
        height=600,
        template='plotly_white'
    )
    
    return fig

def main():
    """主界面"""
    st.markdown("# 🎯 QuantMuse 交易策略分析平台")
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## 📊 策略设置")
        
        # 股票选择
        symbol = st.selectbox(
            "选择股票",
            ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA"],
            index=0
        )
        
        # 时间范围
        period = st.selectbox(
            "分析周期",
            ["6mo", "1y", "2y", "5y"],
            index=1
        )
        
        # 初始资金
        initial_capital = st.number_input(
            "初始资金 ($)",
            value=10000,
            min_value=1000,
            max_value=1000000,
            step=1000
        )
        
        # 手续费
        commission = st.slider(
            "手续费率 (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.01
        ) / 100
        
        st.markdown("---")
        
        # 策略选择
        st.markdown("## ⚙️ 策略选择")
        strategies_to_run = []
        
        if st.checkbox("动量策略", value=True):
            strategies_to_run.append("momentum")
            short_window = st.slider("短期均线", 5, 20, 10)
            long_window = st.slider("长期均线", 20, 50, 30)
        
        if st.checkbox("RSI策略", value=True):
            strategies_to_run.append("rsi")
            rsi_period = st.slider("RSI周期", 10, 20, 14)
            oversold = st.slider("超卖线", 20, 40, 30)
            overbought = st.slider("超买线", 60, 80, 70)
        
        if st.checkbox("MACD策略", value=True):
            strategies_to_run.append("macd")
    
    # 获取数据
    with st.spinner("正在获取数据..."):
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
    
    if data.empty:
        st.error("无法获取数据")
        return
    
    # 运行策略分析
    if st.button("🚀 开始策略分析", type="primary"):
        results = {}
        
        # 初始化策略
        strategies = {}
        if "momentum" in strategies_to_run:
            strategies["动量策略"] = MomentumStrategy(short_window, long_window)
        if "rsi" in strategies_to_run:
            strategies["RSI策略"] = RSIStrategy(rsi_period, oversold, overbought)
        if "macd" in strategies_to_run:
            strategies["MACD策略"] = MACDStrategy()
        
        # 运行回测
        progress_bar = st.progress(0)
        for i, (name, strategy) in enumerate(strategies.items()):
            with st.spinner(f"正在回测 {name}..."):
                portfolio_df, trades_df = strategy.backtest(data, initial_capital, commission)
                results[name] = (portfolio_df, trades_df)
            progress_bar.progress((i + 1) / len(strategies))
        
        # 显示结果
        st.success("✅ 策略分析完成！")
        
        # 策略对比
        if len(results) > 1:
            st.markdown("## 📈 策略收益对比")
            fig_comparison = create_strategy_comparison_chart(results)
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        # 详细结果
        for strategy_name, (portfolio_df, trades_df) in results.items():
            with st.expander(f"📊 {strategy_name} 详细分析", expanded=True):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 交易信号图表
                    fig_trades = create_trades_chart(data, trades_df, strategy_name)
                    st.plotly_chart(fig_trades, use_container_width=True)
                
                with col2:
                    # 绩效指标
                    st.markdown("### 📊 绩效指标")
                    metrics = calculate_performance_metrics(portfolio_df)
                    
                    for metric, value in metrics.items():
                        st.markdown(f"""
                        <div class="performance-metric">
                            <strong>{metric}</strong><br>
                            <span style="font-size: 1.2em; color: #28a745;">{value}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 交易统计
                    st.markdown("### 🔄 交易统计")
                    st.metric("总交易次数", len(trades_df))
                    st.metric("买入次数", len(trades_df[trades_df['action'] == 'BUY']))
                    st.metric("卖出次数", len(trades_df[trades_df['action'] == 'SELL']))
                
                # 交易记录
                if not trades_df.empty:
                    st.markdown("### 📋 交易记录")
                    st.dataframe(trades_df.tail(10), use_container_width=True)
    
    else:
        st.info("👆 请点击'开始策略分析'按钮来运行回测")
        
        # 显示策略说明
        st.markdown("## 📚 策略说明")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="strategy-card">
                <h4>🔄 动量策略</h4>
                <p>基于移动平均线交叉的趋势跟踪策略。当短期均线上穿长期均线时买入，下穿时卖出。</p>
                <ul>
                    <li>适用于趋势明显的市场</li>
                    <li>滞后性较强</li>
                    <li>简单易懂</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="strategy-card">
                <h4>📊 RSI策略</h4>
                <p>基于相对强弱指数的超买超卖策略。RSI低于30买入，高于70卖出。</p>
                <ul>
                    <li>适用于震荡市场</li>
                    <li>反转信号</li>
                    <li>风险相对较小</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="strategy-card">
                <h4>📈 MACD策略</h4>
                <p>基于MACD指标的动量策略。MACD线上穿信号线买入，下穿卖出。</p>
                <ul>
                    <li>综合趋势和动量</li>
                    <li>信号相对准确</li>
                    <li>适合中长期交易</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()