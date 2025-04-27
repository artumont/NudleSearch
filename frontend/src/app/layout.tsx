import type { Metadata } from "next";
import { hoolisterFont } from "@/fonts/fonts";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
    metadataBase: new URL('https://nudle.artumont.online'),
    title: {
        default: "NudleSearch - Web Search Engine",
        template: "%s | NudleSearch"
    },
    description: "A faithful recreation of the Nudle search engine from Watch Dogs 2, built from scratch. Fast, private, and accurate web search.",
    keywords: ["search engine", "nudle", "watch dogs", "web search", "privacy", "fast search", "secure search"],
    authors: [{ name: "Artu (@artumont)" }],
    creator: "Artu (@artumont)",
    publisher: "NudleSearch",
    openGraph: {
        type: "website",
        locale: "en_US",
        url: "https://nudle.vercel.app",
        title: "NudleSearch - Web Search Engine",
        description: "A faithful recreation of the Nudle search engine from Watch Dogs 2, built from scratch. Fast, private, and accurate web search.",
        siteName: "NudleSearch",
    },
    twitter: {
        card: "summary_large_image",
        title: "NudleSearch - Web Search Engine",
        description: "A faithful recreation of the Nudle search engine from Watch Dogs 2, built from scratch. Fast, private, and accurate web search.",
        creator: "@NudleSearch",
        site: "@NudleSearch"
    },
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            'max-video-preview': -1,
            'max-image-preview': 'large',
            'max-snippet': -1,
        },
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={`${hoolisterFont.variable} antialiased`}>
                <ThemeProvider>
                    {children}
                    <ThemeToggle />
                </ThemeProvider>
            </body>
        </html>
    );
}
