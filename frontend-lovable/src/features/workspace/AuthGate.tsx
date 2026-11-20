import {Fragment,useEffect,useRef,useState,type ReactNode,type FormEvent} from 'react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {authFailureMessage,authPresentation,beginProfessionalLogin,PRO_AUTH_ERROR,PRO_AUTH_PENDING} from './pro-auth-client.mjs';
import {requiresOrganization} from './organization-join-model.mjs';
import {OrganizationJoin} from './OrganizationJoin';
import {workspaceIdentity} from './workspace-scope.mjs';
import {WorkProfileChoice} from './WorkProfileChoice';

/** Authentication stays on the server; this component never stores credentials. */
export function AuthGate({children}:{children:ReactNode}){
 const hash = typeof window === 'undefined' ? '' : window.location.hash;
 if (hash.includes('quick-sign') || hash.includes('suivi') || hash.includes('registre-public')) {
   return <Fragment>{children}</Fragment>;
 }
 const {session,api,refresh,workProfile,workProfileLoading}=useWorkspace();
 const [password,setPassword]=useState(''),[pending,setPending]=useState(false),[intent,setIntent]=useState<'login'|'signup'>('login'),[error,setError]=useState(()=>authFailureMessage(typeof window==='undefined'?'':window.location.hash));
 const inFlight=useRef(false);
 const auth=authPresentation(session);
 useEffect(()=>{if(session?.authenticated!==true&&auth.method==='oidc')window.location.replace('/connexion.html');},[session?.authenticated,auth.method]);
 if(requiresOrganization(session))return <OrganizationJoin/>;
 if(session?.authenticated===true&&(workProfile.status==='choose'||workProfile.status==='unavailable'))return <WorkProfileChoice key={workspaceIdentity(session)}/>;
 if(session?.authenticated===true&&workProfileLoading)return <main className="content auth-gate"><p role="status">Ouverture de votre profil de travail…</p></main>;
 if(session?.authenticated===true)return <Fragment key={workspaceIdentity(session)}>{children}</Fragment>;

 async function connect(event:FormEvent<HTMLFormElement>){
  event.preventDefault();
  if(inFlight.current)return;
  inFlight.current=true;setPending(true);setError('');
  try{await api.login(password);await refresh();setPassword('');}
  catch(cause){setError(cause instanceof Error?cause.message:'La connexion n’a pas pu aboutir. Réessayez.');}
  finally{inFlight.current=false;setPending(false);}
 }

 async function connectProfessional(nextIntent:'login'|'signup'='login'){
  if(inFlight.current||!auth.ssoAvailable)return;
  if(nextIntent==='signup'&&!auth.signupAvailable)return;
  inFlight.current=true;setIntent(nextIntent);setPending(true);setError('');
  try{await beginProfessionalLogin(api,(url:string)=>window.location.assign(url),nextIntent);}
  catch{setError(PRO_AUTH_ERROR);inFlight.current=false;setPending(false);}
 }

 return <main id="main-content" className="content auth-gate" style={{maxWidth:520,width:'100%',margin:'10vh auto 0',padding:24}}>
  <h1>{auth.method==='demo'?'Ouverture de la démonstration':auth.method==='oidc'?auth.label:'Connexion à votre espace'}</h1>
  {auth.method==='demo'?<>
   <p role="status">La démonstration est accessible sans mot de passe. Rechargez son accès pour continuer.</p>
   <Button onClick={()=>{void refresh().catch(cause=>setError(cause instanceof Error?cause.message:'Le serveur est inaccessible. Réessayez.'));}}>Réessayer</Button>
  </>:auth.method==='oidc'?<div className="form-stack" aria-busy={pending}>
   <p className="settings-note">Utilisez le compte professionnel autorisé par votre collectivité.</p>
   <Button type="button" disabled={pending||!auth.ssoAvailable} onClick={()=>void connectProfessional()}>{pending&&intent==='login'?'Connexion…':'Se connecter avec mon compte professionnel'}</Button>
   {auth.signupAvailable&&<Button type="button" variant="outline" disabled={pending} onClick={()=>void connectProfessional('signup')}>{pending&&intent==='signup'?'Ouverture de l’inscription…':'Créer mon compte professionnel'}</Button>}
   <p className="settings-note">Votre compte et la double authentification sont gérés par le service de connexion de votre collectivité.</p>
   {!auth.ssoAvailable&&<p role="status" className="settings-note">La connexion professionnelle n’est pas disponible actuellement. Contactez l’administrateur de votre espace.</p>}
  </div>:auth.method==='password'?<>
   <p className="settings-note">Utilisez la phrase de passe fournie pour accéder aux dossiers de cet espace.</p>
   <form className="form-stack" onSubmit={event=>void connect(event)} aria-busy={pending}>
    <label htmlFor="workspace-password">Phrase de passe
     <input id="workspace-password" name="password" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={event=>setPassword(event.target.value)} disabled={pending}/>
    </label>
    <Button type="submit" disabled={pending}>{pending?'Connexion…':'Se connecter'}</Button>
   </form>
  </>:<><p role="alert" className="form-error">La connexion à cet espace n’est pas disponible. Rechargez la page ou contactez l’administrateur.</p><Button onClick={()=>{void refresh().catch(()=>setError('Le serveur est inaccessible. Réessayez.'));}}>Réessayer</Button></>}
  {error&&<p className={error===PRO_AUTH_PENDING?'settings-note':'form-error'} role={error===PRO_AUTH_PENDING?'status':'alert'}>{error}</p>}
 </main>;
}
