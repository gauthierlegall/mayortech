import {useEffect,useRef,useState,type FormEvent} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowRight,ArrowLeft,Landmark,Mail,ShieldCheck,Building2,KeyRound,RefreshCw} from 'lucide-react';
import {beginProfessionalLogin,PRO_AUTH_ERROR,PRO_AUTH_REAUTHENTICATE} from './features/workspace/pro-auth-client.mjs';
import {portalMode,portalCapabilities,portalDestination,legacyDemoDestination,validLoginEmail,privateEntry} from './features/workspace/auth-portal-model.mjs';
import '@fontsource-variable/dm-sans';
import './auth.css';

const mode=portalMode(window.location.pathname) as 'login'|'signup'|'recovery';
const copy={
 login:{
  title:'Bienvenue dans votre espace.',
  description:'Retrouvez les dossiers et les actions de votre collectivité.',
  help:'Vous saisirez votre mot de passe, puis le code à 6 chiffres affiché dans votre application d’authentification.',
  button:'Se connecter',
  pending:'Ouverture de la connexion…',
 },
 signup:{
  title:'Votre compte, votre collectivité.',
  description:'Créez votre compte personnel. Vous choisirez ensuite l’organisation à rejoindre.',
  help:'Confirmez votre adresse avec le lien reçu par email, puis choisissez votre mot de passe. Pour la double authentification, ouvrez une application d’authentification sur votre téléphone, scannez le QR code et saisissez le code à 6 chiffres qu’elle affiche.',
  button:'Créer mon compte',
  pending:'Ouverture de l’inscription…',
 },
 recovery:{
  title:'Retrouver votre accès.',
  description:'Indiquez l’adresse associée à votre compte pour ouvrir la récupération du mot de passe.',
  help:'Vous recevrez un lien de réinitialisation si cette adresse est associée à un compte.',
  button:'Récupérer mon accès',
  pending:'Ouverture de la récupération…',
 },
};
const current=copy[mode];
async function request(path:string,body?:unknown){
 const response=await fetch(path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{Accept:'application/json'}:{Accept:'application/json','Content-Type':'application/json','X-Requested-With':'Travaux'},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error('Le service de connexion ne répond pas. Réessayez dans un instant.');
 return response.json();
}
function AuthPortal(){
 const [capabilities,setCapabilities]=useState<ReturnType<typeof portalCapabilities>|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[email,setEmail]=useState(''),[error,setError]=useState(''),[status,setStatus]=useState('');
 const [privateHref,setPrivateHref]=useState<string|null>(null);
 const inFlight=useRef(false),mounted=useRef(true);
 async function load(){
  setLoading(true);setError('');
  try{
   const options=await request('/api/v1/auth/options');if(!mounted.current)return;
   const view=portalCapabilities(options);setCapabilities(view);setPrivateHref(privateEntry(options,mode));
   // A public demo cookie is never an individual account. No business data is requested here.
   if(!view.demo){const session=await request('/api/v1/session');if(!mounted.current)return;const destination=portalDestination(session);if(destination){location.replace(destination);return;}}
  }catch{if(mounted.current)setError('Le service de connexion est inaccessible. Vérifiez votre connexion puis réessayez.');}
  finally{if(mounted.current)setLoading(false);}
 }
 useEffect(()=>{
  mounted.current=true;
  const oldDemo=legacyDemoDestination(location.pathname,location.hash);
  if(oldDemo){location.replace(oldDemo);return;}
  const marker=new URLSearchParams(location.search).get('auth');
  const legacyMarker=location.hash.startsWith('#/connexion?')?new URLSearchParams(location.hash.split('?')[1]).get('auth'):null;
  if(marker==='failed'||legacyMarker==='failed')setStatus('La connexion n’a pas abouti. Réessayez avec votre compte personnel.');
  if(marker==='pending'||legacyMarker==='pending')setStatus('Votre demande d’accès attend la validation de l’administrateur de l’organisation.');
  if(marker==='reauthenticate')setStatus(PRO_AUTH_REAUTHENTICATE);
  // Remove callback markers promptly; never display provider errors, codes or query text.
  if(location.search||location.hash)history.replaceState(null,'',location.pathname);
  void load();return()=>{mounted.current=false;};
 },[]);
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(inFlight.current||!capabilities?.[mode])return;
  const hint=email.trim();if(!validLoginEmail(hint)){setError('Saisissez une adresse email complète, par exemple prenom@collectivite.fr.');return;}
  inFlight.current=true;setBusy(true);setError('');setStatus('');
  try{await beginProfessionalLogin({authStart:(payload:unknown)=>request('/api/v1/auth/start',payload)},(url:string)=>location.assign(url),mode,hint);}
  catch{if(mounted.current){setError(PRO_AUTH_ERROR);setBusy(false);}inFlight.current=false;}
 }
 const available=capabilities?.[mode]===true;
 return <div className="auth-page">
  <a className="auth-skip" href="#auth-main">Aller à la connexion</a>
  <header className="auth-header"><a className="auth-brand" href="/connexion.html" aria-label="MayorTech, connexion"><span><Landmark size={22}/></span>MayorTech<span className="auth-brand-dot">.</span></a><a className="auth-header-link" href={mode==='signup'?'/connexion.html':'/inscription.html'}>{mode==='signup'?'Déjà un compte ?':'Première visite ?'} <strong>{mode==='signup'?'Se connecter':'Créer un compte'}<ArrowRight size={15}/></strong></a></header>
  <div className="auth-layout">
   <aside className="auth-story" aria-label="Votre espace de travail municipal">
    <h2>Les dossiers avancent.<br/>Vous gardez le fil.</h2>
    <p>Les échanges, les documents et les actions se retrouvent dans un même espace de travail, au service de votre collectivité.</p>
    <ol className="auth-journey">
     <li><span><KeyRound size={19}/></span><div><strong>Un compte personnel</strong><p>Votre identité et vos accès vous appartiennent.</p></div></li>
     <li><span><Building2 size={19}/></span><div><strong>Votre organisation</strong><p>Rejoignez l’espace de votre collectivité.</p></div></li>
     <li><span><Mail size={19}/></span><div><strong>Les échanges utiles</strong><p>Reliez ensuite votre messagerie aux dossiers.</p></div></li>
    </ol>
    <p className="auth-story-note">Un compte ne donne pas accès aux données d’une mairie : chaque organisation autorise ses membres.</p>
   </aside>
   <main id="auth-main" className="auth-main" tabIndex={-1}>
    <div className="auth-form-wrap">
     {mode==='recovery'&&<a href="/connexion.html" className="auth-back"><ArrowLeft size={16}/>Retour à la connexion</a>}
     <h1>{current.title}</h1><p className="auth-description">{current.description}</p>
     {status&&<p className="auth-notice" role="status">{status}</p>}
     {error&&<p className="auth-error" role="alert">{error}</p>}
     {loading?<p className="auth-loading" role="status">Vérification du service de connexion…</p>:available?<form className="auth-form" onSubmit={event=>void submit(event)} aria-busy={busy}>
      <label htmlFor="account-email">Adresse email</label><input id="account-email" name="email" type="email" autoComplete="username" inputMode="email" maxLength={254} required value={email} onChange={event=>setEmail(event.target.value)} placeholder="prenom@collectivite.fr" disabled={busy} aria-describedby="account-email-help"/>
      <p id="account-email-help" className="auth-field-help">{current.help}</p>
      <button className="auth-primary" type="submit" disabled={busy}>{busy?current.pending:current.button}<ArrowRight size={18}/></button>
      {mode==='login'&&<a className="auth-recovery" href="/mot-de-passe-oublie.html">Mot de passe oublié ?</a>}
     </form>:privateHref?<div className="auth-private-handoff"><a className="auth-primary" href={privateHref}>{current.button}<ArrowRight size={18}/></a><p className="auth-field-help">La connexion s’ouvre dans votre espace privé.</p>{mode==='login'&&<a className="auth-recovery" href="/mot-de-passe-oublie.html">Mot de passe oublié ?</a>}</div>:capabilities?<div className="auth-unavailable">
      <div className="auth-unavailable-heading"><ShieldCheck size={21}/><h2>{capabilities.pilot?'Cet espace utilise un accès pilote':mode==='recovery'?'La récupération n’est pas encore activée':'Les comptes sont en cours d’activation'}</h2></div>
      <p>{capabilities.pilot?'L’accès pilote est géré par l’administrateur. La création de comptes personnels sera proposée après l’activation du service de connexion.':mode==='recovery'?'L’envoi des emails de récupération doit être configuré par l’administrateur. Aucun lien ne peut être envoyé pour le moment.':'Le service de connexion doit être activé avant de créer un compte ou de relier une messagerie réelle. Vos identifiants ne sont pas demandés ici.'}</p>
      <button className="auth-secondary" type="button" onClick={()=>void load()}><RefreshCw size={16}/>Vérifier à nouveau</button>
      {capabilities.pilot&&<a className="auth-primary" href="/espace.html#/">Ouvrir l’accès pilote<ArrowRight size={18}/></a>}
     </div>:<button className="auth-secondary" type="button" onClick={()=>void load()}><RefreshCw size={16}/>Réessayer la connexion</button>}
     {(mode==='login'||capabilities?.demo)&&<a className="auth-demo-link" href="/demo.html#/">
      Découvrir la démo<ArrowRight size={17} aria-hidden="true"/><span>Explorez des dossiers fictifs sans créer de compte.</span>
     </a>}
     <section className="auth-safety" aria-labelledby="auth-privacy-title">
      <ShieldCheck size={17} aria-hidden="true"/>
      <div>
       <h2 id="auth-privacy-title">Vos données et le RGPD européen</h2>
       <p>La double authentification protège votre compte. Votre organisation décide qui peut accéder à ses dossiers.</p>
       <a href="/confidentialite.html">Confidentialité et exercice de vos droits</a>
      </div>
     </section>
    </div>
   </main>
  </div>
  <footer className="auth-footer"><span>MayorTech · L’espace de travail des collectivités</span><nav aria-label="Informations légales"><a href="/mentions-legales.html">Mentions légales</a><a href="/confidentialite.html">Confidentialité</a></nav></footer>
 </div>;
}
createRoot(document.getElementById('auth-root')!).render(<AuthPortal/>);
