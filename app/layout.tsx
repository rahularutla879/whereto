import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "where to? — Less planning. More hanging out.",
  description: "Turn your group chat into a great day out. Try the Where To? local demo outing planner with fictional Baltimore venues.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
