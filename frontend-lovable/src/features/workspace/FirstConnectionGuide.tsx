import {useEffect} from 'react';
import {useWorkspace} from './context';
export function FirstConnectionGuide(){
 const {api,session}=useWorkspace();
 useEffect(()=>{if(!session?.auth_required)return;let active=true;api.onboarding().then((value:any)=>{if(active&&!value.completed&&!value.dismissed&&!location.hash.startsWith('#/connexion'))location.replace('#/connexion');}).catch(()=>{});return()=>{active=false;};},[api,session?.auth_required]);
 return null;
}
