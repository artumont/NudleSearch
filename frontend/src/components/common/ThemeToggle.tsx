'use client'

import { useTheme } from '../../providers/ThemeProvider'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme()

    return (
        <div className="fixed bottom-4 right-4 z-50">
            <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-surface transition-colors"
                aria-label="Toggle theme"
            >
                {theme === 'light' ? (
                    <Moon className="h-5 w-5 text-secondary" />
                ) : (
                    <Sun className="h-5 w-5 text-secondary" />
                )}
            </button>
        </div>
    )
}
