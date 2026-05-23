import type { Metadata } from 'next'

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
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
