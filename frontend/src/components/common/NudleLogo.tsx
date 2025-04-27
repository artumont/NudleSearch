interface NudleLogoProps {
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
}

export default function NudleLogo({ size = 'md' }: NudleLogoProps) {
    const sizeClasses = {
        sm: 'text-2xl',
        md: 'text-4xl',
        lg: 'text-6xl',
        xl: 'text-8xl',
        xxl: 'text-[10rem]' 
    };

    const spaceClasses = {
        sm: '',
        md: '',
        lg: '',
        xl: '-space-y-1',
        xxl: '-space-y-12'
    };

    return (
        <div className={`w-auto h-auto flex flex-col ${spaceClasses[size]} items-center justify-center`}>
            <div className={`${sizeClasses[size]} font-nudle`}>
                <span className="text-red-500">nu</span>
                <span className="text-blue-500">d</span>
                <span className="text-purple-500">le</span>
            </div>
            <div className="w-full h-2 bg-amber-400 rounded-4xl"></div>
        </div>
    );
}