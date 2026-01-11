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
    }
}

export type Language = 'en' | 'zh'
export type TranslationKey = keyof typeof translations.en
