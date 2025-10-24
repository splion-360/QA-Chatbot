import type { Metadata } from "next";
import { IBM_Plex_Mono } from "next/font/google";
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { Toaster } from 'react-hot-toast';
import ThemeInitializer from './components/ThemeInitializer';
import "./globals.css";

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "QA Chatbot",
  description: "AI-powered question and answer chatbot",
  icons: {
    icon: "/mascot.png",
  },
  other: {
    'theme-init': '/theme-init.js',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script src="/theme-init.js" />
      </head>
      <body
        className={`${ibmPlexMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <ThemeInitializer />
        <AppRouterCacheProvider>
          {children}
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#ffffff',
                color: '#000000',
                border: '1px solid #e0e0e0',
                borderRadius: '8px',
                fontSize: '14px',
              },
              success: {
                style: {
                  background: '#4caf50',
                  color: '#ffffff',
                },
                iconTheme: {
                  primary: '#ffffff',
                  secondary: '#4caf50',
                },
              },
              error: {
                style: {
                  background: '#f44336',
                  color: '#ffffff',
                },
                iconTheme: {
                  primary: '#ffffff',
                  secondary: '#f44336',
                },
              },
            }}
          />
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
