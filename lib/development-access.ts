import {developmentOriginHeaders} from './development-origin';
export function diagnosticBoundary(request:Request):Record<string,string>|null{
 if(process.env.NODE_ENV!=="development")return null;
 try{
  const host=request.headers.get('host')??new URL(request.url).host;
  if(!['localhost','127.0.0.1','[::1]'].includes(new URL(`http://${host}`).hostname))return null;
  const boundary=developmentOriginHeaders(request);
  if(boundary['X-WhereTo-Proxied']!=='0')return null;
  const origin=request.headers.get('origin');
  if(origin&&origin!==`${new URL(request.url).protocol}//${host}`)return null;
  return boundary;
 }catch{return null;}
}
