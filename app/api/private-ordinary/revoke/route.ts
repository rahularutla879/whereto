import {privateRoute} from '@/lib/private-server-boundary';
export const runtime='nodejs';
export async function POST(request:Request){return privateRoute('/api/private-ordinary/revoke',request)??Response.json({},{status:404,headers:{'Cache-Control':'no-store'}});}
