'use client'

import { Suspense } from 'react'
import NavBar from "@/components/search/NavBar";
import Loading from '@/components/common/Loading';

export default function Home() {
    return (
        <main className="flex flex-col w-full min-h-screen text-white bg-background">
            <nav className="w-full justify-between items-center">
                <Suspense fallback={<Loading />}>
                    <NavBar />
                </Suspense>
                <div className="w-full h-1 bg-surface"></div>
            </nav>
            <Loading/>
        </main>
    );
}