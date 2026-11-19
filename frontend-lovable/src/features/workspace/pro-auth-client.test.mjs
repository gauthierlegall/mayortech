import assert from 'node:assert/strict';
import test from 'node:test';
import {authFailureMessage,authPresentation,beginProfessionalLogin,professionalAuthorizationUrl,PRO_AUTH_ERROR} from './pro-auth-client.mjs';

test('OIDC is explicit and never offers the historical password method when SSO is unavailable',()=>{
 for(const sso_available of [true,false,undefined]){
  const view=authPresentation({authenticated:false,auth:{method:'oidc',sso_available,label:'Connexion de la collectivité'}});
  assert.equal(view.method,'oidc');
  assert.equal(view.ssoAvailable,sso_available===true);
  assert.equal(view.label,'Connexion de la collectivité');
 }
});

test('legacy password and public demonstration remain distinct and unknown explicit methods fail closed',()=>{
 assert.equal(authPresentation({authenticated:false}).method,'password');
 assert.equal(authPresentation({public_demo:true}).method,'demo');
 assert.equal(authPresentation({auth:{method:'demo'}}).method,'demo');
 assert.equal(authPresentation({auth:{method:'password'}}).method,'password');
 assert.equal(authPresentation({auth:{method:'unexpected'}}).method,'unavailable');
 assert.equal(authPresentation({auth:{method:'oidc',label:{html:'untrusted'}}}).label,'Connexion de la collectivité');
});

test('authorization URL preserves the server-provided state and PKCE query without storing or decoding them',()=>{
 const url='https://identity.example.invalid/authorize?state=synthetic-state&code_challenge=synthetic-pkce&redirect_uri=https%3A%2F%2Ftravaux.example.invalid%2Fcallback';
 assert.equal(professionalAuthorizationUrl({authorization_url:url}),url);
});

test('malformed or unsafe authorization targets are refused rather than navigated',()=>{
 for(const value of [undefined,null,{},42,'','/authorize','//identity.example.invalid/authorize','http://identity.example.invalid/authorize','javascript:alert(1)','data:text/plain,auth','https://user:synthetic-secret@identity.example.invalid/authorize','https://identity.example.invalid/authorize#token=synthetic-secret','https://identity.example.invalid/authorize#','https://@identity.example.invalid/authorize',' https://identity.example.invalid/authorize','https://identity.example.invalid/authorize\n','https:\\identity.example.invalid/authorize','https://identity.example.invalid/authorize?state=\u0000','https://'+'a'.repeat(17000)]){
  assert.throws(()=>professionalAuthorizationUrl({authorization_url:value}),error=>error.message===PRO_AUTH_ERROR);
 }
 assert.throws(()=>professionalAuthorizationUrl(null),error=>error.message===PRO_AUTH_ERROR);
});

test('professional login calls only the same-origin API start boundary and passes a validated URL to top-level navigation',async()=>{
 const calls=[],target='https://identity.example.invalid/authorize?state=synthetic';
 await beginProfessionalLogin({authStart:async(...args)=>{calls.push(['start',args]);return{authorization_url:target};},login:()=>assert.fail('password login must not be called')},url=>calls.push(['redirect',url]));
 assert.deepEqual(calls,[['start',[{intent:'login'}]],['redirect',target]]);
});

test('API or navigation failures never expose provider responses, callback codes or secrets',async()=>{
 let redirected=false;
 for(const api of [{},{authStart:async()=>{throw Error('code=synthetic-secret&error_description=private');}},{authStart:async()=>({authorization_url:'http://identity.example.invalid/'})}]){
  await assert.rejects(beginProfessionalLogin(api,()=>{redirected=true;}),error=>error.message===PRO_AUTH_ERROR);
 }
 assert.equal(redirected,false);
 await assert.rejects(beginProfessionalLogin({authStart:async()=>({authorization_url:'https://identity.example.invalid/'})},()=>{throw Error('synthetic navigation detail');}),error=>error.message===PRO_AUTH_ERROR);
});

test('only the generic failed-login marker on the connection route is displayed',()=>{
 assert.equal(authFailureMessage('#/connexion?auth=failed&code=synthetic-secret&error_description=private'),PRO_AUTH_ERROR);
 for(const hash of ['#/connexion','#/connexion?auth=ok','#/other?auth=failed','#/connexion?code=synthetic-secret',undefined])assert.equal(authFailureMessage(hash),'');
});

test('an access request awaiting authorization has a generic pending message without callback details',()=>{
 assert.equal(authFailureMessage('#/connexion?auth=pending&code=synthetic-secret'),'Votre demande d’accès attend l’autorisation de l’administrateur.');
});

test('signup is offered only when the OIDC server explicitly enables it and uses a distinct intent',async()=>{
 assert.equal(authPresentation({auth:{method:'oidc',sso_available:true,signup_available:true}}).signupAvailable,true);
 for(const auth of [{method:'password',sso_available:true,signup_available:true},{method:'oidc',sso_available:false,signup_available:true},{method:'oidc',sso_available:true,signup_available:false}])assert.equal(authPresentation({auth}).signupAvailable,false);
 const calls=[];
 await beginProfessionalLogin({async authStart(payload){calls.push(payload);return{authorization_url:'https://identity.example.invalid/register'};}},()=>{},'signup');
 assert.deepEqual(calls,[{intent:'signup'}]);
 let called=false;await assert.rejects(()=>beginProfessionalLogin({authStart(){called=true;}},()=>{},'unsupported'),error=>error.message===PRO_AUTH_ERROR);assert.equal(called,false);
});

test('recovery uses the same server boundary with an optional validated email hint',async()=>{
 const calls=[];await beginProfessionalLogin({async authStart(payload){calls.push(payload);return{authorization_url:'https://identity.example.invalid/forgot-credentials'};}},()=>{},'recovery','agent@collectivite.fr');
 assert.deepEqual(calls,[{intent:'recovery',login_hint:'agent@collectivite.fr'}]);
 for(const hint of ['agent@example.fr\n','agent localhost','x'.repeat(300),null]){
  let called=false;await assert.rejects(()=>beginProfessionalLogin({authStart(){called=true;}},()=>{},'login',hint),error=>error.message===PRO_AUTH_ERROR);assert.equal(called,false);
 }
});
