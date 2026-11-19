import {useEffect,useRef,useState} from 'react';
import {Paperclip,Upload,X} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {preservePanels,registerPreserver} from './panel-lifecycle';
import {documentUploadAccess,prepareDocumentUpload,uploadReceipt,validateUploadFile} from './document-upload-model.mjs';
import './document-upload.css';

type Payload={filename:string;content_base64:string;client_id:string};
type Receipt=ReturnType<typeof uploadReceipt>;

/** The selected file and retry key stay in memory; no document is put in browser storage. */
export function DocumentUpload({projectId,onUploaded}:{projectId:string;onUploaded:()=>Promise<void>}){
 const {api,session,bootstrap}=useWorkspace();
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[receipt,setReceipt]=useState<Receipt|null>(null),[needsReload,setNeedsReload]=useState(false);
 const input=useRef<HTMLInputElement>(null),alive=useRef(true),working=useRef(false),attempt=useRef<{file:File;clientId:string;payload?:Payload}|null>(null);
 useEffect(()=>{alive.current=true;const unregister=registerPreserver(()=>{if(working.current)throw Error('Attendez la fin du dépôt de document avant de quitter ce dossier.');},()=>working.current);return()=>{alive.current=false;unregister();attempt.current=null;};},[]);
 const allowed=documentUploadAccess(session,bootstrap);
 function choose(next:File|null){
  if(working.current)return;
  setReceipt(null);setNeedsReload(false);const problem=next?validateUploadFile(next):'';setError(problem);setFile(problem?null:next);
  attempt.current=next&&!problem?{file:next,clientId:crypto.randomUUID()}:null;
  if(problem&&input.current)input.current.value='';
 }
 async function reload(){
  if(working.current)return;working.current=true;setBusy(true);setError('');
  let updated=false;
  try{await onUploaded();updated=true;if(alive.current)setNeedsReload(false);}catch{if(alive.current)setError('L’original est conservé, mais la liste n’a pas pu être actualisée. Réessayez de recharger le dossier.');}finally{working.current=false;if(alive.current)setBusy(false);if(updated)window.dispatchEvent(new CustomEvent('travaux:documents-changed',{detail:{projectId}}));}
 }
 async function submit(){
  if(!allowed||!attempt.current||working.current||needsReload)return;
  const current=attempt.current;working.current=true;setBusy(true);setError('');
  let stored=false,updated=false;
  try{
   current.payload??=await prepareDocumentUpload(current.file,current.clientId);
   const received=uploadReceipt(await api.uploadProjectDocument(projectId,current.payload),projectId);stored=true;
   if(alive.current){setReceipt(received);setFile(null);setNeedsReload(true);attempt.current=null;if(input.current)input.current.value='';}
   await onUploaded();updated=true;if(alive.current)setNeedsReload(false);
  }catch(cause){if(alive.current)setError(stored?'L’original est conservé, mais le dossier n’a pas pu être actualisé. Rechargez la liste ci-dessous.':`${cause instanceof Error?cause.message:'Le dépôt n’a pas pu être confirmé.'} Le fichier reste sélectionné ; réessayez pour vérifier ce même dépôt.`);}
  finally{working.current=false;if(alive.current)setBusy(false);if(updated)window.dispatchEvent(new CustomEvent('travaux:documents-changed',{detail:{projectId}}));}
 }
 if(!allowed)return session?.public_demo?<p className="document-upload-note">Le dépôt de fichiers est réservé à un espace privé. Cette démonstration utilise ses pièces fictives.</p>:null;
 return <div className="document-upload" aria-busy={busy}>
  <form onSubmit={event=>{event.preventDefault();void submit();}}>
   <label className="document-upload-picker"><Paperclip size={16}/><span>Ajouter un document</span><input ref={input} type="file" accept=".pdf,.docx,.txt,.md,.csv" aria-label="Choisir un document à ajouter au dossier" disabled={busy||needsReload} onChange={event=>choose(event.target.files?.[0]||null)}/></label>
   <small>PDF, DOCX, TXT, MD ou CSV · 5 Mo maximum</small>
   {file&&<div className="document-upload-selection"><span>{file.name}<small>{file.size<1000?`${file.size} octets`:`${new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(file.size/1000)} ko`}</small></span><Button type="button" variant="ghost" size="icon" aria-label="Retirer le fichier sélectionné" disabled={busy} onClick={()=>{choose(null);if(input.current)input.current.value='';}}><X size={16}/></Button><Button type="submit" size="sm" disabled={busy||needsReload}><Upload size={15}/>{busy?'Dépôt et analyse…':'Ajouter au dossier'}</Button></div>}
  </form>
  {busy&&<p role="status">{receipt?'Actualisation du dossier…':'Dépôt de l’original et analyse du texte en cours…'}</p>}
  {error&&<p className="document-upload-error" role="alert">{error}</p>}
  {receipt&&<div className="document-upload-receipt" role="status"><p>{receipt.message}</p>{receipt.warnings.length>0&&<ul>{receipt.warnings.map((warning:string,index:number)=><li key={index}>{warning}</li>)}</ul>}<p>Les informations proposées attendent votre validation ; elles ne modifient pas les faits confirmés.</p></div>}
  {receipt?.candidate_count>0&&!busy&&!needsReload&&<Button variant="link" asChild><a href={`#/chantiers/${encodeURIComponent(projectId)}?view=page`} onClick={event=>{event.preventDefault();void preservePanels().then(()=>{location.hash=`#/chantiers/${encodeURIComponent(projectId)}?view=page`;}).catch(cause=>setError(cause instanceof Error?cause.message:'Terminez les opérations en cours avant d’ouvrir la page du dossier.'));}}>Voir les informations à vérifier</a></Button>}
  {needsReload&&!busy&&<Button variant="outline" onClick={()=>void reload()}>Recharger les documents</Button>}
 </div>;
}
