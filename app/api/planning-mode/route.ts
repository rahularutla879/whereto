import { providerProxy } from "../../../lib/provider-proxy";
export const runtime = "nodejs";
export async function GET() { return providerProxy("/api/planning-mode"); }
