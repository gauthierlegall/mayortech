import {useEffect,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,Check,CheckCircle2,ChevronRight,Eye,EyeOff,Folder,Inbox,Mail,Plus,RefreshCw,ShieldCheck} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {MailBackfill} from './MailBackfill';
import {beginMailOAuth,mailOAuthConnection,mailOAuthFeedback,importMailSelection,mailAccountPayload,mailProviderConfiguration,mailSetupAccess,mailSetupState,mailSetupStep,sameMailFolders,saveMailFolders,verifyMailAccount} from './mail-connection-model.mjs';
import './mail-connection.css';
import {workspaceMailIdentity} from './mail-navigation-state.mjs';

type Choice={id:string;name:string};
export type MailConnection={id:string;provider:string;label:string;mailbox:string;username:string;endpoint:string;status:string;revision:number;has_secret:boolean;mail_folders:Choice[];calendars:Choice[];selected_calendar_ids:string[];selected_folder_ids:string[];last_sync_at:string|null;last_mail_sync_at:string|null};
export type ConnectionHub={providers:{id:string;available:boolean;label:string;reason:string;status?:string;requires_server_configuration?:boolean;authorization?:string;mail_only?:boolean}[];connections:MailConnection[];can_manage:boolean;public_demo:boolean;test_organization?:boolean;external_connections_enabled:boolean};
const steps=['Messagerie','Compte','Accès','Terminer'];
const stateLabels:Record<string,string>={not_tested:'À vérifier',verified:'Dossiers à choisir',ready:'Prête à lire',read_only:'Lecture seule',disconnected:'Déconnectée',not_connected:'Non reliée'};
const message=(error:unknown)=>error instanceof Error?error.message:'La connexion ne peut pas continuer. Réessayez.';
const sample:MailConnection={id:'example-only',provider:'exchange',label:'Service travaux · exemple',mailbox:'travaux@example.invalid',username:'travaux@example.invalid',endpoint:'https://messagerie.example.invalid/EWS/Exchange.asmx',status:'verified',revision:0,has_secret:false,mail_folders:[{id:'example-inbox',name:'Boîte de réception'}],calendars:[],selected_calendar_ids:[],selected_folder_ids:[],last_sync_at:null,last_mail_sync_at:null};

function MailProviderHelp({hub,provider}:{hub:ConnectionHub;provider:string}){
 const [expanded,setExpanded]=useState(false);
 const access=mailSetupAccess(hub,provider),guide=access.blockedBy==='server_configuration'?mailProviderConfiguration(provider):null;
 const guideId=`mail-provider-configuration-${provider}`;
 return <div className="mail-connect-blocked">
  <p className="mail-connect-blocked-reason" role="status">{access.reason}</p>
  <p className="mail-connect-help">{access.nextAction}</p>
  <div className="mail-connect-actions">
   {access.privateAccessHref&&<Button asChild><a href={access.privateAccessHref}>Ouvrir la page de connexion<ArrowRight size={16}/></a></Button>}
   {guide&&<Button type="button" variant="outline" aria-expanded={expanded} aria-controls={guideId} onClick={()=>setExpanded(value=>!value)}>{guide.title}<ChevronRight size={16} className={expanded?'mail-guide-chevron expanded':'mail-guide-chevron'}/></Button>}
  </div>
  {guide&&expanded&&<section id={guideId} className="mail-provider-guide" aria-labelledby={`${guideId}-title`}>
   <h3 id={`${guideId}-title`}>{guide.title}</h3><p>{guide.introduction}</p>
   <ol>{guide.steps.map((instruction:string)=><li key={instruction}>{instruction}</li>)}</ol>
   <p className="mail-provider-callback-label">Exemple d’URL de retour à remplacer par l’adresse privée approuvée :</p>
   <code>{guide.callbackExample}</code><p>{guide.safety}</p>
  </section>}
 </div>;
}

export function MailConnections(){
 const {api,session}=useWorkspace();
 const identity=workspaceMailIdentity(session);
 return <MailConnectionsContent key={identity} api={api}/>;
}
function MailConnectionsContent({api}:{api:any}){
 const [hub,setHub]=useState<ConnectionHub|null>(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),[selection,setSelection]=useState('new'),[generation,setGeneration]=useState(0),[startAtAccount,setStartAtAccount]=useState(false);
 const [callback]=useState(()=>mailOAuthFeedback(typeof location==='undefined'?'':location.hash));
 const alive=useRef(true),initialLoad=useRef(false);
 useEffect(()=>{alive.current=true;let active=true;api.integrations().then((value:ConnectionHub)=>{if(active&&alive.current){if(!initialLoad.current){initialLoad.current=true;const returned=mailOAuthConnection(value,callback) as MailConnection|undefined;if(returned){setSelection(returned.id);setStartAtAccount(true);}}setHub(value);setError('');}}).catch((failure:unknown)=>{if(active&&alive.current)setError(message(failure));});return()=>{active=false;alive.current=false;};},[api,attempt,callback]);
 async function reload(){const value=await api.integrations() as ConnectionHub;if(!alive.current)throw Error('L’accès actif a changé.');setHub(value);return value;}
 function updated(record:MailConnection){setHub(previous=>previous?{...previous,connections:[...previous.connections.filter(item=>item.id!==record.id),record]}:previous);}
 if(!hub)return <section className="mail-connect-loading" aria-busy={!error}>{error?<><p role="alert">{error}</p><Button variant="outline" onClick={()=>setAttempt(value=>value+1)}>Réessayer</Button></>:<p role="status">Chargement des comptes de messagerie…</p>}</section>;
 const accounts=hub.connections.filter(item=>['exchange','google','microsoft365'].includes(item.provider));
 const selected=accounts.find(item=>item.id===selection);
  return <section className="mail-connections">{callback&&callback.kind!=='success'&&<p className={callback.kind==='error'?'form-error':'mail-connect-help'} role={callback.kind==='error'?'alert':'status'}>{callback.message}</p>}
  {accounts.length>0&&<section className="mail-account-list" aria-label="Comptes de messagerie enregistrés"><div className="section-heading"><h3>Vos messageries</h3><Button variant="outline" size="sm" onClick={()=>{setSelection('new');setStartAtAccount(false);setGeneration(value=>value+1);}}><Plus size={15}/>Ajouter un compte</Button></div>{accounts.map(account=><div className="mail-account-row" key={account.id}><Mail size={19}/><div><strong>{account.label}</strong><span>{account.mailbox}</span></div><span className="status-pill">{stateLabels[mailSetupState(account)]}</span><Button variant="ghost" size="sm" disabled={!mailSetupAccess(hub,account.provider).live||account.status==='disconnected'} onClick={()=>{setSelection(account.id);setStartAtAccount(false);setGeneration(value=>value+1);}}>Configurer<ChevronRight size={15}/></Button></div>)}</section>}
  <MailConnectionWizard key={`${selection}:${generation}`} hub={hub} initial={selected} startAtAccount={startAtAccount} onUpdated={updated} reload={reload}/>
 </section>;
}

function MailConnectionWizard({hub,initial,startAtAccount=false,onUpdated,reload}:{hub:ConnectionHub;initial?:MailConnection;startAtAccount?:boolean;onUpdated:(record:MailConnection)=>void;reload:()=>Promise<ConnectionHub>}){
 const {api,refresh}=useWorkspace();
 const [step,setStep]=useState(initial?(startAtAccount?1:mailSetupStep(initial)):0),[provider,setProvider]=useState(initial?.provider||'microsoft365'),[record,setRecord]=useState<MailConnection|null>(initial||null),[folders,setFolders]=useState<string[]>(initial?.selected_folder_ids||[]);
 const [values,setValues]=useState({mailbox:'',endpoint:'',username:'',label:'',password:''}),[showPassword,setShowPassword]=useState(false),[busy,setBusy]=useState(''),[error,setError]=useState(''),[conflict,setConflict]=useState(false),[uncertain,setUncertain]=useState(false),[canRestart,setCanRestart]=useState(false),[result,setResult]=useState<{moreAvailable:boolean;acknowledged:number|null}|null>(null),[exampleFinished,setExampleFinished]=useState(false);
 const access=mailSetupAccess(hub,provider),preview=provider==='exchange'&&!access.live&&(!record||record.id===sample.id);
 const alive=useRef(true),working=useRef(false),heading=useRef<HTMLHeadingElement>(null),recordRef=useRef(record);
 recordRef.current=record;
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 useEffect(()=>{if(step>0)heading.current?.focus();},[step]);
 function guard(){if(!alive.current)throw Error('L’accès actif a changé. Rouvrez les connexions.');}
 function changed(next:MailConnection){guard();recordRef.current=next;setRecord(next);onUpdated(next);}
 async function perform(label:string,operation:()=>Promise<void>){
  if(working.current)return;working.current=true;setBusy(label);setError('');setConflict(false);
  try{await operation();}catch(failure){if(alive.current){setError(message(failure));setConflict((failure as any)?.detail?.code==='stale_revision');if(label==='verify'&&!recordRef.current&&(!(failure as any)?.status||(failure as any)?.status>=500)){setUncertain(true);setCanRestart(false);setValues(previous=>({...previous,password:''}));setError('La réponse du serveur n’a pas été reçue. Vérifiez les comptes enregistrés avant une nouvelle tentative ; le compte a peut-être été créé.');}}}
  finally{working.current=false;if(alive.current)setBusy('');}
 }
 function chooseProvider(next:string){
  if(working.current||record&&record.id!==sample.id)return;
  setProvider(next);setRecord(null);setFolders([]);setValues({mailbox:'',endpoint:'',username:'',label:'',password:''});setError('');setResult(null);
 }
 async function authorize(){
  if(working.current)return;working.current=true;setBusy('authorization');setError('');
  try{await beginMailOAuth({api,hub,provider,assertCurrent:guard,redirect:(url:string)=>window.location.assign(url)});}
  catch(failure){if(alive.current){setError(message(failure));setBusy('');}working.current=false;}
 }
 const firstStep=record&&record.id!==sample.id?1:0;
 function go(next:number){setError('');setConflict(false);if(preview&&next<3)setExampleFinished(false);setStep(Math.max(firstStep,next));}
 async function refreshAccount(){await perform('refresh',async()=>{const latest=await reload();guard();const current=latest.connections.find(item=>item.id===recordRef.current?.id);if(current){changed(current);setFolders(previous=>previous.filter(id=>current.mail_folders.some(folder=>folder.id===id)));setUncertain(false);setError('État actualisé. Vérifiez vos choix avant de les enregistrer.');}else{const matches=latest.connections.some(item=>item.provider==='exchange'&&item.mailbox.toLocaleLowerCase('fr')===values.mailbox.trim().toLocaleLowerCase('fr'));setCanRestart(!matches);setError(matches?'Un compte correspondant est enregistré. Utilisez Configurer dans la liste des comptes pour reprendre, sans créer de doublon.':'Aucun compte correspondant n’est visible. Vous pouvez actualiser à nouveau ou recommencer la saisie. Aucune création n’a été rejouée.');}});}
 async function verify(){
  if(preview){const kept=folders.filter(id=>sample.mail_folders.some(folder=>folder.id===id));setRecord({...sample,selected_folder_ids:kept});setFolders(kept);go(2);return;}
  if(!recordRef.current){try{mailAccountPayload(values);}catch(failure){setError(message(failure));return;}}
  const resuming=Boolean(recordRef.current);
  await perform('verify',async()=>{const verified=await verifyMailAccount({api,hub,values,connection:recordRef.current,assertCurrent:guard,onCreated:(created:MailConnection)=>{changed(created);setValues(previous=>({...previous,password:''}));}});changed(verified);setValues(previous=>({...previous,password:''}));setFolders(previous=>resuming?previous.filter(id=>verified.mail_folders.some((folder:Choice)=>folder.id===id)):verified.selected_folder_ids);setStep(2);});
 }
 async function saveScope(){
  if(!record)return;
  setResult(null);
  if(preview){setRecord({...record,selected_folder_ids:[...folders]});go(3);return;}
  await perform('selection',async()=>{const selected=await saveMailFolders({api,hub,connection:record,folderIds:folders,assertCurrent:guard});changed(selected);setStep(3);});
 }
 async function collect(){
  if(!record)return;
  if(preview){setExampleFinished(true);return;}
  await perform('import',async()=>{const imported=await importMailSelection({api,hub,connection:record,folderIds:folders,assertCurrent:guard});changed(imported.connection);setResult(imported);try{guard();await refresh();guard();}catch{guard();setError('La lecture est enregistrée, mais l’espace n’a pas pu être actualisé. Rechargez la page pour retrouver les nouveaux courriels.');}});
 }
 const unavailable=provider==='exchange'?Boolean(record&&record.id!==sample.id&&!access.live):!access.live;
 const cloud=provider==='google'||provider==='microsoft365';
 const current=record||(preview?sample:null);
 const selectedFolders=current?.mail_folders.filter(folder=>folders.includes(folder.id))||[];
 const imported=Boolean(record?.last_mail_sync_at);
 const cloudName=provider==='google'?'Google':'Outlook';
 const titles=['Quelle messagerie utilisez-vous ?',preview?'Préparer le compte Exchange':record?'Choisir les dossiers du compte':cloud?`Connecter votre compte ${cloudName}`:'Relier votre compte Exchange','Quels dossiers souhaitez-vous lire ?',preview?'Votre parcours en un coup d’œil':imported?'Votre messagerie est reliée':'Tout est prêt pour une première lecture'];
 return <div className="mail-connect-layout">
  <div className="mail-connect-main">
   <ol className="mail-connect-steps" aria-label="Étapes pour relier la messagerie">{steps.map((label,index)=><li key={label} className={step===index?'active':step>index?'complete':''}><button type="button" disabled={Boolean(busy)||index>step||index<firstStep} aria-current={step===index?'step':undefined} onClick={()=>go(index)}><span>{step>index?<Check size={14}/>:index+1}</span>{label}</button></li>)}</ol>
   {preview&&<div className="mail-connect-example"><ShieldCheck size={18}/><p><strong>Aperçu du raccordement Exchange</strong> {hub.public_demo?'La démonstration présente les étapes sans relier de compte réel ni demander d’identifiants. La connexion Exchange doit être activée par votre administrateur dans un espace protégé.':access.reason+' Cet aperçu ne relie aucun compte et ne demande aucun identifiant.'}{access.privateAccessHref&&<a href={access.privateAccessHref}>Ouvrir la page de connexion<ArrowRight size={14}/></a>}</p></div>}
   {step>0&&!preview&&!access.live&&<MailProviderHelp key={provider} hub={hub} provider={provider}/>}
   <div className="mail-connect-body" aria-busy={Boolean(busy)}>
    <h2 ref={heading} tabIndex={-1}>{titles[step]}</h2>
    {step===0&&<>
     <p>Reliez votre messagerie professionnelle, puis choisissez les dossiers dont les courriels et les pièces rejoindront l’espace partagé du service.</p>
     <fieldset className="mail-provider-choices" disabled={Boolean(busy)||Boolean(record&&record.id!==sample.id)}><legend className="sr-only">Votre fournisseur de messagerie</legend>{[{id:'microsoft365',name:'Outlook / Microsoft 365',description:'Votre adresse professionnelle Microsoft'},{id:'exchange',name:'Exchange local ou hébergé',description:'Le serveur de messagerie de votre collectivité'},{id:'google',name:'Gmail / Google Workspace',description:'Compte Google professionnel ou Gmail'}].map(item=>{const providerAccess=mailSetupAccess(hub,item.id);return <label key={item.id} className={provider===item.id?'selected':''}><input type="radio" name="mail-provider" value={item.id} checked={provider===item.id} onChange={()=>chooseProvider(item.id)}/><Mail size={22} aria-hidden="true"/><span className="mail-provider-label"><strong>{item.name}</strong><small>{item.description}</small></span>{item.id==='exchange'||providerAccess.live?<ChevronRight size={17} aria-hidden="true"/>:<span className="mail-provider-unavailable">{providerAccess.blockedBy==='public_demo'?'Accès privé requis':providerAccess.blockedBy==='test_organization'?'Données fictives uniquement':providerAccess.blockedBy==='administrator'?'Administrateur requis':'Configuration nécessaire'}</span>}</label>;})}</fieldset>
     {unavailable&&cloud&&<MailProviderHelp key={provider} hub={hub} provider={provider}/>}
     {!unavailable&&<div className="mail-connect-actions"><Button disabled={Boolean(busy)} onClick={()=>{if(cloud)void authorize();else go(1);}}>{busy==='authorization'?'Ouverture de la connexion…':cloud?`Connecter ${cloudName}`:preview?'Voir le parcours de connexion':'Continuer avec Exchange'}<ArrowRight size={16}/></Button></div>}
     {cloud&&<p className="mail-connect-consent">{provider==='microsoft365'?'Connecter Outlook ouvre la page officielle Microsoft. Identifiez-vous avec votre adresse professionnelle et examinez les autorisations demandées.':'La connexion ouvre la page officielle Google pour choisir votre compte et examiner les autorisations demandées.'} Au retour, vous choisirez les dossiers à importer. Aucun courriel n’est importé avant votre lancement explicite.</p>}
    </>}
    {step===1&&<>
     {preview?<><p>Dans votre espace protégé, vous renseignez votre adresse professionnelle et les informations de connexion fournies par votre service informatique.</p><dl className="mail-connect-summary"><div><dt>Adresse d’exemple</dt><dd>{sample.mailbox}</dd></div><div><dt>Messagerie</dt><dd>Exchange · exemple sans connexion</dd></div></dl><p className="mail-connect-help">Le bouton suivant montre le choix des dossiers. Aucun serveur n’est contacté.</p><div className="mail-connect-actions"><Button onClick={()=>void verify()}>Voir le choix des dossiers<ArrowRight size={16}/></Button></div></>:
      record?<><p>Ce compte est enregistré. Choisir les dossiers vérifie son accès et recherche les dossiers disponibles, sans importer de courriels.</p><dl className="mail-connect-summary"><div><dt>Adresse</dt><dd>{record.mailbox}</dd></div><div><dt>Messagerie</dt><dd>{cloud?(provider==='google'?'Google Workspace / Gmail':'Outlook / Microsoft 365'):record.endpoint}</dd></div><div><dt>État</dt><dd>{stateLabels[mailSetupState(record)]}</dd></div></dl><div className="mail-connect-actions"><Button disabled={Boolean(busy)||!access.live} onClick={()=>void verify()}><Folder size={16}/>{busy==='verify'?'Recherche des dossiers…':'Choisir les dossiers'}</Button></div><p className="mail-connect-help">Les messages et les pièces des dossiers importés seront partagés avec les personnes autorisées dans cet espace. Pour relier une autre adresse, utilisez Ajouter un compte.</p></>:
      cloud?<><p>Connectez ce compte sur la page officielle {provider==='google'?'Google':'Microsoft'}, avec votre adresse professionnelle. Vous pourrez ensuite choisir les dossiers à importer et lancer leur lecture.</p>{access.live&&<div className="mail-connect-actions"><Button disabled={Boolean(busy)} onClick={()=>void authorize()}>Connecter {cloudName}</Button></div>}</>:
      <form className="mail-connect-form" onSubmit={event=>{event.preventDefault();void verify();}}>
       <p>Le compte reste hébergé chez votre fournisseur. L’espace lit uniquement les dossiers que vous autoriserez.</p>
       <label htmlFor="mail-setup-address">Adresse professionnelle<input id="mail-setup-address" type="email" autoComplete="username" value={values.mailbox} onChange={event=>setValues(previous=>({...previous,mailbox:event.target.value}))} required maxLength={320} placeholder="prenom.nom@collectivite.fr" disabled={Boolean(busy)||uncertain}/></label>
       <label htmlFor="mail-setup-password">Mot de passe<div className="mail-password-control"><input id="mail-setup-password" aria-label="Mot de passe" type={showPassword?'text':'password'} autoComplete="current-password" value={values.password} onChange={event=>setValues(previous=>({...previous,password:event.target.value}))} required maxLength={4000} disabled={Boolean(busy)||uncertain} aria-describedby="mail-password-help"/><Button type="button" variant="ghost" size="icon" aria-label={showPassword?'Masquer le mot de passe':'Afficher le mot de passe'} onClick={()=>setShowPassword(value=>!value)}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</Button></div><small id="mail-password-help">Chiffré sur le serveur de l’espace. Il n’est pas enregistré par Travaux sur cet appareil.</small></label>
       <label htmlFor="mail-setup-server">Adresse du serveur Exchange<input id="mail-setup-server" aria-label="Adresse du serveur Exchange" type="url" value={values.endpoint} onChange={event=>setValues(previous=>({...previous,endpoint:event.target.value}))} required maxLength={2000} placeholder="https://messagerie.collectivite.fr/EWS/Exchange.asmx" disabled={Boolean(busy)||uncertain} aria-describedby="mail-server-help"/><small id="mail-server-help">Demandez l’adresse EWS à votre service informatique si vous ne la connaissez pas.</small></label>
       <details className="mail-connect-advanced"><summary>Mon identifiant est différent de mon adresse mail</summary><label htmlFor="mail-setup-username">Identifiant de connexion<input id="mail-setup-username" value={values.username} onChange={event=>setValues(previous=>({...previous,username:event.target.value}))} autoComplete="off" maxLength={320} placeholder="DOMAINE\identifiant" disabled={Boolean(busy)||uncertain}/><small>À laisser vide si votre adresse mail sert aussi d’identifiant.</small></label><label htmlFor="mail-setup-label">Nom affiché du compte<input id="mail-setup-label" value={values.label} onChange={event=>setValues(previous=>({...previous,label:event.target.value}))} maxLength={200} placeholder="Service travaux" disabled={Boolean(busy)||uncertain}/></label></details>
       <Button type="submit" disabled={Boolean(busy)||uncertain}>{busy==='verify'?'Enregistrement et vérification…':'Vérifier la connexion'}<ArrowRight size={16}/></Button>
      </form>}
    </>}
    {step===2&&current&&<>
     <p>{preview?'Exemple de dossier disponible pour cette messagerie.':'Connexion vérifiée. Voici les dossiers que le serveur rend accessibles à ce compte.'} Choisissez ceux qui pourront rejoindre l’espace partagé du service.</p>
     <div className="mail-connected-address"><CheckCircle2 size={17}/><span>{current.mailbox}</span>{preview&&<small>Adresse d’exemple</small>}</div>
     <fieldset className="mail-folder-choices" disabled={Boolean(busy)||(!preview&&!access.live)}><legend>Dossiers à lire</legend>{current.mail_folders.map(folder=><label key={folder.id}><input type="checkbox" checked={folders.includes(folder.id)} onChange={()=>setFolders(previous=>previous.includes(folder.id)?previous.filter(id=>id!==folder.id):[...previous,folder.id])}/><Folder size={20}/><span>{folder.name}</span></label>)}</fieldset>
     {!current.mail_folders.length&&<p className="mail-connect-help">Aucun dossier de messagerie n’a été trouvé. Vérifiez les droits du compte avec votre service informatique avant de continuer.</p>}
     <p className="mail-connect-help">Les messages de ces dossiers seront accessibles aux personnes autorisées dans cet espace. Le classement et les suppressions dans Travaux ne modifient pas votre boîte d’origine.</p>
     <div className="mail-connect-actions"><Button disabled={Boolean(busy)||!folders.length||(!preview&&!access.live)} onClick={()=>void saveScope()}>{busy==='selection'?'Enregistrement des accès…':'Enregistrer ces dossiers'}<ArrowRight size={16}/></Button></div>
    </>}
    {step===3&&current&&<>
     <p>{preview?'Cet aperçu montre le choix des dossiers. Aucun compte réel n’est relié et aucun courriel n’est importé.':imported?'Un passage de lecture est enregistré pour ce compte. Lancez une nouvelle lecture pour actualiser les dossiers choisis.':'Les accès sont enregistrés. Aucun courriel n’a encore été lu par ce compte ; vous pouvez lancer un premier passage.'}</p>
     <dl className="mail-connect-summary"><div><dt>Compte</dt><dd>{current.mailbox}{preview&&' · exemple non connecté'}</dd></div><div><dt>Dossiers autorisés</dt><dd>{selectedFolders.map(folder=>folder.name).join(', ')||'Aucun dossier'}</dd></div><div><dt>Accès</dt><dd>Lecture seule · aucun envoi de mail</dd></div><div><dt>Lecture des nouveaux messages</dt><dd>À votre demande, depuis Connexions</dd></div></dl>
     {result&&<div className="mail-import-result" role="status"><CheckCircle2 size={19}/><div><strong>{result.moreAvailable?'Premier passage effectué':'Lecture effectuée'}</strong><p>{result.moreAvailable?'D’autres éléments restent disponibles. Vous pouvez poursuivre la lecture.':'Le serveur a terminé ce passage. Les courriels conservés sont consultables dans Messagerie.'}</p>{result.acknowledged!==null&&<small>{result.acknowledged} changements acquittés pendant ce passage. Ce compteur n’est pas un nombre de nouveaux courriels.</small>}</div></div>}
     {exampleFinished&&<div className="mail-import-result" role="status"><CheckCircle2 size={19}/><p><strong>Exemple terminé.</strong> Aucun compte n’a été relié et aucun courriel n’a été importé.</p></div>}
     <div className="mail-connect-actions">{preview?!exampleFinished&&<Button onClick={()=>void collect()}>Terminer l’exemple<Check size={16}/></Button>:<Button disabled={Boolean(busy)||!access.live||!sameMailFolders(folders,current.selected_folder_ids)} onClick={()=>void collect()}><RefreshCw size={16}/>{busy==='import'?'Lecture des courriels…':result?.moreAvailable?'Continuer la lecture':imported?'Vérifier les nouveaux courriels':'Lancer la première lecture'}</Button>}<Button variant="outline" asChild><a href="#/messagerie">{preview?'Voir la messagerie de démonstration':'Ouvrir la messagerie'}<ArrowRight size={16}/></a></Button></div>
     {!preview&&record?.provider==='exchange'&&<details className="mail-connect-history"><summary>Reprendre aussi des courriels plus anciens</summary><MailBackfill connection={record} canManage={hub.can_manage}/></details>}
    </>}
    {error&&<div className="mail-connect-error" role="alert"><p>{error}</p>{(conflict||uncertain)&&<Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>void refreshAccount()}>Actualiser le compte</Button>}{uncertain&&canRestart&&<Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>{setUncertain(false);setCanRestart(false);setError('');setValues(previous=>({...previous,password:''}));}}>Recommencer la saisie</Button>}</div>}
    {step>0&&<footer className="mail-connect-back"><Button variant="ghost" disabled={Boolean(busy)||step<=firstStep} onClick={()=>go(step-1)}><ArrowLeft size={15}/>Retour</Button><a href="#/messagerie">Configurer plus tard</a></footer>}
   </div>
  </div>
  <aside className="mail-connect-aside"><Inbox size={25}/><h3>Vos mails, dans le bon chantier</h3><p>Les courriels et leurs pièces rejoignent la Messagerie. Vous retrouvez leur source depuis les dossiers de travaux.</p><ul><li>Vous choisissez les dossiers accessibles.</li><li>Votre boîte d’origine reste inchangée.</li><li>Les annonces reçues restent à vérifier avant de modifier un fait du chantier.</li></ul><a href="#/agenda">Configurer les agendas séparément<ArrowRight size={14}/></a></aside>
 </div>;
}
