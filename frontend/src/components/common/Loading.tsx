export default function Loading() {
    const getColor = (index: number) => {
        if (index < 2) return 'text-red-500'
        if (index === 2) return 'text-blue-500'
        return 'text-purple-500'
    }

    return (
        <div className="flex items-center justify-center w-full h-screen">
            <div className="relative -space-y-3">
                <div className="flex space-x-2 text-4xl font-nudle">
                    {['n', 'u', 'd', 'l', 'e'].map((letter, index) => (
                        <span
                            key={letter}
                            className={`
                                transition-all
                                ${getColor(index)}
                            `}
                            style={{
                                opacity: 0.5,
                                animation: 'letterPulse 2.0s infinite'
                            }}
                        >
                            {letter}
                        </span>
                    ))}
                </div>
                <div className="absolute h-1 bg-amber-400 rounded-4xl animate-loading left-0 right-0 mx-auto -bottom-4"></div>
                <style jsx>{`
                    @keyframes letterPulse {
                        0% {
                            opacity: 0.3;
                            transform: scale(0.95);
                        }
                        50% {
                            opacity: 1;
                            transform: scale(1.1);
                        }
                        100% {
                            opacity: 0.3;
                            transform: scale(0.95);
                        }
                    }

                    @keyframes loading {
                        0% {
                            width: 5%;
                        }
                        50% {
                            width: 100%;
                        }
                        100% {
                            width: 5%;
                        }
                    }

                    .animate-loading {
                        animation: loading 2s infinite ease-in-out;
                    }
                `}</style>
            </div>
        </div>
    );
}
