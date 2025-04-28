'use client'

import NudleLogo from "@/components/common/NudleLogo";
import SearchBar from "@/components/common/SearchBar";
import { useSearchParams } from "next/navigation";
import { Cog } from "lucide-react";

export default function NavBar() {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';  

    return (
        <div className="flex px-5 pb-2 w-full justify-between items-center">
            <div className="flex">
                <NudleLogo size="lg" />
                <SearchBar query={query}/>
            </div>
            <button className="flex items-center justify-center w-10 h-10 rounded-xl hover:bg-surface transition-colors text-secondary">
                <Cog />
            </button>
        </div>
    );
}