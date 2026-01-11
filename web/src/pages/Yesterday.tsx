import useSWR from 'swr'
import { fetchYesterdayRecap, Trade } from '../utils/api'

export default function Yesterday() {
    const { data, error, isLoading } = useSWR('/recap/yesterday', () => fetchYesterdayRecap())

    if (isLoading) {
        return <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
    }

    if (error) {
        return <div className="text-center text-red-500 p-8">Failed to load yesterday's recap</div>
    }

    const trades: Trade[] = data?.trades || []
    const summary = data?.summary || { total: 0, wins: 0, losses: 0, win_rate: 0, total_pnl_pct: 0 }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white">📋 Yesterday's Recap</h1>
                <span className="text-gray-400">{data?.date}</span>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4">
                <div className="kpi-card">
                    <div className="text-gray-400 text-sm">Total Trades</div>
                    <div className="text-2xl font-bold text-white">{summary.total}</div>
                </div>
                <div className="kpi-card">
                    <div className="text-gray-400 text-sm">Wins / Losses</div>
                    <div className="text-2xl font-bold">
                        <span className="positive">{summary.wins}</span>
                        <span className="text-gray-500"> / </span>
                        <span className="negative">{summary.losses}</span>
                    </div>
                </div>
                <div className="kpi-card">
                    <div className="text-gray-400 text-sm">Win Rate</div>
                    <div className="text-2xl font-bold text-white">{(summary.win_rate * 100).toFixed(1)}%</div>
                </div>
                <div className="kpi-card">
                    <div className="text-gray-400 text-sm">Total PnL</div>
                    <div className={`text-2xl font-bold ${summary.total_pnl_pct >= 0 ? 'positive' : 'negative'}`}>
                        {summary.total_pnl_pct >= 0 ? '+' : ''}{summary.total_pnl_pct}%
                    </div>
                </div>
            </div>

            {/* Trades Table */}
            <div className="card overflow-hidden">
                <h2 className="text-lg font-semibold text-white mb-4">Trade Details</h2>

                {trades.length === 0 ? (
                    <p className="text-gray-400 text-center py-8">No trades yesterday</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                                    <th className="pb-3 font-medium">Symbol</th>
                                    <th className="pb-3 font-medium">Entry</th>
                                    <th className="pb-3 font-medium">Exit</th>
                                    <th className="pb-3 font-medium">PnL</th>
                                    <th className="pb-3 font-medium">Exit Reason</th>
                                    <th className="pb-3 font-medium">Duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map((trade, i) => (
                                    <tr key={i} className="border-b border-gray-800 hover:bg-dark-100">
                                        <td className="py-3 font-bold text-white">{trade.symbol}</td>
                                        <td className="py-3 text-gray-300">${trade.entry_price?.toFixed(2)}</td>
                                        <td className="py-3 text-gray-300">${trade.exit_price?.toFixed(2)}</td>
                                        <td className={`py-3 font-medium ${trade.pnl_pct >= 0 ? 'positive' : 'negative'}`}>
                                            {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct?.toFixed(2)}%
                                        </td>
                                        <td className="py-3">
                                            <span className={`px-2 py-1 rounded text-xs ${trade.exit_reason === 'TAKE_PROFIT' ? 'bg-green-600/20 text-green-400' :
                                                    trade.exit_reason === 'STOP_LOSS' ? 'bg-red-600/20 text-red-400' :
                                                        'bg-gray-600/20 text-gray-400'
                                                }`}>
                                                {trade.exit_reason}
                                            </span>
                                        </td>
                                        <td className="py-3 text-gray-400">{trade.holding_time}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
