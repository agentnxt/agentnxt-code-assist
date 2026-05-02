import type { Metadata } from 'next';
import './styles.css';

export const metadata: Metadata = {
  title: 'AGenNext Code Assist',
  description: 'Optional Next.js chat UI for AGenNext Code Assist',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
