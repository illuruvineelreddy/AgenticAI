import type { Metadata } from 'next'
import './globals.css'
import Providers from '@/lib/providers'

export const metadata: Metadata = {
  title: 'Project Astra - AI Trading Platform',
  description: 'Agentic AI Trading Platform for Indian Markets',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
