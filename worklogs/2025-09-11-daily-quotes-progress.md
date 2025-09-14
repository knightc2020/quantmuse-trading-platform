# 2025-09-11 日线数据抽取与入库进展

时间: 2025-09-11

## 背景
- 2025-09-10 起开始端到端打通日线数据抽取→清洗→写入 Supabase；部分字段 NULL 与类型不匹配导致写入失败。

## 今日完成
- 集成 THS_BD 基础函数指标，补齐 HistoryQuotes 缺失字段（pre_close、upper/lower_limit、换手率、振幅、盘后/含大宗交易、复权因子、停牌信息等）。
- 扩展字段映射与表结构：`sql/daily_quotes_recreate.sql` 新增多项官方指标对应列；`data_service/data_sync.py` 增加映射与清洗规则。
- 列冲突合并：当 HQ 与 BD 同时返回同名列时，自动合并并去重，消除重复列导致的清洗异常。
- 数据清洗强化：
  - 数值列统一 to_numeric + fillna。
  - 整数字段强制为 int64（volume、trans_num、post_volume 等）避免 bigint 接收 "0.0" 的 22P02 错误。
  - 日期列规范化，非法日期置 None；写库前统一将 NaN/NaT → None。
- CLI 提升：`daily_data_sync.py daily` 支持 `--limit-codes/--code-offset/--codes/--codes-file`，便于小样本端到端验证。

## 验证
- 命令：`python daily_data_sync.py daily --date 2025-09-05 --codes 000001.SZ,600000.SH,300750.SZ`
- 结果：写入成功；Supabase 400 语法错误与 NaN 序列化错误均已解决。

## 产出
- 代码文件
  - `data_service/tonghuashun_client.py`
  - `data_service/data_sync.py`
  - `sql/daily_quotes_recreate.sql`
  - `daily_data_sync.py`
- 备份归档
  - `backups/backup-latest.tar.gz`（含当前仓库快照，排除 .git 与 backups 自身）

## 后续计划
- 扩大抽样规模（50→200→2000），观察吞吐与错误率；根据稳定性调整 `batch_size/call_interval`。
- 将限流与批量参数接入 `data_sync_config.json`，统一配置化。
- 提供强制启用 BD 补齐的开关；大区间回填时按需开启。
- TimescaleDB hypertable 化（如环境允许），优化大规模历史回填与查询性能。

