import axios from 'axios'

const api = axios.create({
    baseURL: '/api/v1',
    timeout: 10000,
})

export type DataMode = 'live' | 'backtest'

export interface KPI {
    total_return_pct: number
    avg_daily_return_pct: number
    win_rate: number
    total_trades: number
}

export interface DailyPerformance {
    date: string
    daily_return: number
    cum_return: number
    trades: number
    win_rate: number
    top_winner: { symbol: string; pnl_pct: number } | null
    top_loser: { symbol: string; pnl_pct: number } | null
}

export interface Pick {
    symbol: string
    action: string
    reason: string
    or15_close: number
    entry_price: number
    max_potential_pct: number
}

export interface Trade {
    symbol: string
    entry_price: number
    exit_price: number
    pnl_pct: number
    exit_reason: string
    holding_time: string
}

export interface DashboardData {
    session: string
    kpi: KPI
    performance_7d: DailyPerformance[]
    today_picks: Pick[]
    yesterday_recap: Trade[]
    yesterday_summary: {
        total: number
        wins: number
        losses: number
        win_rate: number
        total_pnl_pct: number
    }
}

export async function fetchDashboard(preset: string = 'all', mode: DataMode = 'backtest'): Promise<DashboardData> {
    const { data } = await api.get<DashboardData>('/dashboard', { params: { preset, mode } })
    return data
}

export async function fetchTodayPicks(preset: string = 'all', mode: DataMode = 'backtest') {
    const { data } = await api.get('/picks/today', { params: { preset, mode } })
    return data
}

export async function fetchYesterdayRecap(preset: string = 'all', mode: DataMode = 'backtest') {
    const { data } = await api.get('/recap/yesterday', { params: { preset, mode } })
    return data
}

export async function fetchRollingPerformance(days: number = 7, preset: string = 'all', mode: DataMode = 'backtest') {
    const { data } = await api.get('/performance/rolling', { params: { days, preset, mode } })
    return data
}

export default api

