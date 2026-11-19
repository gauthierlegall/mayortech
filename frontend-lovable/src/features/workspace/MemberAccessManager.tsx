import {useCallback,useEffect,useId,useRef,useState} from 'react';
import {RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {accessRoleLabels,canManageMembers,memberCatalog,persistMemberAccess,rebaseMemberDraft,refreshAccessState} from './access-management-model.mjs';
import './access-management.css';

export type MemberRole='admin'|'editor'|'reader';
export interface AccessMember {id:string;display_name:string;role:string;role_label?:string;active:boolean|null;revision:number|null;identity_verified?:boolean;kind?:string;email?:string;is_current?:boolean}
export interface MembersCatalog {items:AccessMember[];can_manage:boolean;capabilities?:{identity_provider?:boolean;member_management?:boolean;invitations?:boolean}}
const explain:Record<MemberRole,string>={admin:'Gère l’espace et accède à tous les dossiers.',editor:'Modifie les dossiers qui lui sont attribués.',reader:'Consulte les dossiers qui lui sont attribués.'};
const message=(failure:unknown)=>failure instanceof Error?failure.message:'Les accès ne peuvent pas être modifiés. Votre saisie reste disponible.';
const draftOf=(member:AccessMember)=>({role:member.role as MemberRole,active:member.active===true});

export function MemberAccessManager(){
 const {session,bootstrap}=useWorkspace();
 return <MembersEditor key={JSON.stringify([session?.actor?.tenant_id,session?.actor?.actor_id,bootstrap?.permissions?.organization?.write])}/>;
}
function MembersEditor(){
 const {api,bootstrap,refresh}=useWorkspace();
 const [catalog,setCatalog]=useState<MembersCatalog|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const alive=useRef(true),epoch=useRef(0);
 const load=useCallback(async()=>{
  const token=++epoch.current;setLoading(true);setError('');
  try{const next=memberCatalog(await api.organizationMembers()) as MembersCatalog;if(!alive.current||epoch.current!==token)throw Error('L’accès actif a changé.');setCatalog(next);return next;}
  catch(failure){if(alive.current&&epoch.current===token)setError(message(failure));throw failure;}
  finally{if(alive.current&&epoch.current===token)setLoading(false);}
 },[api]);
 useEffect(()=>{alive.current=true;void load().catch(()=>{});return()=>{alive.current=false;epoch.current++;};},[load]);
 const changed=async()=>{await refreshAccessState(load,refresh);};
 const canManage=canManageMembers(catalog,bootstrap?.permissions);
 return <div className="access-management" aria-busy={loading}>
  <div className="access-heading"><div><h2>Membres de l’organisation</h2><p>{canManage?'Autorisez les comptes professionnels et choisissez leur rôle dans l’espace.':'Les membres et leurs rôles dans cet espace.'}</p></div><Button variant="outline" size="sm" disabled={loading} onClick={()=>void load().catch(()=>{})}><RefreshCw size={15}/>Actualiser la liste</Button></div>
  {loading&&!catalog&&<p role="status">Chargement des membres…</p>}
  {error&&<p className="form-error" role="alert">{error}</p>}
  {catalog?.capabilities?.identity_provider===true&&<p className="access-help">Les comptes apparaissent après une connexion professionnelle. L’accès reste désactivé jusqu’à l’autorisation d’un administrateur. Aucun courriel d’invitation n’est envoyé depuis cet écran.</p>}
  {catalog?.capabilities?.identity_provider===false&&<p className="access-help">Cet espace utilise un accès partagé. La gestion de comptes individuels exige la connexion professionnelle de la collectivité.</p>}
  <div className="access-member-list">{catalog?.items.map(member=><MemberRow key={member.id} member={member} canManage={canManage} api={api} reload={load} onChanged={changed}/>)}</div>
  {catalog&&!catalog.items.length&&<p>Aucun compte n’a encore demandé d’accès.</p>}
 </div>;
}
function MemberRow({member,canManage,api,reload,onChanged}:{member:AccessMember;canManage:boolean;api:any;reload:()=>Promise<MembersCatalog>;onChanged:()=>Promise<void>}){
 const id=useId(),alive=useRef(true),busyRef=useRef(false);
 const [baseline,setBaseline]=useState(member),[draft,setDraft]=useState(()=>draftOf(member)),[busy,setBusy]=useState(false),[error,setError]=useState(''),[conflict,setConflict]=useState(false),[review,setReview]=useState(false);
 const current=useRef({baseline,draft});current.current={baseline,draft};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 useEffect(()=>{
  const previous=current.current;
  if(member.revision===previous.baseline.revision&&member.role===previous.baseline.role&&member.active===previous.baseline.active)return;
  const dirty=previous.draft.role!==previous.baseline.role||previous.draft.active!==previous.baseline.active;
  const rebased=rebaseMemberDraft(previous.baseline,previous.draft,member);
  setBaseline(member);setDraft(rebased.draft as {role:MemberRole;active:boolean});setReview(dirty);setConflict(false);
 },[member]);
 const dirty=draft.role!==baseline.role||draft.active!==baseline.active;
 const guard=()=>{if(!alive.current)throw Error('L’accès actif a changé.');};
 async function save(){
  if(!canManage||busyRef.current||conflict||!dirty)return;
  busyRef.current=true;setBusy(true);setError('');
  try{
   const saved=await persistMemberAccess(api,baseline,draft,guard) as AccessMember;guard();setBaseline(saved);setDraft(draftOf(saved));setReview(false);
   try{await onChanged();}catch{if(alive.current)setError('Les droits ont été modifiés. Actualisez la liste pour retrouver l’état actuel de l’espace.');}
  }catch(failure){if(alive.current){setError(message(failure));setConflict((failure as any)?.detail?.code==='stale_revision');}}
  finally{busyRef.current=false;if(alive.current)setBusy(false);}
 }
 async function reloadDraft(){
  if(busyRef.current)return;busyRef.current=true;setBusy(true);
  try{const next=await reload();guard();const latest=next.items.find(item=>item.id===baseline.id);if(!latest)throw Error('Ce compte n’est plus visible dans votre espace.');const rebased=rebaseMemberDraft(baseline,draft,latest);setBaseline(latest);setDraft(rebased.draft as {role:MemberRole;active:boolean});setConflict(false);setReview(true);setError('');}
  catch(failure){if(alive.current)setError(message(failure));}
  finally{busyRef.current=false;if(alive.current)setBusy(false);}
 }
 const storedRole=accessRoleLabels[member.role as MemberRole]||member.role_label||'Accès partagé';
 return <article className="access-member" aria-labelledby={id}>
  <div className="access-member-identity"><h3 id={id}>{member.display_name}{member.is_current&&<small>Votre compte</small>}</h3>{member.email&&<p>{member.email}</p>}<p>{storedRole}{member.active===false?' · Accès désactivé':member.active===true?' · Accès autorisé':''}</p></div>
  {canManage?<form className="access-member-form" onSubmit={event=>{event.preventDefault();void save();}} aria-busy={busy}>
   <div className="access-role-field"><label htmlFor={`${id}-role`}>Rôle de {member.display_name}</label><select id={`${id}-role`} value={draft.role} onChange={event=>setDraft(previous=>({...previous,role:event.target.value as MemberRole}))} disabled={busy}>{(['reader','editor','admin'] as const).map(role=><option key={role} value={role}>{accessRoleLabels[role]}</option>)}</select></div>
   <label className="access-check"><input type="checkbox" checked={draft.active} onChange={event=>setDraft(previous=>({...previous,active:event.target.checked}))} disabled={busy}/>Autoriser la connexion de {member.display_name}</label>
   <p className="access-role-description">{explain[draft.role]}</p>
   {review&&dirty&&<p role="status" className="access-review">La liste a été actualisée. Votre saisie est conservée : vérifiez-la avant de confirmer.</p>}
   {error&&<p role="alert" className="form-error">{error}</p>}
   <div className="access-row-actions"><Button type="submit" size="sm" disabled={busy||!dirty||conflict}>{busy?'Modification…':member.active===false&&draft.active?'Autoriser cet accès':'Enregistrer les droits'}</Button>{conflict&&<Button type="button" variant="outline" size="sm" disabled={busy} onClick={()=>void reloadDraft()}>Recharger en gardant ma saisie</Button>}</div>
  </form>:<p className="access-role-description">{explain[member.role as MemberRole]||'Les accès sont gérés par l’administrateur de l’espace.'}</p>}
 </article>;
}
