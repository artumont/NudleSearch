'use client'

import { useTheme } from '../../providers/ThemeProvider'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme()

    return (
        <div className="absolute bottom-4 right-4">
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
