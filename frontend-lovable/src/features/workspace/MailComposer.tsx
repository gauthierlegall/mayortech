import {useEffect,useRef,useState} from 'react';
import {FileText,Save} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogDescription,DialogTitle} from '@/components/ui/dialog';
import {createDraftSaveQueue,draftPayload} from '../../../../web/mailbox.js';
import {registerPreserver} from './panel-lifecycle';

export interface MailComposerInitial {sourceId:string;to:string;cc?:string;subject:string;body:string;mode:'reply'|'reply-all'|'forward'|'suggested';warning?:string}
interface Props {api:any;open:boolean;onClose:()=>void;initial:MailComposerInitial;publicDemo:boolean}
interface Draft {id:string;to:string;cc:string;bcc:string;subject:string;body:string;in_reply_to:string|null;mode:'reply'|'forward';revision?:number;updated_at?:string}
type QueueFactory=(options:{api:any;getDraft:()=>Draft|null;isDirty:()=>boolean;markClean:()=>void;isServer:()=>boolean;saveLocal:(draft:Draft)=>void;onSaved:()=>void})=>{flush:()=>Promise<unknown>};
// The audited JavaScript helper calls saveLocal(current); its default callback
// has no parameters, so TypeScript needs the real boundary contract here.
const createQueue=createDraftSaveQueue as unknown as QueueFactory;
const localKey='travaux:mail-drafts:v1';
const emptyFields={to:'',cc:'',bcc:'',subject:'',body:''};

/** The same durable draft queue as the global mailbox. No sending transport. */
export function MailComposer({api,open,onClose,initial,publicDemo}:Props){
  const [fields,setFields]=useState(emptyFields),[status,setStatus]=useState(''),[error,setError]=useState(''),[access,setAccess]=useState<'loading'|'local'|'server'|'blocked'>('loading'),[closing,setClosing]=useState(false),[ccOpen,setCcOpen]=useState(false),[kind,setKind]=useState(initial.mode);
  const latest=useRef({api,onClose,initial,publicDemo});latest.current={api,onClose,initial,publicDemo};
  const current=useRef<Draft|null>(null),dirty=useRef(false),edited=useRef(false),timer=useRef<ReturnType<typeof setTimeout>|null>(null),flushRef=useRef<()=>Promise<void>>(async()=>{}),closingRef=useRef(false);
  useEffect(()=>{
    if(!open)return;
    const config=latest.current;let disposed=false,permitted=false;
    const draft:Draft={id:`local-${crypto.randomUUID()}`,to:config.initial.to||'',cc:config.initial.cc||'',bcc:'',subject:config.initial.subject||'',body:config.initial.body||'',in_reply_to:config.initial.sourceId||null,mode:config.initial.mode==='forward'?'forward':'reply'};
    current.current=draft;dirty.current=true;edited.current=false;closingRef.current=false;
    setFields({...draft});setKind(config.initial.mode);setCcOpen(Boolean(draft.cc));setError('');setStatus('Préparation du brouillon…');setAccess('loading');setClosing(false);
    const ready=config.publicDemo?Promise.resolve().then(()=>{permitted=true;if(!disposed){setAccess('local');setStatus('Brouillon conservé sur cet appareil.');}}):Promise.resolve().then(()=>config.api.mailboxFolders()).then(data=>{
      if(data?.capabilities?.server_drafts!==true||data?.capabilities?.can_compose!==true)throw new Error('Votre compte ne peut pas conserver de brouillon serveur.');
      permitted=true;if(!disposed){setAccess('server');setStatus('');}
    });
    void ready.catch(failure=>{if(!disposed){setAccess('blocked');setError(failure instanceof Error?failure.message:'Les droits de sauvegarde ne peuvent pas être vérifiés.');setStatus('Sauvegarde indisponible.');}});
    function saveLocal(value:Draft){
      let previous:unknown;try{previous=JSON.parse(localStorage.getItem(localKey)||'[]');}catch{previous=[];}
      const rows=Array.isArray(previous)?previous.filter(item=>item&&typeof item.id==='string'&&item.id!==value.id):[];
      localStorage.setItem(localKey,JSON.stringify([{...value,updated_at:new Date().toISOString()},...rows].slice(0,100)));
    }
    const queue=createQueue({api:config.api,getDraft:()=>current.current,isDirty:()=>dirty.current,markClean:()=>{dirty.current=false;},isServer:()=>!config.publicDemo,saveLocal,onSaved:()=>{if(!disposed){setStatus(config.publicDemo?'Brouillon conservé sur cet appareil.':'');setError('');}}});
    const flush=async()=>{
      if(timer.current)clearTimeout(timer.current);
      try{await ready;if(!dirty.current)return;if(!permitted)throw new Error('La sauvegarde du brouillon n’est pas autorisée.');if(!config.publicDemo&&current.current)draftPayload(current.current,true);if(!disposed)setStatus('Enregistrement…');await queue.flush();}
      catch(failure){if(!disposed){setError((failure instanceof Error?failure.message:'Le brouillon n’a pas pu être enregistré.')+' Votre texte reste dans ce formulaire.');setStatus('Modifications non enregistrées.');}throw failure;}
    };
    flushRef.current=flush;
    const unregister=registerPreserver(async()=>{if(!permitted&&!edited.current){try{await ready;}catch{return;}}await flush();},()=>dirty.current&&permitted);
    // Keep a prepared reply even if the user closes it without typing.
    void ready.then(()=>{if(!disposed)timer.current=setTimeout(()=>{void flush().catch(()=>{});},1000);}).catch(()=>{});
    return()=>{disposed=true;if(timer.current)clearTimeout(timer.current);unregister();flushRef.current=async()=>{};};
  // Deliberately initialize only when opening, never on a parent's rerender.
  },[open]);
  function change(key:keyof typeof emptyFields,value:string){
    if(!current.current)return;current.current[key]=value;dirty.current=true;edited.current=true;setFields(previous=>({...previous,[key]:value}));setError('');setStatus('Modifications en cours…');
    if(timer.current)clearTimeout(timer.current);timer.current=setTimeout(()=>{void flushRef.current().catch(()=>{});},publicDemo?0:900);
  }
  async function close(){
    if(closingRef.current)return;closingRef.current=true;setClosing(true);
    try{if(access!=='blocked'||edited.current)await flushRef.current();latest.current.onClose();}catch{/* Keep the fields and dialog open on any save failure. */}finally{closingRef.current=false;setClosing(false);}
  }
  const title=kind==='forward'?'Transférer le message':kind==='reply-all'?'Répondre à tous':kind==='suggested'?'Préparer une réponse':'Répondre au message';
  return <Dialog open={open} onOpenChange={value=>{if(!value)void close();}}><DialogContent className="mail-composer-dialog max-h-[90dvh] overflow-y-auto"><DialogTitle><FileText className="mr-2 inline" size={18}/>{title}</DialogTitle><DialogDescription>{kind==='suggested'?'Modèle de réponse à compléter et relire. Aucun texte n’est envoyé.':'Brouillon relié au message d’origine. Aucun envoi de courriel.'}</DialogDescription>{initial.warning&&<p role="status" className="text-sm text-amber-800">{initial.warning}</p>}<form className="form-stack" onSubmit={event=>{event.preventDefault();void flushRef.current().catch(()=>{});}}><label>À<input value={fields.to} onChange={event=>change('to',event.target.value)} maxLength={4000} disabled={closing||access==='loading'||access==='blocked'} autoComplete="off" placeholder="nom@exemple.fr"/></label><Button variant="link" type="button" size="sm" className="self-start" onClick={()=>setCcOpen(value=>!value)}>Cc / Cci</Button>{ccOpen&&<><label>Cc<input value={fields.cc} onChange={event=>change('cc',event.target.value)} maxLength={4000} disabled={closing||access==='loading'||access==='blocked'} autoComplete="off"/></label><label>Cci<input value={fields.bcc} onChange={event=>change('bcc',event.target.value)} maxLength={4000} disabled={closing||access==='loading'||access==='blocked'} autoComplete="off"/></label></>}<label>Objet<input value={fields.subject} onChange={event=>change('subject',event.target.value)} maxLength={500} disabled={closing||access==='loading'||access==='blocked'}/></label><label>Votre message<textarea rows={8} value={fields.body} onChange={event=>change('body',event.target.value)} maxLength={50000} disabled={closing||access==='loading'||access==='blocked'}/></label>{error&&<p role="alert" className="text-sm text-destructive">{error}</p>}{status&&<p role="status" className="muted-label">{status}</p>}<div className="flex flex-wrap gap-2"><Button type="submit" disabled={closing||access==='loading'||access==='blocked'}><Save size={15}/>Enregistrer le brouillon</Button><Button type="button" variant="outline" disabled={closing} onClick={()=>void close()}>{closing?'Enregistrement…':'Fermer'}</Button></div></form></DialogContent></Dialog>;
}

