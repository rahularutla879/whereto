import { persistenceProxy } from "@/lib/persistence-proxy";
export const runtime = "nodejs";
export async function POST(request: Request) { return persistenceProxy("/api/plans/save", request); }
