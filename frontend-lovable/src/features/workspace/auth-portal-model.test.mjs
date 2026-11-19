import assert from 'node:assert/strict';
import test from 'node:test';
import {portalMode,portalCapabilities,portalDestination,legacyDemoDestination,validLoginEmail,privateEntry} from './auth-portal-model.mjs';

test('separate HTML entry routes have fixed purposes',()=>{
 assert.equal(portalMode('/inscription.html'),'signup');assert.equal(portalMode('/mot-de-passe-oublie.html'),'recovery');assert.equal(portalMode('/connexion.html'),'login');
});
test('the public front door only links to an explicit HTTPS private entry',()=>{
 const config={private_access_url:'https://espace.example.invalid/connexion.html'};
 assert.equal(privateEntry(config,'signup'),'https://espace.example.invalid/inscription.html');
 assert.equal(privateEntry(config,'recovery'),'https://espace.example.invalid/mot-de-passe-oublie.html');
 for(const value of ['',null,'http://espace.invalid/connexion.html','https://user:password@espace.invalid/connexion.html','https://espace.invalid/connexion.html?return=https://bad.invalid','https://espace.invalid/connexion.html#','https://espace.invalid:444/connexion.html','https://espace.invalid/connexion.html\n','//bad.invalid/connexion.html'])assert.equal(privateEntry({private_access_url:value}),null);
});
test('unconfigured and public endpoints cannot offer account creation or recovery',()=>{
 for(const value of [null,{}, {method:'demo',demo_available:true,login_available:true,signup_available:true,recovery_available:true},{method:'oidc',login_available:false,signup_available:true,recovery_available:true}]){
  const view=portalCapabilities(value);assert.equal(view.login,false);assert.equal(view.signup,false);assert.equal(view.recovery,false);
 }
 assert.deepEqual(portalCapabilities({method:'oidc',login_available:true,signup_available:true,recovery_available:true}),{login:true,signup:true,recovery:true,demo:false,pilot:false});
});
test('only individual authenticated private sessions enter the application',()=>{
 for(const session of [null,{}, {authenticated:true,public_demo:true,auth_required:true},{authenticated:true,auth_required:false},{authenticated:false,auth_required:true}])assert.equal(portalDestination(session),null);
 assert.equal(portalDestination({authenticated:true,auth_required:true,organization_required:true}),'/espace.html#/');
});
test('legacy hash compatibility never accepts an external return target',()=>{
 assert.equal(legacyDemoDestination('/','#/messagerie'),'/demo.html#/messagerie');
 assert.equal(legacyDemoDestination('/','#/connexions'),'/demo.html#/connexions');
 for(const hash of ['#https://bad.invalid','#//bad.invalid','javascript:alert(1)','#/connexion?auth=failed','#/x\\y','#/x\n'])assert.equal(legacyDemoDestination('/',hash),null);
 assert.equal(legacyDemoDestination('/connexion.html','#/'),null);
});
test('email hints are bounded and reject control characters before sending',()=>{
 assert.equal(validLoginEmail('agent@collectivite.fr'),true);
 for(const hint of ['',null,'person@localhost','person @collectivite.fr','person@collectivite.fr\n','x'.repeat(254)+'@example.fr'])assert.equal(validLoginEmail(hint),false);
});
