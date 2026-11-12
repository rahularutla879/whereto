// Bounded, duplicate-aware JSON for signed identity documents. Not executable data.
export function identityJSON(raw:string):unknown {
 if(raw.length>100000)throw Error('Identity JSON bound');let i=0;
 const ws=()=>{while(/\s/.test(raw[i]??'')&&i<raw.length)i++;};
 function string(){const start=i++;while(i<raw.length){if(raw[i]==='\\'){i+=2;continue;}if(raw[i++]==='"')return JSON.parse(raw.slice(start,i)) as string;}throw Error('Identity string');}
 function value(depth:number):unknown {
  if(depth>32)throw Error('Identity depth');ws();const ch=raw[i];
  if(ch==='"')return string();
  if(ch==='{'||ch==='['){i++;const object=ch==='{',close=object?'}':']',keys=new Set<string>();ws();if(raw[i]===close){i++;return;}
   while(i<raw.length){if(object){ws();if(raw[i]!=='"')throw Error();const k=string();if(keys.has(k))throw Error('Duplicate identity key');keys.add(k);ws();if(raw[i++]!==':')throw Error();}value(depth+1);ws();if(raw[i]===close){i++;return;}if(raw[i++]!==',')throw Error();}throw Error();}
  const m=/^(?:null|true|false|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(raw.slice(i));if(!m)throw Error();i+=m[0].length;
 }
 value(0);ws();if(i!==raw.length)throw Error('Identity trailing data');return JSON.parse(raw);
}
