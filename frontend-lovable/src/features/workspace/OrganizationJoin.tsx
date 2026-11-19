import {useCallback,useEffect,useId,useRef,useState} from 'react';
import {LogOut,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {organizationAction,organizationCode,organizationsCatalog,requestOrganizationCode,requestOrganizationJoin,requiresOrganization,ORGANIZATION_PENDING,ORGANIZATION_REJECTED} from './organization-join-model.mjs';
import './organization-join.css';

interface Organization {id:string;name:string;is_test:boolean;can_self_join:boolean;membership_status:'joined'|'pending'|'rejected'|'not_joined';can_enter:boolean}
interface Catalog {organization_required:boolean;items:Organization[];test_join_code?:string}
const message=(failure:unknown)=>failure instanceof Error?failure.message:'Les organisations ne peuvent pas être chargées. Réessayez.';

function useAccountExit(working:{current:boolean},guard:()=>void,onError:(value:string)=>void){
 const {api}=useWorkspace();const [leaving,setLeaving]=useState(false);
 async function changeAccount(){
  if(working.current)return;working.current=true;setLeaving(true);onError('');
  try{await api.logout();guard();window.location.assign('/connexion.html');}
  catch{
   working.current=false;try{guard();}catch{return;}
   setLeaving(false);onError('La déconnexion n’a pas abouti. Réessayez avant de changer de compte.');
  }
 }
 return {leaving,changeAccount};
}
function IncompleteAccountChoice(){
 const {refresh}=useWorkspace();const alive=useRef(true),working=useRef(false);const [error,setError]=useState('');
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const guard=()=>{if(!alive.current)throw Error('Le compte actif a changé.');};
 const {leaving,changeAccount}=useAccountExit(working,guard,setError);
 return <main className="content organization-choice-gate"><h1>Rejoindre une organisation</h1><p className="form-error" role="alert">La session de votre compte est incomplète. Rechargez votre connexion avant de continuer.</p>{error&&<p className="form-error" role="alert">{error}</p>}<div className="organization-choice-actions"><Button disabled={leaving} onClick={()=>void refresh().catch(()=>{})}>Réessayer</Button><Button variant="outline" disabled={leaving} onClick={()=>void changeAccount()}><LogOut size={15}/>{leaving?'Déconnexion…':'Changer de compte'}</Button></div></main>;
}

export function OrganizationJoin(){
 const {session}=useWorkspace();const account=session?.account;
 if(typeof account?.id!=='string'||!account.id)return <IncompleteAccountChoice/>;
 return <OrganizationChooser key={account.id} accountId={account.id} displayName={typeof account.display_name==='string'?account.display_name:''}/>;
}
function OrganizationChooser({accountId,displayName}:{accountId:string;displayName:string}){
 const {api,refresh}=useWorkspace();
 const codeId=useId(),input=useRef<HTMLInputElement>(null);
 const [catalog,setCatalog]=useState<Catalog|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(''),[error,setError]=useState(''),[joined,setJoined]=useState(''),[code,setCode]=useState(''),[codeError,setCodeError]=useState('');
 const alive=useRef(true),epoch=useRef(0),working=useRef(false);
 const guard=()=>{if(!alive.current)throw Error('Le compte actif a changé. Rechargez la connexion.');};
 const {leaving,changeAccount}=useAccountExit(working,guard,setError);
 const load=useCallback(async()=>{
  const token=++epoch.current;setLoading(true);setError('');
  try{const next=organizationsCatalog(await api.accountOrganizations()) as Catalog;if(alive.current&&epoch.current===token)setCatalog(next);}
  catch(failure){if(alive.current&&epoch.current===token){setCatalog(null);setError(message(failure));}}
  finally{if(alive.current&&epoch.current===token)setLoading(false);}
 },[api]);
 useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;epoch.current++;};},[load]);
 async function openWorkspace(){
  const next=await api.session();guard();
  if(next?.authenticated!==true||requiresOrganization(next)||next?.account?.id!==accountId)throw Error('L’espace n’a pas pu être ouvert. Réessayez l’ouverture ou reconnectez-vous.');
  await refresh();
 }
 async function choose(organization:Organization){
  if(!catalog||working.current||joined)return;working.current=true;setBusy(organization.id);setError('');
  try{
   const result=await requestOrganizationJoin({api,catalog,organizationId:organization.id,assertCurrent:guard});guard();
   setJoined(organization.id);await openWorkspace();
  }catch(failure){if(alive.current)setError(message(failure));}
  finally{working.current=false;if(alive.current)setBusy('');}
 }
 async function submitCode(){
  if(!catalog||working.current||joined)return;
  setCodeError('');setError('');
  try{organizationCode(code);}catch(failure){setCodeError(message(failure));input.current?.focus();return;}
  working.current=true;setBusy('code');
  try{
   const result=await requestOrganizationCode({api,code,assertCurrent:guard});guard();
   if(result.status==='joined'){setJoined(result.organization.id);await openWorkspace();}
   else setCatalog(previous=>previous?{...previous,items:[...previous.items.filter(item=>item.id!==result.organization.id),{...result.organization,membership_status:result.status as 'pending'|'rejected',can_self_join:false,can_enter:false}]}:previous);
  }catch(failure){if(alive.current)setError(message(failure));}
  finally{working.current=false;if(alive.current)setBusy('');}
 }
 async function retryOpening(){
  if(working.current)return;working.current=true;setBusy(joined);setError('');
  try{await openWorkspace();}catch(failure){if(alive.current)setError(message(failure));}
  finally{working.current=false;if(alive.current)setBusy('');}
 }
 const known=catalog?.items.filter(item=>item.membership_status!=='not_joined')??[];
 const canRequest=Boolean(catalog)&&known.length===0&&!joined;
 return <main id="main-content" className="content organization-choice-gate" aria-busy={loading||Boolean(busy)||leaving}>
  <header><h1>Rejoindre une organisation</h1>{displayName&&<p className="organization-account">Compte : {displayName}</p>}<p>Saisissez le code transmis par votre organisation pour demander l’accès à son espace.</p></header>
  {loading&&!catalog&&<p role="status">Chargement de votre accès…</p>}
  {error&&<p role="alert" className="form-error">{error}</p>}
  {canRequest&&<form className="organization-code-form" noValidate onSubmit={event=>{event.preventDefault();void submitCode();}}>
   <label htmlFor={codeId}>Code de l’organisation</label>
   <input ref={input} id={codeId} name="organization-code" value={code} onChange={event=>{setCode(event.target.value);setCodeError('');}} required maxLength={64} autoComplete="off" autoCapitalize="characters" spellCheck={false} aria-invalid={Boolean(codeError)} aria-describedby={`${codeId}-help${codeError?` ${codeId}-error`:''}`} disabled={Boolean(busy)||leaving||loading}/>
   <p id={`${codeId}-help`} className="organization-code-help">Ce code est fourni par l’administrateur de votre organisation.</p>
   {codeError&&<p id={`${codeId}-error`} className="form-error" role="alert">{codeError}</p>}
   <Button type="submit" disabled={Boolean(busy)||leaving||loading}>{busy==='code'?'Envoi de la demande…':'Rejoindre l’organisation'}</Button>
   {catalog?.test_join_code&&<p className="organization-test-hint">Pour la démonstration fictive {catalog.items.find(item=>item.is_test)?.name}, utilisez le code <strong>{catalog.test_join_code}</strong>. L’accès aux dossiers fictifs est accepté automatiquement.</p>}
  </form>}
  {known.length>0&&<ul className="organization-choices">{known.map(organization=>{
   const action=organizationAction(organization);
   return <li key={organization.id} className="organization-choice-row"><div><h2>{organization.name}</h2>{action==='pending'?<><p className="organization-state-title">Demande en attente</p><p role="status" className="organization-pending">{ORGANIZATION_PENDING}</p></>:action==='rejected'?<><p className="organization-state-title">Demande refusée</p><p role="status" className="organization-pending">{ORGANIZATION_REJECTED}</p></>:<p>{action==='enter'?'Votre accès à cet espace est autorisé.':'Votre accès à cet espace est désactivé. Contactez son administrateur.'}</p>}{organization.is_test&&<p>Données de démonstration fictives.</p>}</div>{action==='enter'&&<Button disabled={Boolean(busy)||leaving||loading||Boolean(joined)} onClick={()=>void choose(organization)}>{busy===organization.id?'Ouverture…':'Ouvrir cet espace'}</Button>}</li>;
  })}</ul>}
  <div className="organization-choice-actions">{joined?<Button disabled={Boolean(busy)||leaving} onClick={()=>void retryOpening()}>{busy?'Ouverture…':'Réessayer l’ouverture'}</Button>:<Button variant="ghost" disabled={loading||Boolean(busy)||leaving} onClick={()=>void load()}><RefreshCw size={15}/>Actualiser mon accès</Button>}<Button variant="outline" disabled={Boolean(busy)||leaving} onClick={()=>void changeAccount()}><LogOut size={15}/>{leaving?'Déconnexion…':'Changer de compte'}</Button></div>
 </main>;
}
