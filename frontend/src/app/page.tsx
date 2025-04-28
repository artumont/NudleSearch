import NudleLogo from "@/components/common/NudleLogo";
import SearchBar from "@/components/common/SearchBar";

export default function Home() {
    return (
        <main className="flex flex-col items-center w-full min-h-screen text-white bg-background">
            <NudleLogo size="xxl" redirect="" />
            <SearchBar />
        </main>
    );
}
