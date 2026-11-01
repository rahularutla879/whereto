import {fragmentToken,TOKEN} from "./saved-plans";
export const TAB_SAVED_KEY="whereto.explicit-saved.v1";
// A remembered device link alone is availability, never navigation intent.
export function savedLaunchToken(hash:string,explicitView:boolean,tabReference:string|null){
 if(hash.startsWith('#saved='))return fragmentToken(hash);
 return explicitView&&tabReference&&TOKEN.test(tabReference)?tabReference:undefined;
}
