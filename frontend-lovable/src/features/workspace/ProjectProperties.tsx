import {useCallback,useEffect,useRef,useState} from 'react';
import {Download,FileText,Paperclip,RefreshCw,Save} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {registerPreserver} from './panel-lifecycle';
import {documentOf,objectOf,textOf,type DocumentRecord} from './ProjectPanels.types';
import {orderPropertyFields,presentationForCommission} from './commission-presentation.mjs';
import './project-properties.css';

type Key='name'|'category'|'estimated_cost'|'actual_cost'|'request_date'|'requester'|'contractor'|'location'|'notes'|'observation'|'priority'|'service_owner'|'status'|'deadline';
type Values=Record<Key,string>;
type Origin={kind:string;source_id:string;actor_id:string};
type Profile={project_id:string;revision:number;project_revision:number;values:Values;origins:Record<Key,Origin>;documents:DocumentRecord[];can_edit:boolean};
type Field={key:Key;label:string;type?:'date'|'money'|'long'|'priority'|'status';wide?:boolean};
const fields:Field[]=[
 {key:'name',label:'Dossier',wide:true},{key:'category',label:'Catégorie'},
 {key:'status',label:'Statut',type:'status'},{key:'priority',label:'Priorité',type:'priority'},
 {key:'request_date',label:'Date demande',type:'date'},{key:'deadline',label:'Échéance',type:'date'},
 {key:'requester',label:'Demandeur'},{key:'service_owner',label:'Service / Responsable'},
 {key:'contractor',label:'Entreprise'},{key:'location',label:'Lieu'},
 {key:'estimated_cost',label:'Coût estimé',type:'money'},{key:'actual_cost',label:'Coût réel',type:'money'},
 {key:'notes',label:'Notes',type:'long',wide:true},{key:'observation',label:'Observation',type:'long',wide:true},
];
const keys=fields.map(field=>field.key);
const priorityChoices=['','Urgente','Haute','Normale','Basse'];
const statusChoices=['À traiter','En cours','En attente','Terminé','Bloqué','Annulé'];
const message=(failure:unknown)=>failure instanceof Error?failure.message:'Les propriétés ne peuvent pas être enregistrées. Réessayez.';
const diff=(values:Values,baseline:Values)=>Object.fromEntries(keys.filter(key=>values[key]!==baseline[key]).map(key=>[key,values[key]])) as Partial<Values>;
function profileOf(raw:unknown,projectId:string):Profile{
 const row=objectOf(raw),values=objectOf(row['values']),origins=objectOf(row['origins']);
 if(row['project_id']!==projectId||!Number.isSafeInteger(row['revision'])||!Number.isSafeInteger(row['project_revision'])||keys.some(key=>typeof values[key]!=='string'))throw Error('Les propriétés reçues ne correspondent pas à ce dossier. Rechargez-les.');
 return {project_id:projectId,revision:row['revision'] as number,project_revision:row['project_revision'] as number,values:values as Values,origins:Object.fromEntries(keys.map(key=>{const origin=objectOf(origins[key]);return[key,{kind:textOf(origin['kind']),source_id:textOf(origin['source_id']),actor_id:textOf(origin['actor_id'])}];})) as Record<Key,Origin>,documents:Array.isArray(row['documents'])?row['documents'].map(documentOf):[],can_edit:row['can_edit']===true};
}

/** Human properties use their own revision, with the project revision as a second guard. */
export function ProjectProperties({projectId,onChanged,onSource,onDocuments}:{projectId:string;onChanged?:()=>Promise<void>|void;onSource?:(sourceId:string)=>void;onDocuments?:()=>void}){
 const {api,bootstrap,activeCommissionId}=useWorkspace();
 const [profile,setProfile]=useState<Profile|null>(null),[values,setValues]=useState<Values|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(''),[feedback,setFeedback]=useState(''),[conflicts,setConflicts]=useState<{label:string;value:string}[]>([]),[needsReview,setNeedsReview]=useState(false);
 const reviewRef=useRef(needsReview);reviewRef.current=needsReview;
 const alive=useRef(true),epoch=useRef(0),baseRef=useRef(profile),valuesRef=useRef(values),saving=useRef<Promise<void>|null>(null),saveRef=useRef<()=>Promise<void>>(async()=>{}),changedRef=useRef(onChanged);
 baseRef.current=profile;valuesRef.current=values;changedRef.current=onChanged;
 const dirty=Boolean(profile&&values&&Object.keys(diff(values,profile.values)).length);
 const canReadSource=bootstrap?.permissions?.mail?.read===true;
 const load=useCallback(async(keepDraft=false)=>{
  if(saving.current)return;
  const token=++epoch.current;setLoading(true);setError('');setFeedback('');
  const previous=baseRef.current,draft=valuesRef.current,pending=keepDraft&&previous&&draft?diff(draft,previous.values):{};
  try{
   const next=profileOf(await api.projectProperties(projectId),projectId);
   if(!alive.current||epoch.current!==token)return;
   const changed=previous?keys.filter(key=>key in pending&&next.values[key]!==previous.values[key]&&next.values[key]!==pending[key]).map(key=>({label:fields.find(field=>field.key===key)!.label,value:next.values[key]})):[];
   const merged={...next.values,...pending};setProfile(next);setValues(merged);setConflicts(changed);const review=keepDraft&&Object.keys(diff(merged,next.values)).length>0;setNeedsReview(review);reviewRef.current=review;
   if(keepDraft&&Object.keys(pending).length)setFeedback('Le dossier a été actualisé. Votre saisie est conservée : relisez-la avant de l’enregistrer.');
  }catch(failure){if(alive.current&&epoch.current===token)setError(message(failure));}
  finally{if(alive.current&&epoch.current===token)setLoading(false);}
 },[api,projectId]);
 const save=useCallback((explicit=false)=>{
  if(saving.current)return saving.current;
  const baseline=baseRef.current,draft=valuesRef.current;
  if(!baseline||!draft||!baseline.can_edit)return Promise.resolve();
  const changes=diff(draft,baseline.values);
  if(!Object.keys(changes).length)return Promise.resolve();
  if(reviewRef.current&&!explicit){const failure=Error('Relisez les propriétés actualisées puis cliquez sur Enregistrer les propriétés avant de quitter cette vue.');return Promise.reject(failure);}
  const token=epoch.current,notify=changedRef.current;
  setBusy(true);setError('');setFeedback('');
  const task=(async()=>{
   const next=profileOf(await api.saveProjectProperties(projectId,{expected_revision:baseline.revision,expected_project_revision:baseline.project_revision,changes}),projectId);
   if(alive.current&&epoch.current===token){setProfile(next);setValues(next.values);setConflicts([]);setNeedsReview(false);reviewRef.current=false;setFeedback('');baseRef.current=next;valuesRef.current=next.values;}
   try{await notify?.();}catch{if(alive.current&&epoch.current===token)setFeedback('Propriétés enregistrées. Le reste du dossier doit être actualisé.');}
  })().catch(failure=>{if(alive.current&&epoch.current===token)setError(message(failure)+' Votre saisie reste disponible.');throw failure;}).finally(()=>{saving.current=null;if(alive.current&&epoch.current===token)setBusy(false);});
  saving.current=task;return task;
 },[api,projectId]);
 saveRef.current=save;
 useEffect(()=>{alive.current=true;setProfile(null);setValues(null);void load();const unregister=registerPreserver(()=>saveRef.current(),()=>Boolean(saving.current||(baseRef.current&&valuesRef.current&&Object.keys(diff(valuesRef.current,baseRef.current.values)).length)));return()=>{alive.current=false;epoch.current++;unregister();};},[projectId,load]);
 if(!profile||!values)return <section className="project-properties" aria-busy={loading}><h2>Propriétés du dossier</h2>{error?<><p role="alert">{error}</p><Button variant="outline" onClick={()=>void load()}>Réessayer</Button></>:<p role="status">Chargement des propriétés…</p>}</section>;
 const change=(key:Key,value:string)=>{setValues(previous=>previous?{...previous,[key]:value}:previous);setFeedback('');};
 const source=(key:Key)=>{const origin=profile.origins[key];return origin?.source_id&&canReadSource&&onSource?<Button type="button" variant="link" size="sm" className="property-provenance" onClick={()=>onSource(origin.source_id)}><FileText size={12}/>{origin.kind==='confirmed_fact'?'Fait confirmé · voir la source':'Saisie humaine · voir la source'}</Button>:origin?.kind==='confirmed_fact'?<small>Valeur issue d’un fait confirmé</small>:origin?.kind==='human_property'?<small>Saisie humaine conservée</small>:null;};
 return <section className="project-properties" aria-busy={busy||loading}>
  <header className="properties-heading"><div><h2>Propriétés du dossier</h2><p>{presentationForCommission(activeCommissionId).properties}</p></div><Button type="button" variant="outline" disabled={busy||loading} onClick={()=>void load(dirty)}><RefreshCw size={15}/>{dirty?'Actualiser en gardant ma saisie':'Actualiser'}</Button></header>
  <p className="properties-policy">Ces saisies sont conservées avec leur source. Les annonces reçues par mail restent à vérifier séparément.</p>
  {error&&<div className="properties-message error" role="alert"><p>{error}</p><p>Si le dossier a changé, actualisez-le en gardant votre saisie, puis vérifiez les valeurs avant d’enregistrer.</p></div>}
  {feedback&&!needsReview&&<p className="properties-message" role="status">{feedback}</p>}
  {needsReview&&<p className="properties-message" role="status">Votre saisie doit être relue après actualisation. Cliquez sur Enregistrer les propriétés pour la confirmer ; la navigation attend cette confirmation.</p>}
  {conflicts.length>0&&<div className="properties-message" role="alert"><strong>Des valeurs ont aussi changé dans le dossier :</strong><ul>{conflicts.map(item=><li key={item.label}>{item.label} : {item.value||'Non renseigné'}</li>)}</ul></div>}
  <form onSubmit={event=>{event.preventDefault();void save(true).catch(()=>{});}}>
   <div className="properties-grid">{orderPropertyFields(fields,activeCommissionId).map(field=>{
    const id=`property-${projectId}-${field.key}`,disabled=!profile.can_edit||busy||loading;
    let input;
    if(field.type==='long')input=<textarea id={id} value={values[field.key]} rows={5} maxLength={40000} disabled={disabled} onChange={event=>change(field.key,event.target.value)}/>;
    else if(field.type==='priority'||field.type==='status'){
     const choices=field.type==='priority'?priorityChoices:statusChoices;const custom=values[field.key]&&!choices.includes(values[field.key])?values[field.key]:null;
     input=<select id={id} value={values[field.key]} disabled={disabled} onChange={event=>change(field.key,event.target.value)}>{custom&&<option value={custom}>{custom}</option>}{choices.map(choice=><option key={choice} value={choice}>{choice||'Non renseignée'}</option>)}</select>;
    }else input=<div className={field.type==='money'?'property-money':''}><input id={id} type={field.type==='date'?'date':'text'} inputMode={field.type==='money'?'decimal':undefined} value={values[field.key]} maxLength={field.type==='money'?20:field.key==='name'?300:500} required={field.key==='name'} disabled={disabled} onChange={event=>change(field.key,event.target.value)}/>{field.type==='money'&&<span aria-hidden="true">€</span>}</div>;
    return <div key={field.key} className={`property-field${field.wide?' wide':''}`}><label htmlFor={id}>{field.label}{field.type==='money'&&<span className="sr-only"> en euros</span>}</label>{input}{source(field.key)}{field.type==='long'&&<small>{values[field.key].length.toLocaleString('fr-FR')} / 40 000 caractères</small>}</div>;
   })}</div>
   <div className="properties-save">{(!profile.can_edit||dirty)&&<p>{!profile.can_edit?'Vous disposez d’un accès en lecture seule.':'Modifications à enregistrer.'}</p>}{profile.can_edit&&<Button type="submit" disabled={busy||loading||!dirty}><Save size={15}/>{busy?'Enregistrement…':'Enregistrer les propriétés'}</Button>}</div>
  </form>
  <section className="property-attachments" aria-labelledby={`attachments-${projectId}`}><div className="section-heading"><h3 id={`attachments-${projectId}`}><Paperclip size={17}/>Pièces jointes</h3>{onDocuments&&<Button type="button" variant="outline" size="sm" disabled={busy} onClick={()=>onDocuments()}>Ouvrir les documents</Button>}</div>
   {profile.documents.length?<ul>{profile.documents.map((document,index)=><li key={document.id||`${document.source_id}-${index}`}><FileText size={17}/><div><strong>{document.filename}</strong><small>{document.available?'Original conservé':'Original indisponible pour cet ancien import'}</small></div>{document.available&&document.id&&canReadSource&&<Button variant="ghost" size="icon" title={`Télécharger ${document.filename}`} asChild><a href={`/api/v1/documents/${encodeURIComponent(document.id)}/download`} download><Download size={16}/></a></Button>}</li>)}</ul>:<p>Aucune pièce jointe rattachée à ce dossier.</p>}
   <p className="properties-attachment-help">Les pièces jointes proviennent des courriels importés et rattachés au dossier. Leur original et leur message source sont accessibles dans Documents. Les imports de comptes réels nécessitent un espace protégé.</p>
  </section>
 </section>;
}
