import {professionalAuthorizationUrl} from './pro-auth-client.mjs';
export const MAIL_OAUTH_ERROR='Le raccordement de la messagerie n’a pas pu démarrer. Réessayez.';
const MAIL_PROVIDERS=['exchange','google','microsoft365'];
export function mailSetupAccess(hub,provider='exchange'){
 const selected=hub?.providers?.find(item=>item.id===provider);
 if(hub?.test_organization===true)return {
  live:false,
  blockedBy:'test_organization',
  reason:'Mairie test utilise des courriels fictifs. Les comptes externes y sont désactivés.',
  nextAction:'Pour relier une boîte réelle, ouvrez l’espace privé de votre collectivité.',
  privateAccessHref:null,
 };
 const live=MAIL_PROVIDERS.includes(provider)&&hub?.public_demo!==true&&hub?.can_manage===true&&hub?.external_connections_enabled===true&&selected?.available===true;
 const blockedBy=live?null:hub?.public_demo===true?'public_demo':hub?.can_manage!==true?'administrator':'server_configuration';
 const reason=blockedBy==='public_demo'?'Cette démonstration publique ne permet pas de relier un compte réel.':blockedBy==='administrator'?'Un administrateur doit autoriser la connexion de messagerie.':selected?.reason||'Le serveur de messagerie doit être autorisé dans cet espace.';
 const nextAction=blockedBy==='public_demo'?'Votre administrateur doit activer un espace privé et y configurer la messagerie. La page de connexion indique les possibilités d’accès.':blockedBy==='administrator'?'Demandez à l’administrateur de cet espace d’autoriser le raccordement et de vérifier vos droits.':blockedBy==='server_configuration'?'Demandez à l’administrateur de terminer la configuration du fournisseur sur le serveur, puis revenez sur cette page.':'';
 return {live:Boolean(live),reason,blockedBy,nextAction,privateAccessHref:blockedBy==='public_demo'?'/connexion.html':null};
}
export function mailProviderConfiguration(provider){
 if(!['microsoft365','google'].includes(provider))return null;
 const microsoft=provider==='microsoft365',callbackPath=`/api/v1/integrations/oauth/${provider}/callback`;
 return {
  title:microsoft?'Configuration Microsoft 365':'Configuration Google Workspace',
  introduction:'Ces consignes s’adressent à l’administrateur de l’espace privé et au service informatique. Cette aide ne configure aucun compte.',
  callbackPath,callbackExample:`https://espace-prive.example${callbackPath}`,
  steps:microsoft?[
   'Créer une application Web confidentielle dans Microsoft Entra, limitée au tenant de la collectivité.',
   'Renseigner le tenant (GUID), l’identifiant client et le secret côté serveur, depuis le gestionnaire de secrets de l’exploitant. Les jetons du compte sont conservés dans le coffre chiffré du serveur.',
   'Déclarer l’URL de retour exacte de l’espace privé HTTPS. L’exemple ci-dessous doit être remplacé par son adresse approuvée.',
   'Configurer avec la DSI les permissions déléguées User.Read, Mail.Read et offline_access. Le titulaire peut autoriser l’accès si la politique Microsoft Entra le permet. Sinon, un administrateur Microsoft doit approuver la demande.',
   'Autoriser les sorties réseau nécessaires vers login.microsoftonline.com et graph.microsoft.com, puis connecter une boîte de recette et choisir les dossiers à lire.',
  ]:[
   'Activer Gmail API et créer un client OAuth Web dans le projet Google approuvé par la collectivité.',
   'Renseigner l’identifiant client et le secret côté serveur, depuis le gestionnaire de secrets de l’exploitant. Les jetons du compte sont conservés dans le coffre chiffré du serveur.',
   'Déclarer l’URL de retour exacte de l’espace privé HTTPS. L’exemple ci-dessous doit être remplacé par son adresse approuvée.',
   'Faire valider par la DSI le consentement, le scope gmail.readonly, ses exigences de vérification et les domaines de boîte autorisés.',
   'Autoriser les sorties réseau nécessaires vers accounts.google.com, oauth2.googleapis.com et gmail.googleapis.com, puis connecter une boîte de recette et choisir les dossiers à lire.',
  ],
  safety:'Ne saisissez aucun secret dans la démonstration publique. Cette configuration autorise une lecture de courriels ; elle n’active pas l’envoi de messages.',
 };
}
function requireLive(hub,provider='exchange'){const access=mailSetupAccess(hub,provider);if(!access.live)throw Error(access.reason);}
const guardDefault=()=>{};
export function mailAccountPayload(values){
 const mailbox=String(values.mailbox||'').trim(),endpoint=String(values.endpoint||'').trim(),password=String(values.password||'');
 if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mailbox)||mailbox.length>320)throw Error('Renseignez une adresse de messagerie professionnelle valide.');
 if(!endpoint)throw Error('Renseignez l’adresse du serveur fournie par votre service informatique.');
 let url;try{url=new URL(endpoint);}catch{throw Error('Renseignez une adresse de serveur HTTPS valide.');}
 if(url.protocol!=='https:')throw Error('L’adresse du serveur doit utiliser HTTPS.');
 if(url.username||url.password||url.hash)throw Error('L’adresse du serveur ne doit contenir aucun identifiant ni fragment.');
 if(!password||password.length>4000)throw Error('Renseignez le mot de passe du compte.');
 const username=String(values.username||'').trim()||mailbox;
 const label=String(values.label||'').trim()||mailbox;
 if(username.length>320||label.length>200||endpoint.length>2000)throw Error('Les informations du compte dépassent la longueur autorisée.');
 return {provider:'exchange',mailbox,endpoint,username,label,password};
}
export async function verifyMailAccount({api,hub,values,connection,onCreated=(_record)=>{},assertCurrent=guardDefault}){
 requireLive(hub,connection?.provider||'exchange');assertCurrent();let record=connection;
 if(!record){record=await api.createConnection(mailAccountPayload(values));assertCurrent();onCreated(record);}
 if(!MAIL_PROVIDERS.includes(record.provider)||record.status==='disconnected')throw Error('Ce compte ne peut pas être vérifié. Ajoutez un autre compte.');
 const verified=await api.probeConnection(record.id,{expected_revision:record.revision});assertCurrent();return verified;
}
export async function saveMailFolders({api,hub,connection,folderIds,assertCurrent=guardDefault}){
 requireLive(hub,connection.provider);assertCurrent();
 const selected=[...new Set(folderIds)];
 if(!selected.length||selected.some(id=>!connection.mail_folders.some(folder=>folder.id===id)))throw Error('Choisissez au moins un dossier accessible à ce compte.');
 if(!['verified','synced'].includes(connection.status))throw Error('Vérifiez le compte avant de choisir ses dossiers.');
 const saved=await api.selectConnection(connection.id,{folder_ids:selected,calendar_ids:[...connection.selected_calendar_ids],expected_revision:connection.revision});assertCurrent();return saved;
}
export function sameMailFolders(left=[],right=[]){return left.length===right.length&&left.every(id=>right.includes(id));}
export async function importMailSelection({api,hub,connection,folderIds,assertCurrent=guardDefault}){
 requireLive(hub,connection.provider);assertCurrent();
 if(!['verified','synced'].includes(connection.status)||!connection.selected_folder_ids.length||!sameMailFolders(folderIds,connection.selected_folder_ids))throw Error('Enregistrez la sélection de dossiers avant de lancer la lecture.');
 const result=await api.syncConnectionMail(connection.id,{expected_revision:connection.revision});assertCurrent();
 return {connection:result.connection,moreAvailable:result.more_available===true,acknowledged:Number.isSafeInteger(result.accepted)&&result.accepted>=0?result.accepted:null};
}
export function mailSetupState(connection){
 if(!connection)return 'not_connected';
 if(connection.status==='disconnected')return 'disconnected';
 if(!['verified','synced'].includes(connection.status))return 'not_tested';
 if(!connection.selected_folder_ids?.length)return 'verified';
 return connection.last_mail_sync_at?'read_only':'ready';
}
export function mailSetupStep(connection){const state=mailSetupState(connection);return ['ready','read_only'].includes(state)?3:state==='verified'?2:1;}

export async function beginMailOAuth({api,hub,provider,label='',redirect,assertCurrent=guardDefault}){
 requireLive(hub,provider);assertCurrent();
 if(!['google','microsoft365'].includes(provider))throw Error(MAIL_OAUTH_ERROR);
 const cleaned=typeof label==='string'?label.trim():'';
 if(cleaned.length>200)throw Error('Le nom du compte est trop long.');
 let response;
 try{response=await api.startMailOAuth(provider,cleaned?{label:cleaned}:{});}catch{throw Error(MAIL_OAUTH_ERROR);}
 assertCurrent();
 try{redirect(professionalAuthorizationUrl(response));}catch{throw Error(MAIL_OAUTH_ERROR);}
}

export function mailOAuthFeedback(hash){
 if(typeof hash!=='string')return null;
 const [route,query]=hash.replace(/^#/,'').split('?');if(route!=='/connexions')return null;
 const parameters=new URLSearchParams(query||'');
 const outcomes=parameters.getAll('oauth');
 if(outcomes.length!==1)return null;
 if(outcomes[0]==='failed')return {kind:'error',message:'La connexion a échoué. Reprenez avec votre compte professionnel ou contactez l’administrateur si Microsoft demande son approbation.'};
 if(outcomes[0]==='cancelled')return {kind:'cancelled',message:'Le raccordement a été annulé. Vous pouvez reprendre la connexion.'};
 if(outcomes[0]!=='connected')return null;
 const ids=parameters.getAll('connection');
 const valid=ids.length===1&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(ids[0]);
 return {
  kind:'success',
  message:'Retrouvez votre compte dans la liste pour vérifier les dossiers à lire.',
  ...(valid?{connectionId:ids[0]}:{}),
 };
}

export function mailOAuthConnection(hub,feedback){
 if(feedback?.kind!=='success'||!feedback.connectionId||!Array.isArray(hub?.connections))return undefined;
 return hub.connections.find(record=>record.id===feedback.connectionId
  &&['microsoft365','google'].includes(record.provider)
  &&record.status!=='disconnected'&&record.has_secret===true
  &&mailSetupAccess(hub,record.provider).live);
}
