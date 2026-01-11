import useSWR from 'swr'
import {
    BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ComposedChart
} from 'recharts'
import { TrendingUp, TrendingDown, BarChart3, Target, Zap } from 'lucide-react'
import { fetchDashboard, DashboardData } from '../utils/api'
import { useI18n } from '../stores/i18n.store'
import { useModeStore } from '../stores/mode.store'

export default function Dashboard() {
    const { t } = useI18n()
    const { mode } = useModeStore()
    const { data, error, isLoading } = useSWR<DashboardData>(['/dashboard', mode], () => fetchDashboard('all', mode))

    if (isLoading) {
        return <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
    }

    if (error || !data) {
        return <div className="text-center text-red-500 p-8">Failed to load dashboard data</div>
    }

    const chartData = [...data.performance_7d].reverse().map(d => ({
        date: d.date.slice(5), // MM-DD
        return: +(d.daily_return * 100).toFixed(2),
        cumulative: +(d.cum_return * 100).toFixed(2),
    }))

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white">📊 {t('appName')}</h1>
                <span className="text-gray-400">{t('session')}: {data.session}</span>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
                <KPICard
                    label={t('totalReturn')}
                    value={`${data.kpi.total_return_pct >= 0 ? '+' : ''}${data.kpi.total_return_pct}%`}
                    icon={<TrendingUp className="w-6 h-6" />}
                    positive={data.kpi.total_return_pct >= 0}
                />
                <KPICard
                    label={t('winRate')}
                    value={`${(data.kpi.win_rate * 100).toFixed(1)}%`}
                    icon={<Target className="w-6 h-6" />}
                />
                <KPICard
                    label={t('totalTrades')}
                    value={data.kpi.total_trades.toString()}
                    icon={<BarChart3 className="w-6 h-6" />}
                />
                <KPICard
                    label={t('avgDaily')}
                    value={`${data.kpi.avg_daily_return_pct >= 0 ? '+' : ''}${data.kpi.avg_daily_return_pct}%`}
                    icon={<Zap className="w-6 h-6" />}
                    positive={data.kpi.avg_daily_return_pct >= 0}
                />
            </div>

            {/* 7D Performance Chart */}
            <div className="card">
                <h2 className="text-lg font-semibold text-white mb-4">📈 {t('performance7d')}</h2>
                <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="date" stroke="#9CA3AF" />
                        <YAxis stroke="#9CA3AF" tickFormatter={(v) => `${v}%`} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #374151' }}
                            labelStyle={{ color: '#fff' }}
                        />
                        <Bar dataKey="return" fill="#0ea5e9" name="Daily Return" />
                        <Line type="monotone" dataKey="cumulative" stroke="#22c55e" strokeWidth={2} name="Cumulative" />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* Today Picks & Yesterday Recap */}
            <div className="grid grid-cols-2 gap-6">
                {/* Today Picks */}
                <div className="card">
                    <h2 className="text-lg font-semibold text-white mb-4">🎯 {t('todayPicks')} ({data.today_picks.length})</h2>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {data.today_picks.length === 0 ? (
                            <p className="text-gray-400">{t('noPicksToday')}</p>
                        ) : (
                            data.today_picks.map((pick, i) => (
                                <div key={i} className="stock-card flex items-center justify-between">
                                    <div>
                                        <span className="font-bold text-white">{pick.symbol}</span>
                                        <span className="ml-2 text-xs px-2 py-1 bg-green-600/20 text-green-400 rounded">
                                            {pick.action}
                                        </span>
                                    </div>
                                    <span className="text-gray-400 text-sm truncate max-w-[200px]" title={pick.reason}>
                                        {pick.reason.slice(0, 40)}...
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Yesterday Recap */}
                <div className="card">
                    <h2 className="text-lg font-semibold text-white mb-4">
                        📋 {t('yesterdayRecap')}
                        <span className={`ml-2 ${data.yesterday_summary.total_pnl_pct >= 0 ? 'positive' : 'negative'}`}>
                            ({data.yesterday_summary.total_pnl_pct >= 0 ? '+' : ''}{data.yesterday_summary.total_pnl_pct}%)
                        </span>
                    </h2>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {data.yesterday_recap.length === 0 ? (
                            <p className="text-gray-400">{t('noTradesYesterday')}</p>
                        ) : (
                            data.yesterday_recap.map((trade, i) => (
                                <div key={i} className="stock-card flex items-center justify-between">
                                    <span className="font-bold text-white">{trade.symbol}</span>
                                    <div className="flex items-center gap-4">
                                        <span className="text-gray-400 text-sm">${trade.entry_price} → ${trade.exit_price}</span>
                                        <span className={trade.pnl_pct >= 0 ? 'positive' : 'negative'}>
                                            {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct}%
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

function KPICard({ label, value, icon, positive }: {
    label: string;
    value: string;
    icon: React.ReactNode;
    positive?: boolean
}) {
    return (
        <div className="kpi-card">
            <div className="flex justify-center mb-2 text-primary-500">{icon}</div>
            <div className={`text-2xl font-bold ${positive === true ? 'positive' : positive === false ? 'negative' : 'text-white'}`}>
                {value}
            </div>
            <div className="text-gray-400 text-sm mt-1">{label}</div>
        </div>
    )
}
