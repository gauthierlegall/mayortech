/** Entry routes and capabilities are explicit; public demo sessions never become private access. */
export function portalMode(pathname){
 return pathname==='/inscription.html'?'signup':pathname==='/mot-de-passe-oublie.html'?'recovery':'login';
}
export function portalCapabilities(value){
 const oidc=value?.method==='oidc';
 return {login:oidc&&value.login_available===true,signup:oidc&&value.login_available===true&&value.signup_available===true,recovery:oidc&&value.login_available===true&&value.recovery_available===true,demo:value?.method==='demo'&&value.demo_available===true,pilot:value?.method==='password'};
}
export function privateEntry(value,mode='login'){
 try{
  const raw=value?.private_access_url;
  if(typeof raw!=='string'||raw.length>2048||/[\u0000-\u0020\u007f\\#]/.test(raw)||raw.slice(8).split('/')[0].includes('@'))return null;
  const url=new URL(raw);
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/connexion.html'||!url.hostname||url.port)return null;
  return url.origin+(mode==='signup'?'/inscription.html':mode==='recovery'?'/mot-de-passe-oublie.html':'/connexion.html');
 }catch{return null;}
}
export function portalDestination(session){
 return session?.authenticated===true&&session?.auth_required===true&&session?.public_demo!==true?'/espace.html#/':null;
}
export function legacyDemoDestination(pathname,hash){
 // Only old local hash routes are carried forward. No query-supplied return URL.
 return pathname==='/'&&typeof hash==='string'&&/^#\/(?!\/)[a-zA-Z0-9/?=&%_.-]*$/.test(hash)&&!/^#\/connexion(?:\?|$)/.test(hash)?'/demo.html'+hash:null;
}
export function validLoginEmail(value){
 return typeof value==='string'&&value.length<=254&&!/[\u0000-\u0020\u007f]/.test(value)&&/^[^@]+@[^@.]+(?:\.[^@.]+)+$/.test(value);
}
