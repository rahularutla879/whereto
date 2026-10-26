import { providerProxy } from "../../../../lib/provider-proxy";
export const runtime = "nodejs";
export async function POST(request: Request) { return providerProxy("/api/plans/options", request); }
