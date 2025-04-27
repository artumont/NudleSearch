import { Search } from 'lucide-react' 

export default function SearchBar() {
    return (
        <div className="flex m-5 lg:w-2xl h-10">
            <div className="relative flex items-center w-full">
                <input
                    className="bg-surface w-full h-full rounded-2xl focus:ring-0 outline-0 text-primary placeholder:text-secondary px-4 pr-12"
                    placeholder="Search the web..."
                />
                <Search className="absolute right-4 text-secondary" size={20} />
            </div>
        </div>
    );
}