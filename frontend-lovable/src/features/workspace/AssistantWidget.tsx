import {lazy,Suspense,useEffect,useRef,useState,type CSSProperties} from 'react';
import {MessageSquare,Minus,Settings2,Sparkles,X} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {assistantOpenEvent,openAssistant,type OpenAssistantDetail} from './assistant-events';
import {widgetViewport} from './assistant-widget-model.mjs';
import './assistant-widget.css';
export {openAssistant};
const ConversationBody=lazy(()=>import('./Conversation').then(module=>({default:module.ConversationBody})));

export function AssistantWidget({projectId}:{projectId?:string}){
 const [open,setOpen]=useState(false),[started,setStarted]=useState(false),[requestedProject,setRequestedProject]=useState<string|undefined>(projectId),[geometry,setGeometry]=useState(()=>widgetViewport({layoutHeight:window.innerHeight,visibleHeight:window.visualViewport?.height||window.innerHeight,offsetTop:window.visualViewport?.offsetTop||0,mobile:window.innerWidth<=640}));
 const trigger=useRef<HTMLButtonElement>(null),panel=useRef<HTMLElement>(null),returnFocus=useRef<HTMLElement|null>(null);
 const currentProject=useRef(projectId);currentProject.current=projectId;
 function show(context?:string){returnFocus.current=document.activeElement instanceof HTMLElement?document.activeElement:null;setRequestedProject(context||currentProject.current);setStarted(true);setOpen(true);}
 function reduce(restore=true){setOpen(false);if(restore)requestAnimationFrame(()=>{const target=returnFocus.current;target?.isConnected?target.focus():trigger.current?.focus();});}
 useEffect(()=>{
  const handler=(event:Event)=>show((event as CustomEvent<OpenAssistantDetail>).detail?.projectId);
  window.addEventListener(assistantOpenEvent,handler);return()=>window.removeEventListener(assistantOpenEvent,handler);
 },[]);
 useEffect(()=>{
  const measure=()=>setGeometry(widgetViewport({layoutHeight:window.innerHeight,visibleHeight:window.visualViewport?.height||window.innerHeight,offsetTop:window.visualViewport?.offsetTop||0,mobile:window.innerWidth<=640}));
  window.addEventListener('resize',measure);window.visualViewport?.addEventListener('resize',measure);window.visualViewport?.addEventListener('scroll',measure);
  return()=>{window.removeEventListener('resize',measure);window.visualViewport?.removeEventListener('resize',measure);window.visualViewport?.removeEventListener('scroll',measure);};
 },[]);
 useEffect(()=>{if(!open)return;requestAnimationFrame(()=>panel.current?.focus());const key=(event:KeyboardEvent)=>{if(event.key==='Escape'&&!event.defaultPrevented&&!document.querySelector('[role="dialog"][data-state="open"]')){event.preventDefault();reduce();}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[open]);
 const style={'--assistant-popup-bottom':`${geometry.bottom}px`,'--assistant-popup-height':`${geometry.height}px`,'--assistant-launcher-bottom':`${geometry.launcherBottom}px`} as CSSProperties;
 return <div className="assistant-widget" style={style} data-keyboard={geometry.keyboard?'true':'false'}>
  {started&&<section ref={panel} hidden={!open} inert={!open} role="dialog" aria-modal="false" id="assistant-popup" aria-labelledby="assistant-popup-title" tabIndex={-1} className="assistant-popup">
   <header className="assistant-popup-heading"><div><Sparkles size={18}/><h2 id="assistant-popup-title">Assistant</h2></div><div><Button variant="ghost" size="icon" title="Notifications et Telegram" aria-label="Notifications et Telegram" asChild><a href="#/assistant?settings=notifications" onClick={()=>reduce(false)}><Settings2 size={18}/></a></Button><Button variant="ghost" size="icon" aria-label="Réduire le chat" title="Réduire le chat" onClick={()=>reduce()}><Minus size={19}/></Button></div></header>
   <div className="assistant-popup-content"><Suspense fallback={<p role="status" className="assistant-popup-loading">Ouverture de votre conversation…</p>}><ConversationBody initialProjectId={requestedProject} suggestedProjectId={projectId||requestedProject} persistent floating onNavigate={()=>reduce(false)}/></Suspense></div>
  </section>}
  <Button ref={trigger} className="assistant-launcher" aria-label={open?'Réduire le chat':'Ouvrir le chat Assistant'} aria-expanded={open} aria-controls="assistant-popup" title={open?'Réduire le chat':'Ouvrir le chat Assistant'} onClick={()=>open?reduce():show(projectId)}>{open?<X size={22}/>:<MessageSquare size={22}/>}<span>Assistant</span></Button>
 </div>;
}
