import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type DataMode = 'live' | 'backtest'

interface ModeStore {
    mode: DataMode
    setMode: (mode: DataMode) => void
    toggleMode: () => void
}

export const useModeStore = create<ModeStore>()(
    persist(
        (set, get) => ({
            mode: 'backtest', // Default to backtest

            setMode: (mode: DataMode) => {
                set({ mode })
            },

            toggleMode: () => {
                const current = get().mode
                set({ mode: current === 'live' ? 'backtest' : 'live' })
            },
        }),
        {
            name: 'data-mode-storage',
        }
    )
)
