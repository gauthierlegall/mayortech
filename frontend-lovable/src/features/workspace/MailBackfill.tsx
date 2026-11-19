import {useEffect,useRef,useState} from 'react';
import {ArrowRight,History,Pause,Play,RefreshCw,Square} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import './mail-backfill.css';

type Folder={id:string;name:string};
type Account={id:string;revision:number;label:string;mailbox:string;selected_folder_ids:string[];mail_folders:Folder[];status:string};
type Scope={connection_id:string;folder_ids:string[];start:string;end:string;expected_connection_revision:number};
type Preview={connection_id:string;connection_label:string;mailbox:string;start:string;end:string;folders:Folder[];batch_size:number};
type Job=Preview&{id:string;status:string;revision:number;has_more:boolean;can_resume:boolean;created_at:string;current_folder:Folder|null;progress:{scanned:number;imported:number;already_present:number;out_of_range:number;unavailable:number;quarantined:number;batches:number;folders_completed:number;folders_total:number};last_error:{code:string;message:string}|null};
const states:Record<string,string>={ready:'Prêt à reprendre',running:'Lecture en cours',paused:'En pause',completed:'Terminé',cancelled:'Annulé',failed:'Interrompu'};
const labelDate=(date:string)=>new Date(date+'T12:00:00').toLocaleDateString('fr-FR');
const failureMessage=(failure:unknown)=>failure instanceof Error?failure.message:'La reprise ne peut pas continuer. Actualisez son état puis réessayez.';

export function MailBackfill({connection,canManage}:{connection:Account;canManage:boolean}){
 const {api}=useWorkspace();
 const [jobs,setJobs]=useState<Job[]>([]),[folders,setFolders]=useState<string[]>(connection.selected_folder_ids),[start,setStart]=useState(''),[end,setEnd]=useState(''),[preview,setPreview]=useState<Preview|null>(null),[previewScope,setPreviewScope]=useState<Scope|null>(null),[loading,setLoading]=useState(true),[working,setWorking]=useState(''),[running,setRunning]=useState(''),[error,setError]=useState(''),[feedback,setFeedback]=useState('');
 const alive=useRef(true),stop=useRef(true),generation=useRef(0);
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const allowed=connection.mail_folders.filter(folder=>connection.selected_folder_ids.includes(folder.id));
 const connected=['verified','synced'].includes(connection.status);
 function merge(job:Job){if(!alive.current)return;setJobs(previous=>{const old=previous.find(item=>item.id===job.id);if(old&&old.revision>job.revision)return previous;return[...previous.filter(item=>item.id!==job.id),job].sort((a,b)=>b.created_at.localeCompare(a.created_at));});}
 async function reload(){setLoading(true);try{const response=await api.mailBackfills(connection.id);if(alive.current)setJobs(previous=>(response.items||[]).filter((job:Job)=>job.connection_id===connection.id).map((job:Job)=>{const current=previous.find(item=>item.id===job.id);return current&&current.revision>job.revision?current:job;}));}catch(failure){if(alive.current)setError(failureMessage(failure));}finally{if(alive.current)setLoading(false);}}
 useEffect(()=>{alive.current=true;void reload();return()=>{alive.current=false;stop.current=true;generation.current++;};},[api,connection.id]);
 useEffect(()=>{setFolders(previous=>previous.filter(id=>connection.selected_folder_ids.includes(id)));setPreview(null);setPreviewScope(null);},[connection.revision]);
 function changed(){setPreview(null);setPreviewScope(null);setFeedback('');}
 async function act(job:Job,action:'pause'|'resume'|'cancel'){
  // A running batch may have reserved the next revision. Read its latest state
  // before controls, then retry one conflict without ever replaying a batch.
  let latest=await api.mailBackfill(job.id) as Job;
  try{return await api.controlMailBackfill(job.id,action,latest.revision) as Job;}
  catch(failure){if((failure as {status?:number})?.status!==409)throw failure;latest=await api.mailBackfill(job.id) as Job;return await api.controlMailBackfill(job.id,action,latest.revision) as Job;}
 }
 async function process(initial:Job){
  if(running||working)return;const run=++generation.current;stop.current=false;setRunning(initial.id);setError('');setFeedback('');
  let job=initial;
  try{
   job=await api.mailBackfill(job.id) as Job;merge(job);
   if(['paused','failed'].includes(job.status)){job=await act(job,'resume');merge(job);}
   while(alive.current&&!stop.current&&generation.current===run&&['ready','running'].includes(job.status)){
    job=await api.controlMailBackfill(job.id,'run',job.revision) as Job;merge(job);
   }
   if(alive.current&&job.status==='completed')setFeedback('Reprise terminée. Les courriels sont disponibles ; les propositions restent à vérifier.');
  }catch(failure){
   if(alive.current){try{merge(await api.mailBackfill(initial.id) as Job);}catch{/* Preserve the last known progress on a network failure. */}if(!stop.current)setError(failureMessage(failure));}
  }finally{if(alive.current&&generation.current===run)setRunning('');}
 }
 async function control(job:Job,action:'pause'|'cancel'){
  stop.current=true;setWorking(job.id);setError('');
  try{const current=await act(job,action);merge(current);setFeedback(action==='pause'?'Reprise mise en pause. Vous pourrez continuer depuis le dernier lot conservé.':'Reprise annulée. Les courriels déjà importés restent conservés.');}
  catch(failure){setError(failureMessage(failure));try{merge(await api.mailBackfill(job.id) as Job);}catch{/* A refresh remains available. */}}
  finally{if(alive.current)setWorking('');}
 }
 const busy=Boolean(working||running);
 return <section className="mail-backfill" aria-labelledby={`backfill-${connection.id}`}>
  <div className="backfill-heading"><div><h3 id={`backfill-${connection.id}`}><History size={17}/>Reprendre les anciens courriels</h3><p>Choisissez les dossiers et la période à retrouver. Les originaux sont conservés et les messages déjà présents ne sont pas ajoutés une seconde fois.</p></div><Button variant="ghost" size="sm" disabled={Boolean(working)} onClick={()=>void reload()}><RefreshCw size={14}/>Actualiser</Button></div>
  {canManage&&connected&&allowed.length>0&&<form className="backfill-form" onSubmit={async event=>{event.preventDefault();if(busy)return;setWorking('preview');setError('');setFeedback('');const scope={connection_id:connection.id,folder_ids:folders,start,end,expected_connection_revision:connection.revision};try{setPreview(await api.previewMailBackfill(scope) as Preview);setPreviewScope(scope);}catch(failure){setError(failureMessage(failure));}finally{if(alive.current)setWorking('');}}}>
   <div className="backfill-dates"><label>Du<input type="date" required max={end||today} value={start} disabled={busy} onChange={event=>{setStart(event.target.value);changed();}}/></label><label>Au, inclus<input type="date" required min={start||undefined} max={today} value={end} disabled={busy} onChange={event=>{setEnd(event.target.value);changed();}}/></label></div>
   <fieldset disabled={busy}><legend>Dossiers à reprendre</legend>{allowed.map(folder=><label key={folder.id}><input type="checkbox" checked={folders.includes(folder.id)} onChange={()=>{setFolders(previous=>previous.includes(folder.id)?previous.filter(id=>id!==folder.id):[...previous,folder.id]);changed();}}/>{folder.name}</label>)}</fieldset>
   <Button variant="outline" type="submit" disabled={busy||!folders.length}>{working==='preview'?'Préparation…':'Préparer la reprise'}<ArrowRight size={14}/></Button>
  </form>}
  {canManage&&(!connected||!allowed.length)&&<p className="backfill-note">Vérifiez le compte et enregistrez au moins un dossier de messagerie avant de préparer une reprise.</p>}
  {preview&&previewScope&&<div className="backfill-preview"><h4>Vérifier le périmètre</h4><dl><div><dt>Compte</dt><dd>{preview.connection_label} · {preview.mailbox}</dd></div><div><dt>Période</dt><dd>Du {labelDate(preview.start)} au {labelDate(preview.end)} inclus, heure de Paris</dd></div><div><dt>Dossiers</dt><dd>{preview.folders.map(folder=>folder.name).join(', ')}</dd></div></dl><p>Le serveur sera parcouru par petits lots pour retrouver cette période. Le nombre total n’est pas connu à l’avance. Vous pourrez mettre en pause puis reprendre.</p><Button disabled={busy} onClick={async()=>{setWorking('create');setError('');try{const job=await api.createMailBackfill(previewScope) as Job;merge(job);setPreview(null);setPreviewScope(null);setFeedback('Reprise préparée. Lancez la lecture pour parcourir les premiers lots.');}catch(failure){setError(failureMessage(failure));}finally{if(alive.current)setWorking('');}}}>{working==='create'?'Création…':'Créer cette reprise'}</Button></div>}
  {error&&<p role="alert" className="form-error">{error}</p>}{feedback&&<p role="status" className="backfill-feedback">{feedback}</p>}
  {loading&&!jobs.length&&<p role="status">Chargement des reprises…</p>}
  <div className="backfill-jobs">{jobs.map(job=><article key={job.id}><header><div><h4>{labelDate(job.start)} – {labelDate(job.end)}</h4><p>{job.folders.map(folder=>folder.name).join(', ')}</p></div><span className="status-pill">{states[job.status]||job.status}</span></header><dl className="backfill-counts"><div><dt>Éléments parcourus</dt><dd>{job.progress.scanned}</dd></div><div><dt>Courriels importés</dt><dd>{job.progress.imported}</dd></div><div><dt>Déjà présents</dt><dd>{job.progress.already_present}</dd></div><div><dt>Hors période</dt><dd>{job.progress.out_of_range}</dd></div></dl><p className="backfill-note">{job.current_folder?`Dossier en cours : ${job.current_folder.name}. `:''}{job.progress.folders_completed} / {job.progress.folders_total} dossiers parcourus · {job.progress.batches} lots conservés.{job.progress.quarantined>0?` ${job.progress.quarantined} éléments isolés pour contrôle.`:''}{job.progress.unavailable>0?` ${job.progress.unavailable} éléments indisponibles sur le serveur.`:''}</p>{job.last_error&&<p className="form-error" role="alert">{job.last_error.message}</p>}<div className="backfill-actions">{canManage&&!['completed','cancelled'].includes(job.status)&&<><Button size="sm" disabled={busy||!connected||(job.status==='failed'&&!job.can_resume)} onClick={()=>void process(job)}><Play size={14}/>{running===job.id?'Lecture par lots…':['paused','failed'].includes(job.status)?'Reprendre la lecture':'Lancer la lecture'}</Button>{['ready','running'].includes(job.status)&&<Button size="sm" variant="outline" disabled={Boolean(working)||Boolean(running&&running!==job.id)} onClick={()=>void control(job,'pause')}><Pause size={14}/>Mettre en pause</Button>}<Button size="sm" variant="ghost" disabled={Boolean(working)||Boolean(running&&running!==job.id)} onClick={()=>{if(window.confirm('Annuler cette reprise ? Les courriels déjà importés seront conservés.'))void control(job,'cancel');}}><Square size={13}/>Annuler la reprise</Button></>}<Button variant="link" size="sm" asChild><a href="#/mail">Voir les courriels<ArrowRight size={14}/></a></Button><Button variant="link" size="sm" asChild><a href="#/review">Vérifier les propositions<ArrowRight size={14}/></a></Button></div></article>)}</div>
  {jobs.length>0&&<p className="backfill-note">La lecture avance tant que cette page est ouverte. Après fermeture ou interruption, revenez ici pour reprendre ; le dernier lot conservé reste mémorisé. Aucun élément n’est envoyé ni modifié dans la boîte d’origine.</p>}
 </section>;
}
