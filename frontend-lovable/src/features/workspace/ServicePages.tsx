import {useEffect,useState} from 'react';
import {useLocation} from '@tanstack/react-router';
import {Check,ArrowRight} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from './context';
import {Actions} from './Actions';
import {resolveSummaryDestination} from './summary-redirect.mjs';
import {workspaceIdentity} from './workspace-scope.mjs';
const list=(value:any)=>Array.isArray(value)?value:value?.items||[];
const valueText=(value:any)=>typeof value==='string'?value:JSON.stringify(value);
const fieldLabel=(field:string)=>field.startsWith('action.')?'Action proposée':({progress:'Avancement',delivery_date:'Livraison',budget_raw:'Budget',contractor:'Entreprise',deadline:'Échéance'} as Record<string,string>)[field]||'Information à confirmer';

export function AllActions(){return <Actions/>;}

export function ReviewPage(){const {api,refresh}=useWorkspace();const [reviews,setReviews]=useState<any[]>([]),[selected,setSelected]=useState<any>(null),[error,setError]=useState(''),[source,setSource]=useState<any>(null),[decision,setDecision]=useState(''),[busy,setBusy]=useState(false);const location=useLocation();
 const load=async()=>{const items=list(await api.reviews());const projectId=new URLSearchParams(window.location.hash.split('?')[1]||'').get('project');const filtered=items.filter((item:any)=>!projectId||item.project_id===projectId);setReviews(filtered);const wanted=location.pathname.split('/')[2];setSelected(filtered.find((item:any)=>item.id===wanted)||filtered[0]||null);};
 useEffect(()=>{void load().catch(error=>setError(error.message));},[location.href]);
 async function decide(kind:string,reason='',corrected?:string){if(!selected)return;setBusy(true);setError('');try{const project=await api.project(selected.project_id);await api.decide(selected.id,{decision:kind,expected_revision:project.revision,...(reason?{reason}:{}),...(corrected?{corrected_value:corrected}:{})});setDecision('');await refresh();await load();}catch(error){setError(error instanceof Error?error.message:'La décision n’a pas pu être enregistrée.');}finally{setBusy(false);}}
 return <main className="content"><div className="page-heading"><div><h1>À vérifier</h1><p>Relisez la source avant de confirmer ce qui change dans le dossier.</p></div></div>{error&&<p className="form-error" role="alert">{error}</p>}{!selected?<div className="empty"><Check/><h2>Aucune proposition sélectionnée</h2><p>Consultez un chantier pour relire ses sources.</p></div>:<div className="review-columns"><nav className="review-proposals" aria-label="Propositions">{reviews.map(item=><button key={item.id} className={item.id===selected.id?'selected':''} onClick={()=>setSelected(item)}><strong>{fieldLabel(item.field)}</strong><small>{item.project_name}</small></button>)}</nav><section className="proposal"><div className="proposal-label">À VÉRIFIER <span>{selected.project_name}</span></div><h2>{fieldLabel(selected.field)}</h2>{selected.previous_values?.length>0&&<div className="previous-facts"><h3>Information précédente</h3>{selected.previous_values.map((previous:any)=><p key={previous.id}>{valueText(previous.value)}</p>)}</div>}<p className="proposed-value">{valueText(selected.value)}</p><blockquote>{selected.evidence?.[0]?.quote||'Ouvrez la source pour consulter le message.'}</blockquote><Button variant="link" className="source-link" onClick={async()=>setSource(await api.source(selected.source_id))}>Ouvrir le message source<ArrowRight/></Button><div className="proposal-actions"><Button disabled={busy} onClick={()=>selected.conflict_with?.length?setDecision('replace'):void decide('accept')}><Check/>{selected.conflict_with?.length?'Remplacer la valeur précédente':'Confirmer'}</Button><Button variant="outline" disabled={busy} onClick={()=>setDecision('correct')}>Corriger</Button><Button variant="ghost" disabled={busy} onClick={()=>setDecision('reject')}>Écarter</Button></div></section></div>}
 <Dialog open={Boolean(decision)} onOpenChange={open=>{if(!open)setDecision('');}}><DialogContent><DialogTitle>{decision==='correct'?'Corriger la proposition':decision==='replace'?'Confirmer le remplacement':'Écarter la proposition'}</DialogTitle><DialogDescription>Le motif reste associé à votre décision et à la source.</DialogDescription><form className="form-stack" onSubmit={event=>{event.preventDefault();const data=new FormData(event.currentTarget);void decide(decision==='correct'?'accept':decision,String(data.get('reason')),decision==='correct'?String(data.get('corrected')):undefined);}}>{decision==='correct'&&<label>Valeur retenue<textarea name="corrected" required defaultValue={valueText(selected?.value)}/></label>}<label>Motif<textarea name="reason" required maxLength={2000}/></label><Button type="submit" disabled={busy}>Enregistrer la décision</Button></form></DialogContent></Dialog>
 <Dialog open={Boolean(source)} onOpenChange={open=>{if(!open)setSource(null);}}><DialogContent><DialogTitle>{(source?.source||source)?.subject||'Document source'}</DialogTitle><DialogDescription>{(source?.source||source)?.sender||'Source du dossier'}</DialogDescription><pre className="source-text">{(source?.source||source)?.body}</pre></DialogContent></Dialog></main>;
}

/** Compatibility only: summaries are opened from their owning project. */
export function LegacySummaryRedirect({id}:{id?:string}){
 const {api,state,session}=useWorkspace();
 const identity=workspaceIdentity(session),projectScope=JSON.stringify(state.projects.map(project=>project.id).sort());
 useEffect(()=>{let active=true;void resolveSummaryDestination(api,id,JSON.parse(projectScope)).then(destination=>{if(active)window.location.replace(destination);});return()=>{active=false;};},[api,id,identity,projectScope]);
 return <main className="content"><p role="status">Ouverture du chantier…</p><a href="#/">Tous les chantiers</a></main>;
}
