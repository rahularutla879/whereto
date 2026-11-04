/** Official universal Maps URLs. Only public establishment identities belong here.
 * Missing origin uses Maps' location picker/current location; missing destination
 * lets the user enter their original start in Maps. Neither sends our private start.
 */
export function mapsDirections(origin:string|null|undefined,destination:string|null|undefined,mode:string){
 if((!origin&&!destination)||origin&&origin===destination)return null;
 const params=new URLSearchParams({api:'1',travelmode:['walk','walking','WALK'].includes(mode)?'walking':'driving'});
 if(origin){params.set('origin','Place');params.set('origin_place_id',origin);}
 if(destination){params.set('destination','Place');params.set('destination_place_id',destination);}
 return `https://www.google.com/maps/dir/?${params}`;
}
