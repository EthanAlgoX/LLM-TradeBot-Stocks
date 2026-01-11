# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-01-11

### Fixed

- **DecisionAgent 数据流 Bug**: 修复 `current_price` 被内部覆盖的问题，现使用 `ProcessedData` 传入的实际入场价
- **入场价计算不一致**: 统一 `_evaluate_signal()` 和 `_simulate_day()` 的入场价计算逻辑，均使用当天开盘价

### Improved

- 多 Agent 数据流更清晰，严格避免 lookahead bias
- 回测结果准确性提升

## [1.0.0] - 2026-01-10

### Added

- 3-Agent 框架 (DataProcessor, MultiPeriod, Decision)
- OR15 策略 (Opening Range 15-minute)
- 91 只股票 watchlist（按行业分类）
- 动态止盈/追踪止损
- 高波动股票优化 (BKKT, RCAT, SIDU 等)
- 自动会话管理（保留最近 5 个回测）
- 完整的每日记录（包括未交易股票）
