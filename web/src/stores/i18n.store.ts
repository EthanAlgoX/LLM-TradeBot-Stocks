import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { translations, Language, TranslationKey } from '../i18n/translations'

interface I18nStore {
    language: Language
    setLanguage: (lang: Language) => void
    t: (key: TranslationKey) => string
}

export const useI18n = create<I18nStore>()(
    persist(
        (set, get) => ({
            language: 'zh',

            setLanguage: (lang: Language) => {
                set({ language: lang })
            },

            t: (key: TranslationKey) => {
                const { language } = get()
                return translations[language][key] || key
            },
        }),
        {
            name: 'language-storage',
        }
    )
)
