import {useEffect,useRef,useState} from 'react';
import {LogOut} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {preservePanels} from './panel-lifecycle';
import {scopeNativeActions} from './native-actions';
import {observeWorkspaceIdentity,workspaceIdentity,workspaceIdentityEvent} from './workspace-scope.mjs';
import {canLogoutWorkspace,logoutWorkspace} from './workspace-logout-model.mjs';
import './workspace-logout.css';

export function WorkspaceLogout(){
 const {session,api}=useWorkspace();
 const [leaving,setLeaving]=useState(false),[error,setError]=useState('');
 const alive=useRef(true),inFlight=useRef(false),currentIdentity=useRef(workspaceIdentity(session));
 const identity=workspaceIdentity(session);
 useEffect(()=>{currentIdentity.current=identity;},[identity]);
 useEffect(()=>{
  alive.current=true;
  const changed=(event:Event)=>{if(event instanceof CustomEvent&&typeof event.detail?.key==='string')currentIdentity.current=event.detail.key;};
  window.addEventListener(workspaceIdentityEvent,changed);
  return()=>{alive.current=false;window.removeEventListener(workspaceIdentityEvent,changed);};
 },[]);
 if(!canLogoutWorkspace(session))return null;

 async function leave(){
  if(inFlight.current)return;
  inFlight.current=true;setLeaving(true);setError('');
  const initialIdentity=currentIdentity.current;
  const assertCurrent=()=>{if(!alive.current||currentIdentity.current!==initialIdentity)throw Error('Le compte actif a changé.');};
  try{
   await logoutWorkspace({session,api,preserve:preservePanels,assertCurrent,
    onRevoked:()=>{const anonymous={authenticated:false};scopeNativeActions(workspaceIdentity(anonymous),[]);observeWorkspaceIdentity(anonymous);},
    redirect:()=>window.location.assign('/connexion.html')});
  }catch(failure){
   inFlight.current=false;
   if(!alive.current||currentIdentity.current!==initialIdentity)return;
   setLeaving(false);setError(failure instanceof Error?failure.message:'La déconnexion n’a pas abouti. Réessayez.');
  }
 }

 return <div className="workspace-logout" aria-busy={leaving}>
  <Button className="workspace-logout-button" type="button" variant="ghost" disabled={leaving} onClick={()=>void leave()}>
   <LogOut size={18} aria-hidden="true"/><span aria-live="polite">{leaving?'Déconnexion…':'Se déconnecter'}</span>
  </Button>
  {error&&<p className="workspace-logout-error" role="alert">{error}</p>}
 </div>;
}
