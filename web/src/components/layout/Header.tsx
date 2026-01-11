import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Calendar, Clock, TrendingUp, Languages } from 'lucide-react'
import { useI18n } from '../../stores/i18n.store'

const navItems = [
    { path: '/', label: 'dashboard', icon: BarChart3 },
    { path: '/today', label: 'today', icon: TrendingUp },
    { path: '/yesterday', label: 'yesterday', icon: Clock },
]

export default function Header() {
    const location = useLocation()
    const { language, setLanguage, t } = useI18n()

    return (
        <header className="bg-dark-200 border-b border-gray-800">
            <div className="container mx-auto px-4">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center gap-2">
                        <BarChart3 className="w-8 h-8 text-primary-500" />
                        <span className="text-xl font-bold text-white">{t('appName')}</span>
                    </div>

                    <div className="flex items-center gap-4">
                        <nav className="flex gap-1">
                            {navItems.map((item) => {
                                const isActive = location.pathname === item.path
                                const Icon = item.icon
                                return (
                                    <Link
                                        key={item.path}
                                        to={item.path}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${isActive
                                            ? 'bg-primary-600 text-white'
                                            : 'text-gray-400 hover:text-white hover:bg-dark-100'
                                            }`}
                                    >
                                        <Icon className="w-4 h-4" />
                                        {t(item.label as any)}
                                    </Link>
                                )
                            })}
                        </nav>

                        {/* Language Switcher */}
                        <button
                            onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-dark-100 transition-colors"
                            title="Switch Language"
                        >
                            <Languages className="w-4 h-4" />
                            <span className="text-sm font-medium">{language === 'en' ? '中文' : 'EN'}</span>
                        </button>
                    </div>
                </div>
            </div>
        </header>
    )
}
