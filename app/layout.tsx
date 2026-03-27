import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';

const font = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
  variable: '--font-plus-jakarta',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://noor.app'),
  title: 'Noor — Islamic Companion Apps',
  description:
    'Noor builds modern Islamic companion apps. Start your daily Quran journey with the Tafsir Bot.',
  openGraph: {
    title: 'Noor — Islamic Companion Apps',
    description: 'Noor builds modern Islamic companion apps.',
    url: 'https://noor.app',
    type: 'website',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${font.variable} font-sans antialiased bg-noor-alabaster`}>
        {children}
      </body>
    </html>
  );
}
