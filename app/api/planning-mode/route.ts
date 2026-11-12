import { providerProxy } from "../../../lib/provider-proxy";
export const runtime = "nodejs";
export function GET():Promise<Response>;
export function GET(request:Request):Promise<Response>;
export async function GET(request?:Request) { return providerProxy("/api/planning-mode",undefined,request); }
