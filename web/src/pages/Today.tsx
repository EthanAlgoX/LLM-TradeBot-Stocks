import useSWR from 'swr'
import { fetchTodayPicks, Pick } from '../utils/api'
import { useI18n } from '../stores/i18n.store'
import { useModeStore } from '../stores/mode.store'

export default function Today() {
    const { t, tr } = useI18n()
    const { mode } = useModeStore()
    const { data, error, isLoading } = useSWR(['/picks/today', mode], () => fetchTodayPicks('all', mode))

    if (isLoading) {
        return <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
    }

    if (error) {
        return <div className="text-center text-red-500 p-8">Failed to load today's picks</div>
    }

    const picks: Pick[] = data?.picks || []

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white">🎯 {t('todayPicksTitle')}</h1>
                <span className="text-gray-400">{data?.date}</span>
            </div>

            {picks.length === 0 ? (
                <div className="card text-center py-12">
                    <p className="text-gray-400 text-lg">{t('noPicksToday')}</p>
                    <p className="text-gray-500 mt-2">{t('checkBackAfterOpen')}</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {picks.map((pick, i) => (
                        <div key={i} className="card hover:border-primary-500 transition-colors">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-xl font-bold text-white">{pick.symbol}</span>
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${pick.action === 'BUY'
                                    ? 'bg-green-600/20 text-green-400 border border-green-600'
                                    : 'bg-gray-600/20 text-gray-400 border border-gray-600'
                                    }`}>
                                    {pick.action === 'BUY' ? t('buy') : pick.action === 'SELL' ? t('sell') : t('wait')}
                                </span>
                            </div>

                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">{t('or15Close')}</span>
                                    <span className="text-white">${pick.or15_close?.toFixed(2) || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">{t('entryPrice')}</span>
                                    <span className="text-white">${pick.entry_price?.toFixed(2) || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">{t('maxPotential')}</span>
                                    <span className="positive">+{pick.max_potential_pct?.toFixed(1) || 0}%</span>
                                </div>
                            </div>

                            <div className="mt-4 pt-3 border-t border-gray-700">
                                <p className="text-gray-300 text-sm">{tr(pick.reason)}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
