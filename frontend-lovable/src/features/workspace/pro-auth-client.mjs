/** Browser-side presentation and redirect boundary; identity is verified on the server. */
export const PRO_AUTH_ERROR='La connexion professionnelle n’a pas pu aboutir. Réessayez ou contactez l’administrateur de votre espace.';
export const PRO_AUTH_PENDING='Votre demande d’accès attend l’autorisation de l’administrateur.';
export const PRO_AUTH_REAUTHENTICATE='Reconnectez-vous pour terminer. Saisissez votre mot de passe, puis le code à 6 chiffres affiché dans votre application d’authentification.';
const DEFAULT_LABEL='Connexion de la collectivité';

export function authPresentation(session){
 const auth=session?.auth;
 const method=session?.public_demo===true?'demo':auth===undefined?'password':
  ['oidc','password','demo'].includes(auth?.method)?auth.method:'unavailable';
 const label=typeof auth?.label==='string'&&auth.label.trim()&&auth.label.length<=160?auth.label.trim():DEFAULT_LABEL;
 return {method,label,ssoAvailable:method==='oidc'&&auth?.sso_available===true,signupAvailable:method==='oidc'&&auth?.sso_available===true&&auth?.signup_available===true};
}

export function professionalAuthorizationUrl(response){
 try{
  const value=response?.authorization_url;
  if(typeof value!=='string'||value.length>16384||!value.startsWith('https://')||/[\u0000-\u0020\u007f\\#]/.test(value)||value.slice(8).split('/')[0].includes('@'))throw Error();
  const url=new URL(value);
  if(url.protocol!=='https:'||!url.hostname||url.username||url.password||url.hash)throw Error();
  return value;
 }catch{throw Error(PRO_AUTH_ERROR);}
}

export async function beginProfessionalLogin(api,redirect,intent='login',loginHint=''){
 try{
  if(typeof api?.authStart!=='function'||!['login','signup','recovery'].includes(intent))throw Error();
  if(typeof loginHint!=='string'||loginHint.length>254||/[\u0000-\u0020\u007f]/.test(loginHint)||(loginHint&&!/^[^@]+@[^@.]+(?:\.[^@.]+)+$/.test(loginHint)))throw Error();
  const value=await api.authStart({intent,...(loginHint?{login_hint:loginHint}:{})});
  redirect(professionalAuthorizationUrl(value));
 }catch{throw Error(PRO_AUTH_ERROR);}
}

export function authFailureMessage(hash){
 if(typeof hash!=='string')return '';
 const [route,query]=hash.replace(/^#/,'').split('?');
 if(route!=='/connexion')return '';
 const statuses=new URLSearchParams(query||'').getAll('auth');
 return statuses.includes('failed')?PRO_AUTH_ERROR:statuses.includes('pending')?PRO_AUTH_PENDING:'';
}
