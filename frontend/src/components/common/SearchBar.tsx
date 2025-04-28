'use client'

import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

interface SearchProps {
    query?: string
}

export default function SearchBar({query = ''}: SearchProps) {
    const router = useRouter()
    const [searchQuery, setSearchQuery] = useState(query)

    const handleSearch = () => {
        if (searchQuery.trim()) {
            const formattedQuery = encodeURIComponent(searchQuery.trim())
            router.push(`/search?q=${formattedQuery}`)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSearch()
        }
    }

    return (
        <div className="flex m-5 w-sm md:w-lg lg:w-2xl h-10">
            <div className="relative flex items-center w-full">
                <input
                    id="search"
                    className="bg-surface w-full h-full rounded-2xl focus:ring-0 outline-0 text-primary placeholder:text-secondary px-4 pr-12"
                    placeholder="Search the web..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                />
                <Search className="absolute right-4 text-secondary hover:cursor-pointer" onClick={handleSearch} size={20} />
            </div>
        </div>
    );
}