import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  referrer: "no-referrer",
  title: "where to? — Less planning. More hanging out.",
  description: "Turn your group chat into a great day out. Try the Where To? local demo outing planner with fictional Baltimore venues.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Extensions may add attributes to this static body before hydration. This
  // one-level escape hatch does not suppress mismatches in child components.
  return <html lang="en"><body suppressHydrationWarning>{children}</body></html>;
}
