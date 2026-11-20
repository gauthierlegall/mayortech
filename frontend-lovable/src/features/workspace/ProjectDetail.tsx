import {lazy,Suspense,useCallback,useEffect,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,CalendarDays,ChartGantt,ChevronRight,FileText,HardHat,History,Landmark,MapPin,MessagesSquare,ListChecks,SlidersHorizontal,Star,HeartHandshake} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {formatDate} from './model';
import {Mail} from './Mail';
import {SourcePreview} from './SourcePreview';
import {Actions} from './Actions';
import {Planning} from './Planning';
import {openAssistant} from './AssistantWidget';
import illustration from '@/assets/ecole-portail.jpg';
import {HistoryPanel,ProposalPanel,SummaryDialog} from './ProjectPanels';
import {DocumentsPanel} from './DocumentsPanel';
import {candidateOf,documentOf,objectOf,projectOf,resultItems,textOf,type CandidateRecord,type DocumentRecord,type NativeMetadata,type ProjectApi,type ProjectRecord} from './ProjectPanels.types';
import {dateLabel,displayValue,statusLabel} from '../../../../web/model.js';
import {preservePanels} from './panel-lifecycle';
import {cachedNativeActions,cachedNativeNotes,loadNativeActions,flushNativeActions,type NativeAction,type NativeNotesProjection} from './native-actions';
import {projectNotesPreview} from './project-notes-preview.mjs';
import {importedWorkbook} from './project-import-model.mjs';
import {WorkbookProjectContext} from './WorkbookProjectContext';
import {resolveDocumentCatalog,formatCatalogAmount,verifiedDocumentReview} from './document-catalog';
const BlockEditor=lazy(()=>import('./BlockEditor'));

const ProjectProperties=lazy(()=>import('./ProjectProperties').then(module=>({default:module.ProjectProperties})));
const Terrain=lazy(()=>import('./Terrain').then(module=>({default:module.Terrain})));
const CulturePanel=lazy(()=>import('../culture/CulturePanel').then(module=>({default:module.CulturePanel})));
const UrbanismePortsPanel=lazy(()=>import('../urbanisme/UrbanismePortsPanel').then(module=>({default:module.UrbanismePortsPanel})));
const SocialAidPanel=lazy(()=>import('../enfance/SocialAidPanel').then(module=>({default:module.SocialAidPanel})));
const readProperties=()=>new URLSearchParams(location.hash.split('?')[1]||'').get('view')==='properties';
type Tab='planning'|'notes'|'actions'|'terrain'|'documents'|'mail'|'culture'|'urbanisme'|'social';
function readView(){const params=new URLSearchParams(typeof location==='undefined'?'':location.hash.split('?')[1]||'');const view=params.get('view');return {tab:(view==='properties'?'notes':view==='culture'?'culture':view==='urbanisme'?'urbanisme':view==='social'?'social':view==='terrain'?'terrain':view==='table'||view==='kanban'?'actions':view==='documents'?'documents':view==='exchanges'||view==='mail'?'mail':view==='page'?'notes':'planning') as Tab,actionView:(view==='kanban'?'kanban':'table') as 'table'|'kanban',mail:params.get('mail')};}

export function ProjectDetail({id}:{id:string}){
  const {state,api,refresh,session,bootstrap,toggleFavorite}=useWorkspace();
  const backend=api as ProjectApi;
  const refreshRef=useRef(refresh);refreshRef.current=refresh;
  const [project,setProject]=useState<ProjectRecord|null>(null),[documents,setDocuments]=useState<DocumentRecord[]>([]),[reviews,setReviews]=useState<CandidateRecord[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[partialError,setPartialError]=useState('');
  const [propertiesOpen,setPropertiesOpen]=useState(readProperties);
  const [view,setView]=useState(readView),[source,setSource]=useState<{id:string;focus:HTMLElement|null}|null>(null),[summariesOpen,setSummariesOpen]=useState(false),[summaryId,setSummaryId]=useState<string|null>(null),[metadata,setMetadata]=useState<NativeMetadata|null>(null),[navigationError,setNavigationError]=useState(''),[editing,setEditing]=useState(false);
  const epoch=useRef(0),mounted=useRef(true);
  const [nativeRows,setNativeRows]=useState<NativeAction[]>(()=>cachedNativeActions([id])),[nativeReady,setNativeReady]=useState(false);
  const [notesProjection,setNotesProjection]=useState<NativeNotesProjection>(()=>cachedNativeNotes(id));
  const [documentReviewRows,setDocumentReviewRows]=useState<unknown[]>([]);
  const canWrite=objectOf(objectOf(bootstrap?.permissions)['workspace'])['write']===true;
  useEffect(()=>{let active=true;const cached=cachedNativeActions([id]);setNativeReady(cached.length>0);setNativeRows(cached);setNotesProjection(cachedNativeNotes(id));const changed=()=>{if(active){setNativeRows(cachedNativeActions([id]));setNotesProjection(cachedNativeNotes(id));setNativeReady(true);}};window.addEventListener('travaux:native-actions',changed);if(view.tab==='notes')void loadNativeActions(api,[id],canWrite).then(changed).catch(()=>{if(active){setNativeReady(true);setNotesProjection({status:'unavailable'});}});return()=>{active=false;window.removeEventListener('travaux:native-actions',changed);};},[api,id,canWrite,view.tab]);
  const overview=state.projects.find(item=>item.id===id);
  const accessKey=state.projects.map(item=>item.id).sort().join('|');
  const favorite=overview?.favorite===true;
  const reload=useCallback(async(global=false)=>{
    const token=++epoch.current;
    const [detail,files,pending,decisions]=await Promise.allSettled([backend.project(id),backend.documents(id),backend.reviews(id),typeof api.documentReviews==='function'?api.documentReviews(id):Promise.resolve(null)]);
    if(!mounted.current||token!==epoch.current)return;
    if(detail.status==='rejected'){setError(detail.reason instanceof Error?detail.reason.message:'Le dossier ne peut pas être chargé. Réessayez.');setLoading(false);return;}
    try{
      const loaded=projectOf(detail.value);if(loaded.id!==id)throw new Error('Le dossier reçu ne correspond pas au chantier demandé.');
      setProject(loaded);setError('');
      setDocuments(files.status==='fulfilled'?resultItems(files.value).map(documentOf).filter(file=>file.kind!=='email'&&file.kind!=='eml'):[]);
      setReviews(pending.status==='fulfilled'?resultItems(pending.value).map(candidateOf):loaded.pending);
      setDocumentReviewRows(decisions.status==='fulfilled'&&objectOf(decisions.value)['project_id']===id?resultItems(decisions.value):[]);
      setPartialError(files.status==='rejected'||pending.status==='rejected'?'Certaines pièces ou propositions n’ont pas pu être chargées. Réessayez pour disposer du dossier complet.':'');
      if(global)await refreshRef.current();
    }catch(failure){setError(failure instanceof Error?failure.message:'Le dossier reçu est incomplet.');}
    finally{if(mounted.current&&token===epoch.current)setLoading(false);}
  },[backend,id]);
  useEffect(()=>{const changed=(event:Event)=>{if(event instanceof CustomEvent&&objectOf(event.detail)['projectId']===id)void reload(true);};window.addEventListener('travaux:document-decision',changed);return()=>window.removeEventListener('travaux:document-decision',changed);},[id,reload]);
  useEffect(()=>{
    const changed=async(event:Event)=>{
      if(!(event instanceof CustomEvent)||objectOf(event.detail)['projectId']!==id)return;
      try{await preservePanels();await reload(false);if(event.type==='travaux:assistant-change'&&objectOf(event.detail)['operation']==='action')await loadNativeActions(api,[id],canWrite);}
      catch(failure){if(mounted.current)setNavigationError(failure instanceof Error?failure.message:'Le dossier a changé. Enregistrez vos saisies puis rechargez-le.');}
    };
    window.addEventListener('travaux:assistant-change',changed);window.addEventListener('travaux:documents-changed',changed);
    return()=>{window.removeEventListener('travaux:assistant-change',changed);window.removeEventListener('travaux:documents-changed',changed);};
  },[id,reload,api,canWrite]);
  useEffect(()=>{mounted.current=true;setProject(null);setLoading(true);setView(readView());setPropertiesOpen(readProperties());setMetadata(null);setEditing(false);void reload();return()=>{mounted.current=false;epoch.current++;};},[id,reload]);
  useEffect(()=>{void reload();},[accessKey,reload]);
  useEffect(()=>{const changed=()=>{setView(readView());if(readProperties())setPropertiesOpen(true);};window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed);},[]);
  async function changeTab(tab:Tab,actionView=view.actionView,mail:string|null=null){
    setNavigationError('');
    try{await preservePanels();setView({tab,actionView,mail});const query=new URLSearchParams({view:tab==='social'?'social':tab==='culture'?'culture':tab==='urbanisme'?'urbanisme':tab==='planning'?'planning':tab==='terrain'?'terrain':tab==='notes'?'page':tab==='actions'?actionView:tab==='mail'?'exchanges':'documents'});if(mail)query.set('mail',mail);history.replaceState(null,'',`#/chantiers/${encodeURIComponent(id)}?${query}`);return true;}catch(failure){setNavigationError(failure instanceof Error?failure.message:'Les dernières modifications doivent être enregistrées avant de changer de vue.');return false;}
  }
  async function openProperties(){if(await changeTab('notes')){setPropertiesOpen(true);history.replaceState(null,'',`#/chantiers/${encodeURIComponent(id)}?view=properties`);requestAnimationFrame(()=>document.getElementById('project-properties-section')?.scrollIntoView({block:'start'}));}}
  async function toggleProperties(){try{await preservePanels();setPropertiesOpen(value=>!value);setNavigationError('');}catch(failure){setNavigationError(failure instanceof Error?failure.message:'Enregistrez les propriétés avant de fermer ce panneau.');}}
  const openSource=(sourceId:string)=>setSource({id:sourceId,focus:document.activeElement instanceof HTMLElement?document.activeElement:null});
  const openMail=(mailId:string)=>{void changeTab('mail',view.actionView,mailId);};
  const onChanged=useCallback(()=>{setNavigationError('');return reload(true);},[reload]);
  const onNativeSaved=useCallback(()=>{void reload(false);void loadNativeActions(api,[id],false).catch(()=>setNotesProjection({status:'unavailable'}));},[reload,api,id]);
  if(!state.projects.some(item=>item.id===id)||project?.sources.some(source=>source.project_ids.some(link=>!state.projects.some(item=>item.id===link))))return <main className="content detail-page"><h1>Ce dossier n’est plus accessible</h1><p>Votre accès a changé. Revenez aux chantiers autorisés.</p><a href="#/">Tous les chantiers</a></main>;
  if(loading&&!project)return <main className="content detail-page"><p role="status">Ouverture du dossier…</p></main>;
  if(!project)return <main className="content detail-page"><a href="#/" className="back-link"><ArrowLeft size={15}/>Tous les chantiers</a><h1>Le dossier ne peut pas être ouvert</h1><p role="alert">{error||'Ce chantier est introuvable dans votre espace.'}</p><Button onClick={()=>void reload()}>Réessayer</Button></main>;
  const fact=(field:string)=>project.facts.find(item=>item.field===field);
  const delivery=fact('delivery_date'),company=fact('contractor'),locationFact=fact('location'),owner=fact('owner');
  const confirmed=project.facts.filter(item=>!item.field.startsWith('action.'));
  const workbookSource=importedWorkbook(project.notes);
  const database=metadata?.databases.find(item=>item.id===metadata.managedActionDatabaseId)||metadata?.databases.find(item=>item.id===metadata.activeDatabaseId);
  const rows=database?.rows||[];
  const rowsWithStatus=rows.map(row=>{const read=(names:string[])=>row.fields.find(field=>names.includes(field.name.toLocaleLowerCase('fr')))?.text||'';return {id:row.id,title:read(['intitulé','action','titre','nom'])||row.fields[0]?.text||'',status:read(['statut']),due:read(['échéance']),owner:read(['responsable']),sourceUrl:row.sourceUrl||''};});
  const next=[...nativeRows].filter(row=>row.title&&row.status!=='Terminé').sort((a,b)=>(a.due||'9999').localeCompare(b.due||'9999')||Number(b.priority==='Haute')-Number(a.priority==='Haute')||a.title.localeCompare(b.title,'fr'))[0];
  const summaries=[...project.summaries].sort((a,b)=>b.version-a.version);
  const latest=summaries[0];
  const situation=latest?.content||(confirmed.length?confirmed.slice(0,4).map(item=>`${item.label} : ${displayValue(item.value)}`).join(' · '):project.description);
  const catalogue=resolveDocumentCatalog(project,documents).items;
  const sourceChips=[project.facts.find(item=>item.field==='budget_raw'),reviews.find(item=>item.field==='delivery_date')].filter((item):item is CandidateRecord=>Boolean(item));
  const currentSummary=latest&&!latest.stale&&!latest.coverage_stale?latest:null;
  const property=(key:string,fallback:string)=>typeof project.properties?.values[key]==='string'?project.properties.values[key] as string:fallback;
  const deadlineText=formatDate(property('deadline',overview?.deadline||''),'');
  const category=fact('category'),categoryText=property('category',category?displayValue(category.value):overview?.category||''),locationText=property('location',locationFact?displayValue(locationFact.value):''),companyText=property('contractor',company?displayValue(company.value):'');const ownerText=property('service_owner',owner?displayValue(owner.value):overview?.owner||'');const initials=ownerText.trim().split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join('').toLocaleUpperCase('fr');
  const notesPreview=projectNotesPreview(project.notes,project.sources,notesProjection),previewNotes=notesPreview.notes.slice(-3);
  async function toggleNotes(){try{await preservePanels();await flushNativeActions();setEditing(value=>!value);setNavigationError('');}catch(failure){setNavigationError(failure instanceof Error?failure.message:'Enregistrez les notes avant de fermer l’éditeur.');}}
  return <main className="content detail-page">
    <a href="#/" className="back-link"><ArrowLeft size={15}/>Tous les chantiers</a>
    <div className="detail-heading"><div className="project-symbol"><HardHat/></div><div><span className="eyebrow">{project.reference}{categoryText?` · ${categoryText}`:''}</span><h1>{project.name||'Chantier sans nom'}</h1>{locationText&&<p><MapPin size={14}/>{locationText}</p>}</div><Button variant="ghost" size="icon" title={favorite?'Retirer des favoris':'Ajouter aux favoris'} aria-pressed={favorite} onClick={()=>toggleFavorite(id)}><Star className={favorite?'favorite-star':''}/></Button></div>
    <div className="detail-meta"><span className={`status-pill ${['completed','closed'].includes(project.status)?'done':'progress'}`}><span/>{statusLabel(project.status)}</span>{ownerText&&<span><span className="avatar small">{initials}</span>{ownerText}</span>}{deadlineText&&<span><CalendarDays size={16}/>Échéance : <strong>{deadlineText}</strong></span>}{(delivery||!deadlineText)&&<span><CalendarDays size={16}/>Livraison : <strong>{delivery?formatDate(typeof delivery.value==='string'?delivery.value:''):'Non renseignée'}</strong></span>}{companyText&&<span>{companyText}</span>}<a href="#/parametres?section=modules" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stone-200 bg-white hover:bg-stone-50 text-xs font-semibold text-[#102A4C] transition-colors shadow-3xs cursor-pointer" title="Demander un engagement financier M57 ou lancer un marché public"><Landmark size={14} className="text-[#102A4C]"/><span>Demander un engagement M57 / Marché</span></a><Button variant="outline" size="sm" className="project-properties-trigger" onClick={()=>void openProperties()}><SlidersHorizontal size={14}/>Propriétés</Button></div>
    <div className="detail-tabs" role="tablist" aria-label="Contenu du chantier">{[{name:'Page',id:'notes',icon:FileText},{name:'Actions',id:'actions',icon:ListChecks},{name:'Planning',id:'planning',icon:ChartGantt},{name:'Terrain',id:'terrain',icon:HardHat},{name:'Urbanisme & Ports',id:'urbanisme',icon:MapPin},{name:'Enfance & Social',id:'social',icon:HeartHandshake},{name:'Culture & Finances',id:'culture',icon:Landmark},{name:'Documents',id:'documents',icon:FileText},{name:'Échanges',id:'mail',icon:MessagesSquare}].map(tab=><Button key={tab.id} role="tab" id={`project-tab-${tab.id}`} aria-controls="project-tab-content" aria-selected={view.tab===tab.id} variant="ghost" className={view.tab===tab.id?'active':''} onClick={()=>void changeTab(tab.id as Tab)}><tab.icon/>{tab.name}{tab.id==='actions'&&nativeReady&&<span>{nativeRows.length}</span>}{tab.id==='documents'&&<span>{documents.length}</span>}</Button>)}<Button variant="outline" size="sm" className="assistant-button" onClick={()=>openAssistant(id)}><MessagesSquare size={15}/>Assistant</Button></div>
    {(error||partialError||navigationError)&&<div className="source-callout" role="alert"><p>{navigationError||error||partialError}</p>{!navigationError&&<Button variant="link" size="sm" onClick={()=>void reload()}>Recharger le dossier</Button>}</div>}
    <div id="project-tab-content" role="tabpanel" aria-labelledby={`project-tab-${view.tab}`}>
      {view.tab==='social'&&<Suspense fallback={<p role="status">Chargement du module Enfance & Social…</p>}><SocialAidPanel projectId={id}/></Suspense>}
      {view.tab==='urbanisme'&&<Suspense fallback={<p role="status">Chargement du module Urbanisme & Ports…</p>}><UrbanismePortsPanel projectId={id}/></Suspense>}
      {view.tab==='culture'&&<Suspense fallback={<p role="status">Chargement du module Culture & Finances…</p>}><CulturePanel projectId={id}/></Suspense>}
      {view.tab==='planning'&&<Planning project={project} onSource={openSource} onChanged={onChanged}/>}
      {view.tab==='terrain'&&<Suspense fallback={<p role="status">Chargement du suivi terrain…</p>}><Terrain projectId={id}/></Suspense>}
      {view.tab==='documents'&&<DocumentsPanel project={project} documents={documents} onSource={openSource} onMail={openMail}/>}
      {view.tab==='mail'&&<Mail key={`${id}:${view.mail||''}`} projectId={id} {...(view.mail?{initialId:view.mail}:{})}/>}
      {view.tab==='actions'&&<Actions projectId={id}/>}
      {view.tab==='notes'&&<div className="detail-columns"><div className="detail-body">
        <ProposalPanel project={project} reviews={reviews} api={backend} canWrite={canWrite} onChanged={onChanged} onSource={openSource}/>
        <section className="summary-section"><div className="section-heading"><h2>Situation actuelle</h2><Button variant="ghost" size="sm" onClick={()=>{setSummaryId(latest?.id||null);setSummariesOpen(true);}}><FileText size={15}/>Préparer un récapitulatif</Button></div>{(situation||!workbookSource)&&<p className="summary-text">{situation||'Aucun fait confirmé pour ce chantier. Les annonces reçues restent à vérifier.'}</p>}{workbookSource&&<WorkbookProjectContext project={project} source={workbookSource}/>} {latest&&!currentSummary&&<p className="muted-label">Le dernier récapitulatif est une archive : le dossier a évolué depuis cette version.</p>}<div className="source-chips">{sourceChips.map(item=>{const source=project.sources.find(value=>value.id===item.source_id);return <Button key={item.id} variant="outline" size="sm" onClick={()=>openSource(item.source_id)}><MessagesSquare size={14}/>{item.status==='pending'?'Report':source?.subject.toLocaleLowerCase('fr').includes('devis')?'Devis confirmé':'Budget confirmé'}{source?` · ${formatDate(source.received_at||source.created_at)}`:''}</Button>;})}<Button variant="ghost" size="sm" onClick={()=>{setSummaryId(latest?.id||null);setSummariesOpen(true);}}><History/>Historique des récapitulatifs ({summaries.length})</Button></div></section>
        <section id="project-properties-section" className="project-properties-section"><div className="section-heading"><div><h2>Informations du dossier</h2><p className="muted-label">Demande, coûts, coordonnées et observations.</p></div><Button variant="outline" size="sm" aria-expanded={propertiesOpen} aria-controls="project-properties-form" onClick={()=>void toggleProperties()}><SlidersHorizontal size={14}/>{propertiesOpen?'Masquer les propriétés':'Afficher les propriétés'}</Button></div>{propertiesOpen&&<div id="project-properties-form"><Suspense fallback={<p role="status">Chargement des propriétés…</p>}><ProjectProperties key={id} projectId={id} onChanged={onChanged} onSource={openSource} onDocuments={()=>void changeTab('documents')}/></Suspense></div>}</section>
        <section className="notes-section"><div className="section-heading"><h2>Notes de chantier</h2><Button variant="ghost" size="sm" onClick={()=>void toggleNotes()}><FileText/>{editing?"Fermer l’éditeur":"Modifier les notes"}</Button></div>{editing?<Suspense fallback={<p role="status">Ouverture des notes…</p>}><BlockEditor api={backend} project={project} view="page" canWrite={canWrite} onSaved={onNativeSaved} onMetadata={setMetadata}/></Suspense>:<div className="note-preview">{notesPreview.status==='loading'&&<p className="muted-label" role="status">Chargement de l’aperçu des notes…</p>}{notesPreview.status==='unavailable'&&<p className="muted-label" role="status">L’aperçu natif est indisponible. Le texte enregistré reste affiché ; ouvrez les notes pour consulter la page complète.</p>}{previewNotes.length?previewNotes.map((note:any)=><p key={note.id} className="whitespace-pre-wrap">{note.actionsOnly?'Les actions de cette page se consultent dans l’onglet Actions.':note.content.length>700?note.content.slice(0,700)+"…":note.content}</p>):notesPreview.status==='ready'?<p>Aucune note de chantier enregistrée.</p>:null}</div>}</section>
        <HistoryPanel project={project} onSource={openSource}/>
      </div><aside className="detail-aside">{session?.demo&&session?.auth_required!==true&&<figure><img className="site-image" src={illustration} alt="Illustration de démonstration fournie avec le projet Lovable" width={1536} height={1024}/><figcaption className="muted-label">Illustration de démonstration</figcaption></figure>}<section className="aside-section"><span className="eyebrow">PROCHAINE ACTION</span>{next?<><h3>{next.title}</h3>{next.due&&<p><CalendarDays size={14}/>{formatDate(next.due,next.due)}</p>}{next.owner&&<p><span className="avatar small">{next.owner.trim().split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join('').toLocaleUpperCase('fr')}</span>{next.owner}</p>}<Button variant="outline" size="sm" onClick={()=>void changeTab('actions')}>Voir les actions<ArrowRight size={14}/></Button></>:<p>{nativeReady?"Aucune action en attente dans le suivi enregistré.":"Chargement du suivi des actions…"}</p>}</section><section className="aside-section"><span className="eyebrow">DOCUMENTS DU DOSSIER</span>{catalogue.slice(0,4).map((item,index)=>{const document=item.document;const raw=documentReviewRows.find(value=>objectOf(value)['document_id']===document.id);const state=raw?verifiedDocumentReview(raw,project,document):null;return <Button key={document.id||`${document.source_id}-${index}`} variant="ghost" className="aside-document" onClick={()=>void changeTab('documents')}><FileText/><span><strong>{item.verified&&item.version?`Devis · Version ${item.version}`:document.filename}</strong><small>{[state?.statusLabel,formatCatalogAmount(item.amount)].filter(Boolean).join(' · ')||(document.available?'Original conservé':'Original indisponible')}</small></span><ChevronRight size={14}/></Button>;})}{!documents.length&&<p>Aucune pièce jointe rattachée.</p>}</section><section className="aside-section"><span className="eyebrow">POINTS À VÉRIFIER</span>{reviews.slice(0,4).map(candidate=><p className="check-point" key={candidate.id}><span className="project-dot amber"/>{candidate.label} : {displayValue(candidate.value)}</p>)}{!reviews.length&&<p>Aucune proposition en attente.</p>}</section></aside></div>}
    </div>
    <SummaryDialog open={summariesOpen} project={project} api={backend} canWrite={canWrite} initialId={summaryId} onClose={()=>setSummariesOpen(false)} onChanged={onChanged} onSource={openSource}/>
    <SourcePreview api={api} sourceId={source?.id||null} onClose={()=>setSource(null)} returnFocus={source?.focus||null}/>
  </main>;
}
