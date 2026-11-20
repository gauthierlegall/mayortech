import {useEffect,useState,lazy,Suspense,type CSSProperties} from 'react';
import {Check,Palette,Building2,Users,Plug,ShieldCheck,History,RefreshCw,LayoutGrid,Cpu,Network} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {applyWorkspaceAppearance,getWorkspaceAppearance,saveWorkspaceAppearance,workspacePalettes} from './appearance-adapter';
import {SourcePreview} from './SourcePreview';
import {OrganizationModulesSettings} from './OrganizationModulesSettings';
import {ConnectorsSettings} from './ConnectorsSettings';
import {StructureEnrolementSettings} from './StructureEnrolementSettings';
import {SovereignExportAuditCard} from './SovereignExportAuditCard';

const ConnectionManager=lazy(()=>import('./Connections').then(module=>({default:module.ConnectionManager})));
const MemberAccessManager=lazy(()=>import('./MemberAccessManager').then(module=>({default:module.MemberAccessManager})));
const OrganizationRequests=lazy(()=>import('./OrganizationRequests').then(module=>({default:module.OrganizationRequests})));
const ProjectAccessManager=lazy(()=>import('./ProjectAccessManager').then(module=>({default:module.ProjectAccessManager})));
const tabs=[{id:'appearance',name:'Apparence',icon:Palette},{id:'organization',name:'Organisation',icon:Building2},{id:'structure',name:'Structure & Enrôlement',icon:Network},{id:'modules',name:'Modules & Périmètre',icon:LayoutGrid},{id:'connectors',name:'Connexions & Interopérabilité',icon:Cpu},{id:'members',name:'Membres',icon:Users},{id:'roles',name:'Rôles et droits',icon:ShieldCheck},{id:'audit',name:'Journal',icon:History}] as const;
type Tab=typeof tabs[number]['id'];
const labels:Record<string,string>={organization:'Organisation',members:'Membres',roles:'Rôles et droits',audit:'Journal',workspace:'Chantiers',mail:'Messagerie',read:'Consulter',write:'Modifier',flags:'Classer les messages'};
const events:Record<string,string>={'organization.updated':'Organisation modifiée','project.created':'Chantier créé','source.ingested':'Courriel ajouté','source.assigned':'Courriel rattaché','candidate.accepted':'Information confirmée','candidate.rejected':'Proposition écartée','candidate.corrected':'Information corrigée','candidate.replaced':'Information remplacée','note.added':'Note ajoutée','summary.created':'Récapitulatif préparé','summary.approved':'Récapitulatif validé','native_page.saved':'Notes enregistrées','page.saved':'Notes enregistrées','workspace.note_imported':'Notes du document enregistrées','document.stored':'Document conservé'};
const date=(value:string)=>{const parsed=new Date(value);return Number.isNaN(parsed.valueOf())?'Date indisponible':new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(parsed);};
function selectedTab():Tab{
 if(typeof window==='undefined')return 'appearance';
 const [path,query='']=window.location.hash.replace(/^#/,'').split('?');
 let value=path?.match(/^\/settings\/([^/?]+)/)?.[1]??new URLSearchParams(query||window.location.search).get('section');
 if(value==='connexions'||value==='connections') value='connectors';
 return tabs.some(tab=>tab.id===value)?value as Tab:'appearance';
}

export function Settings(){
 const {api,refresh}=useWorkspace();
 const [tab,setTab]=useState<Tab>(selectedTab),[appearance,setAppearance]=useState(getWorkspaceAppearance);
 const [data,setData]=useState<any>(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(0),[saving,setSaving]=useState(false),[feedback,setFeedback]=useState('');
 const [source,setSource]=useState<{id:string;focus:HTMLElement|null}|null>(null);
 const [membersRevision,setMembersRevision]=useState(0);
 useEffect(()=>{applyWorkspaceAppearance();const changed=()=>setTab(selectedTab());window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed);},[]);
 useEffect(()=>{
  let active=true;setData(null);setError('');setFeedback('');
  if(tab==='appearance'||tab==='members'||tab==='modules'||tab==='connectors'||tab==='structure'){setLoading(false);return()=>{active=false;};}
  setLoading(true);
  const load={organization:()=>api.organization(),members:()=>api.organizationMembers(),roles:()=>api.organizationRoles(),audit:()=>api.organizationAudit()}[tab as 'organization'|'members'|'roles'|'audit'];
  Promise.resolve().then(load).then(value=>{if(active)setData(value);}).catch(cause=>{if(active)setError(cause instanceof Error?cause.message:'Les paramètres ne peuvent pas être chargés. Réessayez.');}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[api,tab,retry]);
 const select=(id:Tab)=>{setTab(id);window.history.replaceState(null,'',window.location.hash.startsWith('#/settings')?`#/settings/${id}`:`#/parametres?section=${id}`);};
 const changeAppearance=(change:Parameters<typeof saveWorkspaceAppearance>[0])=>setAppearance(saveWorkspaceAppearance(change));
 const grants:any[]=data?.items?.[0]?.permissions??[];
 return <main className="content settings-page">
  <div className="page-heading"><div><h1>Paramètres</h1><p>Personnalisez votre espace et consultez ses accès.</p></div></div>
  <nav className="settings-tabs" aria-label="Paramètres">{tabs.map(item=><Button key={item.id} variant={tab===item.id?'secondary':'ghost'} aria-current={tab===item.id?'page':undefined} onClick={()=>select(item.id)}><item.icon aria-hidden="true"/>{item.name}</Button>)}</nav>
  <section className="settings-section" aria-label={tabs.find(item=>item.id===tab)?.name} aria-busy={loading}>
   {loading&&<p role="status">Chargement…</p>}
   {error&&<div className="source-callout" role="alert"><p>{error}</p><Button variant="outline" onClick={()=>setRetry(value=>value+1)}><RefreshCw/>Réessayer</Button></div>}
   {tab==='appearance'&&<><h2>Couleur d’accent</h2><p>La couleur de votre espace de travail, sur cet appareil.</p><div className="palette-options">{workspacePalettes.map(p=><Button key={p.id} variant="outline" className={`palette-choice${appearance.color===p.id?' selected':''}`} aria-pressed={appearance.color===p.id} onClick={()=>changeAppearance({color:p.id})}><span className="swatch" style={{backgroundColor:p.accent} as CSSProperties} aria-hidden="true"/>{p.name}{appearance.color===p.id&&<Check aria-hidden="true"/>}</Button>)}</div><h2 className="mt-10">Espacement</h2><fieldset className="settings-density density-options"><legend className="sr-only">Espacement de l’interface</legend>{[{id:'compact',name:'Compact'},{id:'comfortable',name:'Confortable'}].map(item=><label key={item.id}><input type="radio" name="density" value={item.id} checked={appearance.density===item.id} onChange={()=>changeAppearance({density:item.id as 'compact'|'comfortable'})}/>{item.name}</label>)}</fieldset><p className="settings-note" role="status">Les changements s’appliquent immédiatement et sont conservés sur cet appareil.</p></>}
    {data&&tab==='organization'&&<><h2>Organisation</h2><form className="form-stack max-w-lg" onSubmit={async event=>{event.preventDefault();if(!data.can_manage||saving)return;const values=new FormData(event.currentTarget);setSaving(true);setFeedback('');try{const saved=await api.saveOrganization({name:String(values.get('name')??'').trim(),service:String(values.get('service')??'').trim(),expected_revision:data.revision});setData(saved);setFeedback('');void refresh().catch(()=>{});}catch(cause){setFeedback(cause instanceof Error?cause.message:'La modification n’a pas pu être enregistrée. Votre texte reste visible.');}finally{setSaving(false);}}}><label>Nom de l’organisation<input name="name" defaultValue={data.name??''} required maxLength={200} readOnly={!data.can_manage}/></label><label>Service<input name="service" defaultValue={data.service??''} required maxLength={200} readOnly={!data.can_manage}/></label>{data.can_manage?<Button type="submit" disabled={saving}>{saving?'Enregistrement…':'Enregistrer'}</Button>:<p className="settings-note">Ces informations sont gérées par l’administrateur de l’espace.</p>}{feedback&&<p className="settings-feedback" role="alert">{feedback}</p>}</form><SovereignExportAuditCard/></>}
    {tab==='structure'&&<StructureEnrolementSettings/>}
    {tab==='modules'&&<OrganizationModulesSettings/>}
    {tab==='connectors'&&<ConnectorsSettings/>}
   {tab==='members'&&<Suspense fallback={<p role="status">Chargement des membres…</p>}><OrganizationRequests onChanged={()=>setMembersRevision(value=>value+1)}/><MemberAccessManager key={membersRevision}/></Suspense>}
   {data&&tab==='roles'&&<><h2>Rôles et droits</h2><p>Les droits appliqués par le serveur dans cet espace.</p><div className="permissions-table" role="region" aria-label="Droits des rôles, tableau défilant" tabIndex={0}><table><thead><tr><th scope="col">Droit</th>{(data.items??[]).map((role:any)=><th scope="col" key={role.id}>{role.name}</th>)}</tr></thead><tbody>{grants.map(grant=><tr key={`${grant.resource}:${grant.action}`}><th scope="row">{labels[grant.resource]??grant.resource}<span>{labels[grant.action]??grant.action}</span></th>{(data.items??[]).map((role:any)=>{const allowed=role.permissions?.some((item:any)=>item.resource===grant.resource&&item.action===grant.action&&item.allowed);return <td key={role.id}><span className={allowed?'permission-yes':'permission-no'} aria-label={allowed?'Autorisé':'Non autorisé'}>{allowed?'✓':'—'}</span></td>;})}</tr>)}</tbody></table></div>{data.capabilities?.identity_provider===false&&<p className="settings-note">Les rôles sont consultables. Aucun compte supplémentaire ni invitation n’est créé.</p>}</>}
   {tab==='roles'&&<Suspense fallback={<p role="status">Chargement des accès par dossier…</p>}><ProjectAccessManager/></Suspense>}
   {data&&tab==='audit'&&<><h2>Journal de l’espace</h2>{data.items?.length?<ol className="organization-journal">{data.items.map((entry:any)=><li key={entry.id}><time dateTime={entry.created_at}>{date(entry.created_at)}</time><div><strong>{events[entry.action]??entry.action}</strong>{entry.project_name&&<p><a href={`#/project/${encodeURIComponent(entry.project_id)}`}>{entry.project_name}</a></p>}{entry.actor_label&&<small>{entry.actor_label}</small>}{entry.provenance?.source_id&&<Button variant="link" size="sm" onClick={event=>setSource({id:entry.provenance.source_id,focus:event.currentTarget})}>Voir la source</Button>}</div></li>)}</ol>:<p className="empty">Les décisions et modifications de cet espace apparaîtront ici.</p>}{data.total>data.items?.length&&<p className="settings-note">Les {data.items.length} événements les plus récents sont affichés sur {data.total}.</p>}</>}
   </section>
  <SourcePreview api={api} sourceId={source?.id??null} returnFocus={source?.focus??null} onClose={()=>setSource(null)}/>
 </main>;
}
