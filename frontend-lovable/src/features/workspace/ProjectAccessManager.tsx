import {useCallback,useEffect,useId,useRef,useState} from 'react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {accessRoleLabels,canManageMembers,memberCatalog,persistProjectAccess,projectAccessDto,rebaseProjectChoices} from './access-management-model.mjs';
import type {AccessMember,MemberRole,MembersCatalog} from './MemberAccessManager';
import './access-management.css';

interface ProjectAccess {project_id:string;revision:number;items:{id:string;display_name:string;role:string}[];administrators_have_access:true}
const message=(failure:unknown)=>failure instanceof Error?failure.message:'Les accès ne peuvent pas être chargés. Vos choix restent conservés.';
export function ProjectAccessManager(){
 const {session,bootstrap}=useWorkspace();
 return <DossierAccessEditor key={JSON.stringify([session?.actor?.tenant_id,session?.actor?.actor_id,bootstrap?.permissions?.organization?.write])}/>;
}
function DossierAccessEditor(){
 const {api,state,bootstrap,refresh}=useWorkspace();
 const choiceId=useId();
 const [members,setMembers]=useState<MembersCatalog|null>(null),[projectId,setProjectId]=useState(''),[access,setAccess]=useState<ProjectAccess|null>(null),[choices,setChoices]=useState<Record<string,boolean>>({});
 const [loading,setLoading]=useState(true),[saving,setSaving]=useState(''),[error,setError]=useState(''),[conflict,setConflict]=useState(false),[review,setReview]=useState(false);
 const alive=useRef(true),epoch=useRef(0),savingRef=useRef(false),selection=useRef(projectId);selection.current=projectId;
 const canManage=canManageMembers(members,bootstrap?.permissions);
 useEffect(()=>{alive.current=true;let current=true;api.organizationMembers().then((raw:unknown)=>{if(current)setMembers(memberCatalog(raw) as MembersCatalog);}).catch((failure:unknown)=>{if(current)setError(message(failure));}).finally(()=>{if(current)setLoading(false);});return()=>{current=false;alive.current=false;epoch.current++;};},[api]);
 const load=useCallback(async(ident:string,keepChoices=false)=>{
  if(!ident)return;const token=++epoch.current;setLoading(true);setError('');
  try{
   const [raw,catalog]=await Promise.all([api.projectAccess(ident),api.organizationMembers()]);
   if(!alive.current||epoch.current!==token||selection.current!==ident)return;
   const next=projectAccessDto(raw,ident) as ProjectAccess;setMembers(memberCatalog(catalog) as MembersCatalog);setAccess(next);setChoices(previous=>keepChoices?rebaseProjectChoices(previous,next):{});setConflict(false);setReview(keepChoices);
  }catch(failure){if(alive.current&&epoch.current===token)setError(message(failure));}
  finally{if(alive.current&&epoch.current===token)setLoading(false);}
 },[api]);
 useEffect(()=>{setAccess(null);setError('');setChoices({});setConflict(false);setReview(false);if(projectId&&canManage)void load(projectId);},[projectId,canManage,load]);
 async function save(member:AccessMember){
  if(!access||!canManage||conflict||savingRef.current||!(member.id in choices))return;
  const ident=projectId;savingRef.current=true;setSaving(member.id);setError('');
  const guard=()=>{if(!alive.current||selection.current!==ident)throw Error('Le dossier actif a changé.');};
  try{const next=await persistProjectAccess(api,access,member,choices[member.id],guard) as ProjectAccess;guard();setAccess(next);setChoices(previous=>rebaseProjectChoices(previous,next));setReview(false);try{await refresh();}catch{if(alive.current)setError('L’accès a été modifié. Actualisez la page pour retrouver la liste des chantiers.');}}
  catch(failure){if(alive.current){setError(message(failure));setConflict((failure as any)?.detail?.code==='stale_revision');}}
  finally{savingRef.current=false;if(alive.current)setSaving('');}
 }
 const pending=Object.keys(choices).length>0;
 const eligible=members?.items.filter(member=>member.active===true&&['reader','editor'].includes(member.role))||[];
 const administrators=members?.items.filter(member=>member.active===true&&member.role==='admin')||[];
 const granted=new Set(access?.items.map(member=>member.id)||[]);
 const unavailable=Object.keys(choices).filter(id=>!eligible.some(member=>member.id===id));
 return <section className="access-management project-access-manager" aria-busy={loading}>
  <h2>Accès par dossier</h2><p className="access-help">Le rôle lecteur ou éditeur s’applique uniquement aux dossiers attribués. Les administrateurs ont accès à tous les dossiers.</p>
  {!canManage?<><p>Les attributions sont gérées par un administrateur. Vous consultez ici les droits de votre espace en lecture seule.</p>{loading&&<p role="status">Chargement des droits…</p>}</>:<>
   <div className="access-project-choice"><label htmlFor={choiceId}>Dossier à gérer</label><select id={choiceId} value={projectId} disabled={loading||Boolean(saving)||pending} onChange={event=>setProjectId(event.target.value)}><option value="">Choisir un dossier…</option>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}{project.ref?` · ${project.ref}`:''}</option>)}</select></div>
   {pending&&<div className="access-pending"><p>Enregistrez ou annulez vos choix avant de changer de dossier.</p><Button variant="ghost" size="sm" disabled={Boolean(saving)} onClick={()=>{setChoices({});setReview(false);}}>Annuler les modifications</Button></div>}
   {access&&<>
    <p className="access-help">Administrateurs : {administrators.map(member=>member.display_name).join(', ')||'gérés par l’organisation'}. Leur accès est permanent tant que leur rôle administrateur est actif.</p>
    {review&&pending&&<p className="access-review" role="status">Les accès actuels ont été rechargés. Vos choix sont conservés : vérifiez-les avant de confirmer chaque modification.</p>}
    {unavailable.length>0&&<p className="form-error" role="alert">Certains comptes de votre saisie ne sont plus actifs. Leurs choix sont conservés mais ne peuvent pas être appliqués. Annulez-les pour changer de dossier.</p>}
    <div className="access-grant-list">{eligible.map(member=>{
     const checked=member.id in choices?choices[member.id]:granted.has(member.id),dirty=checked!==granted.has(member.id);
     return <div className="access-grant-row" key={member.id}><div><strong>{member.display_name}</strong><small>{accessRoleLabels[member.role as MemberRole]} · {granted.has(member.id)?'Accès accordé':'Aucun accès à ce dossier'}</small></div><label className="access-check"><input type="checkbox" checked={checked} disabled={Boolean(saving)||loading} onChange={event=>{const value=event.target.checked;setChoices(previous=>{const next={...previous,[member.id]:value};if(value===granted.has(member.id))delete next[member.id];return next;});}}/>Autoriser {member.display_name} sur ce dossier</label><Button size="sm" disabled={Boolean(saving)||loading||conflict||!dirty} onClick={()=>void save(member)}>{saving===member.id?'Modification…':'Enregistrer'}</Button></div>;
    })}</div>{!eligible.length&&<p>Aucun membre lecteur ou éditeur actif à attribuer. Autorisez d’abord son compte dans Membres.</p>}
   </>}
  </>}
  {error&&<p role="alert" className="form-error">{error}</p>}
  {canManage&&projectId&&<Button variant="outline" size="sm" disabled={Boolean(saving)||loading} onClick={()=>void load(projectId,pending)}>{pending?'Recharger en gardant mes choix':'Actualiser les accès'}</Button>}
 </section>;
}
