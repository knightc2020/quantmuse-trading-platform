# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuantMuse is a professional quantitative trading platform built with Streamlit, featuring real-time market data analysis, technical indicators, strategy backtesting, and AI-powered analytics. The platform supports both crypto (via Binance) and stock data (via Yahoo Finance) with extensive AI/NLP capabilities.

## Development Commands

### Installation and Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# Install with all optional dependencies
pip install -e .[ai,visualization,realtime,web,test]

# Setup environment variables
cp .env.example .env
# Edit .env with your Supabase credentials
```

### Running Applications
```bash
# Main Streamlit dashboard (primary interface)
streamlit run streamlit_app.py

# Strategy analysis dashboard  
streamlit run strategy_dashboard.py

# Dragon Tiger analysis app
streamlit run dragon_tiger_app.py

# Simple web interface
python run_web_simple.py

# Basic data service demo
python main.py
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=data_service

# Run specific test modules
pytest tests/test_binance_fetcher.py
pytest tests/test_llm_integration.py
```

### Configuration
- Copy `config.example.json` to `config.json` and configure API keys
- Set up `.env` file with Supabase credentials for database operations
- Trading parameters, risk management, and strategy settings are in `config.json`

## Architecture Overview

### Core Structure
```
data_service/              # Main package containing all trading logic
├── fetchers/             # Data acquisition (Binance, Yahoo, Alpha Vantage)  
├── processors/           # Data processing and technical analysis
├── storage/              # Database, file storage, caching
├── strategies/           # Trading strategy implementations
├── backtest/            # Backtesting engine and performance analysis
├── factors/             # Quantitative factor analysis and stock selection
├── ai/                  # LLM integration, NLP, sentiment analysis
├── ml/                  # Machine learning models
├── realtime/            # Real-time data streaming
├── visualization/       # Chart generation and plotting utilities
└── web/                 # Web API components
```

### Key Components

**Data Layer**
- `fetchers/`: Multi-source data acquisition with graceful fallbacks
- `storage/`: SQLite/PostgreSQL with Redis caching and file storage
- `processors/`: Technical indicator calculation and data preprocessing

**Analytics Engine** 
- `factors/`: Factor-based stock screening and portfolio optimization
- `backtest/`: Strategy backtesting with comprehensive performance metrics
- `strategies/`: Momentum, mean reversion, and value strategies

**AI/ML Integration**
- `ai/`: OpenAI/LangChain integration for market analysis
- `ai/sentiment_analyzer.py`: Multi-source sentiment analysis
- `ai/news_processor.py`: News sentiment processing
- `ml/`: Traditional ML models for prediction

**Applications**
- `streamlit_app.py`: Main trading dashboard with real-time data
- `strategy_dashboard.py`: Strategy backtesting and comparison
- `dragon_tiger_app.py`: Dragon Tiger list analysis for Chinese markets

### Data Flow Architecture

1. **Data Ingestion**: Fetchers pull data from APIs (Binance, Yahoo, Alpha Vantage)
2. **Processing**: Raw data converted to standardized format with technical indicators
3. **Storage**: Processed data cached in Redis, persisted in database
4. **Analysis**: Factor calculation, strategy signals, AI sentiment analysis
5. **Visualization**: Streamlit apps display results with interactive charts

### Configuration System

The platform uses a two-tier configuration:
- `config.json`: Main configuration for trading parameters, API keys, database settings
- `.env`: Environment-specific variables (Supabase credentials)

Key configuration sections:
- `api_keys`: External service credentials (Binance, OpenAI, Alpha Vantage)
- `trading`: Risk management, position sizing, drawdown limits  
- `strategies`: Strategy-specific parameters
- `ai`: LLM settings and feature toggles

### Error Handling

The codebase uses graceful degradation:
- Missing optional dependencies are handled with try/catch imports
- API failures fall back to cached data or alternative sources
- All modules in `data_service/__init__.py` have import error handling

### Testing Strategy

- `tests/` contains unit tests for core components
- `pytest.ini` configures test discovery and warning filters
- Coverage tracking available via pytest-cov
- Integration tests cover data fetcher and LLM functionality

## Development Notes

### Dependencies
The project has modular dependencies defined in `setup.py`:
- Core: pandas, numpy, yfinance, requests
- AI: OpenAI, LangChain, transformers, spaCy, NLTK
- Visualization: Streamlit, Plotly, matplotlib
- Web: FastAPI, uvicorn
- Realtime: websockets, Redis

### Database Integration
- Supabase as primary database (configured via `.env`)
- SQLite fallback for local development
- Redis for high-speed caching of market data
- Database schema includes market data, trading signals, and analysis results

### AI/LLM Features
- Sentiment analysis of news and social media
- Market commentary generation via GPT-4
- Strategy recommendations based on market conditions
- NLP processing for financial text analysis

## 工作历史记录 (Work History)

### 2025-09-07 - 初始化 CLAUDE.md
**任务**: 分析代码库并创建 CLAUDE.md 文件
**主要改动**:
- 创建了完整的 CLAUDE.md 文件，包含项目概览、开发命令、架构说明
- 分析了项目结构：data_service 核心包含 15+ 个功能模块
- 识别了多个应用入口点：streamlit_app.py (主界面)、strategy_dashboard.py (策略分析)、dragon_tiger_app.py (龙虎榜分析)
- 记录了关键配置：config.json + .env 双层配置系统
- 建立了测试流程：pytest 配置，覆盖率测试
**技术栈**: Streamlit + Plotly + Pandas + Supabase + OpenAI/LangChain
**状态**: ✅ 完成

### 2025-09-07 - 项目可用性检查
**任务**: 验证项目当前可用状态
**检查结果**:
- ✅ 核心依赖已安装：Streamlit 1.49.1, yfinance, pandas, plotly
- ✅ data_service 包可正常导入，所有模块加载成功
- ✅ streamlit_app.py 主应用可以运行（有警告但不影响使用）
- ✅ Yahoo Finance 数据连接正常，能获取实时股票数据
- ❌ 配置文件缺失：需要创建 .env 和 config.json
- ❌ Supabase 环境变量未设置

**当前可用功能**:
- 基本股票数据分析（通过 Yahoo Finance）
- Streamlit 主界面显示
- 技术指标计算
- 图表可视化

**需要配置才能使用的功能**:
- Supabase 数据库操作
- API 密钥相关功能（OpenAI, Binance 等）
**状态**: ⚠️ 部分可用

---
*注意：每次完成重要任务后，请在此部分添加新的工作记录，包含日期、任务描述、主要改动和当前状态*