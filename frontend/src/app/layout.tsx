import "./globals.css";

export const metadata = {
    title: "Mix Assistant AI - Studio Engineer Consultation",
    description: "AI-powered audio engineering feedback and production advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {

    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet" />
            </head>
            <body>
                <div id="root">{children}</div>
            </body>
        </html>
    );
}
