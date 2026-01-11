export const translations = {
    en: {
        // Header
        appName: "AI Stock Daily",
        dashboard: "Dashboard",
        today: "Today",
        yesterday: "Yesterday",

        // Dashboard
        totalReturn: "7D Total Return",
        winRate: "Win Rate",
        totalTrades: "Total Trades",
        avgDaily: "Avg Daily",
        performance7d: "7 Day Performance",
        todayPicks: "Today's Picks",
        yesterdayRecap: "Yesterday's Recap",

        // Today
        todayPicksTitle: "Today's Picks",
        or15Close: "OR15 Close",
        entryPrice: "Entry Price",
        maxPotential: "Max Potential",
        reason: "Reason",
        noPicksToday: "No picks today",
        checkBackAfterOpen: "Check back after market open",

        // Yesterday
        yesterdayRecapTitle: "Yesterday's Recap",
        summary: "Summary",
        wins: "Wins",
        losses: "Losses",
        tradeDetails: "Trade Details",
        symbol: "Symbol",
        entry: "Entry",
        exit: "Exit",
        pnl: "PnL",
        exitReason: "Exit Reason",
        duration: "Duration",
        noTradesYesterday: "No trades yesterday",

        // Common
        session: "Session",
        date: "Date",
        action: "Action",
        buy: "BUY",
        sell: "SELL",
        wait: "WAIT",

        // Mode
        live: "Live",
        backtest: "Backtest",
    },

    zh: {
        // Header
        appName: "AI 选股日报",
        dashboard: "仪表盘",
        today: "今日选股",
        yesterday: "昨日复盘",

        // Dashboard
        totalReturn: "7日总收益",
        winRate: "胜率",
        totalTrades: "总交易数",
        avgDaily: "日均收益",
        performance7d: "7日收益表现",
        todayPicks: "今日选股",
        yesterdayRecap: "昨日复盘",

        // Today
        todayPicksTitle: "今日选股",
        or15Close: "OR15收盘",
        entryPrice: "入场价",
        maxPotential: "最大潜力",
        reason: "原因",
        noPicksToday: "今日无选股",
        checkBackAfterOpen: "开盘后查看",

        // Yesterday
        yesterdayRecapTitle: "昨日复盘",
        summary: "汇总",
        wins: "盈利",
        losses: "亏损",
        tradeDetails: "交易详情",
        symbol: "股票",
        entry: "入场",
        exit: "出场",
        pnl: "收益",
        exitReason: "出场原因",
        duration: "持仓时间",
        noTradesYesterday: "昨日无交易",

        // Common
        session: "会话",
        date: "日期",
        action: "操作",
        buy: "买入",
        sell: "卖出",
        wait: "观望",

        // Mode
        live: "实盘",
        backtest: "回测",
    }
}

// Reason translation mapping (for dynamic data)
export const reasonTranslations: Record<string, { en: string; zh: string }> = {
    // Common reasons
    "Breakout pattern detected": { en: "Breakout pattern detected", zh: "突破形态确认" },
    "No clear signal": { en: "No clear signal", zh: "无明确信号" },
    "符合突破条件": { en: "Breakout pattern detected", zh: "符合突破条件" },
    "无明确信号": { en: "No clear signal", zh: "无明确信号" },
    "非 TOP5": { en: "Not in Top 5", zh: "非 TOP5" },
    "趋势向上+突破OR15": { en: "Uptrend + OR15 breakout", zh: "趋势向上+突破OR15" },
    "突破OR15高点": { en: "OR15 high breakout", zh: "突破OR15高点" },
    "动量强劲": { en: "Strong momentum", zh: "动量强劲" },
    "成交量放大": { en: "Volume surge", zh: "成交量放大" },
    "强买入信号": { en: "Strong buy signal", zh: "强买入信号" },
    "买入信号": { en: "Buy signal", zh: "买入信号" },
    "趋势向上": { en: "Uptrend", zh: "趋势向上" },
    "趋势向下": { en: "Downtrend", zh: "趋势向下" },
    "横盘整理": { en: "Consolidation", zh: "横盘整理" },
    "突破确认": { en: "Breakout confirmed", zh: "突破确认" },
    "回调买入": { en: "Buy on pullback", zh: "回调买入" },
    "止损触发": { en: "Stop loss triggered", zh: "止损触发" },
    "止盈触发": { en: "Take profit triggered", zh: "止盈触发" },
}

export function translateReason(reason: string, lang: Language): string {
    const mapping = reasonTranslations[reason]
    if (mapping) {
        return mapping[lang]
    }
    return reason // Return original if no translation found
}

export type Language = 'en' | 'zh'
export type TranslationKey = keyof typeof translations.en
