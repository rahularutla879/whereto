import registry from '../data/mock-venues.json';
// Shared with Python's catalog/schema checks; no second maintained activity list.
export function supportedActivityGroups(){
 const values=Object.values(registry.catalog);
 return [
  {title:'Places and activities',scheduled:false,items:values.filter(item=>!('eventStart' in item)).map(item=>({label:item.label}))},
  {title:'Sports and performance venues',scheduled:true,items:values.filter(item=>'eventStart' in item).map(item=>({label:item.label}))},
 ];
}
