import test from 'node:test';
import assert from 'node:assert/strict';
import * as setup from './mail-connection-model.mjs';

const hub={public_demo:false,can_manage:true,external_connections_enabled:true,providers:[{id:'exchange',available:true}]};
const account={label:'Travaux',mailbox:'travaux@example.invalid',username:'',endpoint:'https://mail.example.invalid/EWS/Exchange.asmx',password:'fictional-test-secret'};
const connection={id:'one',provider:'exchange',revision:2,status:'verified',has_secret:true,selected_calendar_ids:['calendar-a'],selected_folder_ids:['inbox'],mail_folders:[{id:'inbox',name:'Réception'},{id:'archive',name:'Archives'}],last_mail_sync_at:null};

test('public and unprivileged setup cannot call a real connection endpoint',async()=>{
 for(const restricted of [{...hub,public_demo:true},{...hub,can_manage:false},{...hub,external_connections_enabled:false}]){
  let called=false;
  await assert.rejects(()=>setup.verifyMailAccount({api:{createConnection(){called=true;}},hub:restricted,values:account}),/démonstration publique|administrateur|autorisé/u);
  assert.equal(called,false);
 }
});

test('account validation never guesses the server and defaults the login to the supplied email',()=>{
 const payload=setup.mailAccountPayload(account);
 assert.equal(payload.username,account.mailbox);assert.equal(payload.provider,'exchange');
 assert.equal(payload.endpoint,account.endpoint);
 assert.throws(()=>setup.mailAccountPayload({...account,endpoint:''}),/serveur/u);
 assert.throws(()=>setup.mailAccountPayload({...account,endpoint:'http://mail.example.invalid'}),/HTTPS/u);
 assert.throws(()=>setup.mailAccountPayload({...account,endpoint:'https://user:pass@mail.example.invalid'}),/identifiant/u);
});

test('a created account is retained before a failed probe, so retry probes it without another creation',async()=>{
 let saved;const calls=[];
 const created={...connection,status:'not_tested',revision:0};
 const api={async createConnection(){calls.push('create');return created;},async probeConnection(id,payload){calls.push(['probe',id,payload]);throw Error('Serveur temporairement inaccessible');}};
 await assert.rejects(()=>setup.verifyMailAccount({api,hub,values:account,onCreated:value=>{saved=value;}}),/temporairement/u);
 assert.equal(saved,created);
 api.probeConnection=async(id,payload)=>{calls.push(['retry',id,payload]);return connection;};
 const result=await setup.verifyMailAccount({api,hub,connection:saved});
 assert.equal(result,connection);assert.equal(calls.filter(value=>value==='create').length,1);
 assert.deepEqual(calls.at(-1),['retry','one',{expected_revision:0}]);
});

test('revoked identity after creation prevents probe and publishing the old account',async()=>{
 let current=true,probed=false,published=false;
 const api={async createConnection(){current=false;return connection;},async probeConnection(){probed=true;}};
 await assert.rejects(()=>setup.verifyMailAccount({api,hub,values:account,assertCurrent(){if(!current)throw Error('identity changed');},onCreated(){published=true;}}),/identity changed/u);
 assert.equal(probed,false);assert.equal(published,false);
});

test('saving mailbox folders preserves calendar selection and uses the current connection revision',async()=>{
 let sent;
 const api={async selectConnection(id,payload){sent={id,payload};return {...connection,revision:3,selected_folder_ids:['archive']};}};
 const saved=await setup.saveMailFolders({api,hub,connection,folderIds:['archive']});
 assert.deepEqual(sent,{id:'one',payload:{expected_revision:2,calendar_ids:['calendar-a'],folder_ids:['archive']}});
 assert.equal(saved.revision,3);assert.deepEqual(connection.selected_folder_ids,['inbox']);
});

test('an empty or undiscovered folder cannot be saved',async()=>{
 for(const folderIds of [[],['unknown']])await assert.rejects(()=>setup.saveMailFolders({api:{},hub,connection,folderIds}),/dossier/u);
});

test('a stale revision leaves the submitted selection intact and does not retry automatically',async()=>{
 const folderIds=['archive'];let calls=0;
 const conflict=Object.assign(Error('Version modifiée'),{status:409,detail:{code:'stale_revision'}});
 await assert.rejects(()=>setup.saveMailFolders({api:{async selectConnection(){calls++;throw conflict;}},hub,connection,folderIds}),error=>error===conflict);
 assert.equal(calls,1);assert.deepEqual(folderIds,['archive']);
});

test('import is blocked while local folders differ from the saved selection',async()=>{
 let called=false;
 await assert.rejects(()=>setup.importMailSelection({api:{async syncConnectionMail(){called=true;}},hub,connection,folderIds:['archive']}),/sélection/u);
 assert.equal(called,false);
});

test('one partial collect uses returned revision and does not claim unique mail count or drain silently',async()=>{
 let calls=0;
 const saved={...connection,revision:7};
 const result=await setup.importMailSelection({api:{async syncConnectionMail(id,payload){calls++;assert.equal(id,'one');assert.deepEqual(payload,{expected_revision:7});return {accepted:5,more_available:true,connection:{...saved,revision:8,last_mail_sync_at:'2026-11-16T10:00:00Z'}};}},hub,connection:saved,folderIds:['inbox']});
 assert.equal(calls,1);assert.equal(result.moreAvailable,true);assert.equal(result.acknowledged,5);assert.equal(result.connection.revision,8);
 assert.equal('importedMailCount' in result,false);
});

test('calendar-only synchronization is not treated as a completed mail import',()=>{
 assert.equal(setup.mailSetupState({...connection,status:'synced',last_calendar_sync_at:'2026-11-16T10:00:00Z'}),'ready');
 assert.equal(setup.mailSetupState({...connection,last_mail_sync_at:'2026-11-16T10:00:00Z'}),'read_only');
 assert.equal(setup.mailSetupState({...connection,status:'not_tested'}),'not_tested');
 assert.equal(setup.mailSetupState({...connection,status:'disconnected'}),'disconnected');
});

const cloudHub={...hub,providers:[{id:'exchange',available:false},{id:'google',available:true,authorization:'oauth2'},{id:'microsoft365',available:true,authorization:'oauth2'}]};
test('mail access is provider-scoped and an unavailable cloud provider cannot borrow Exchange availability',()=>{
 assert.equal(setup.mailSetupAccess(cloudHub,'google').live,true);
 assert.equal(setup.mailSetupAccess(cloudHub).live,false);
 assert.equal(setup.mailSetupAccess(hub,'google').live,false);
 assert.equal(setup.mailSetupAccess({...cloudHub,public_demo:true},'google').live,false);
 assert.equal(setup.mailSetupAccess({...cloudHub,providers:[{id:'unexpected',available:true}]},'unexpected').live,false);
 const unavailable={...cloudHub,providers:[{id:'google',available:false,reason:'Configuration Google nécessaire.'}]};
 assert.equal(setup.mailSetupAccess(unavailable,'google').reason,'Configuration Google nécessaire.');
});

test('an existing cloud account uses generic probe, folder selection and one read-only collect without password creation',async()=>{
 for(const provider of ['google','microsoft365']){
  const record={...connection,provider,selected_calendar_ids:[]};const calls=[];
  const api={createConnection(){assert.fail('cloud must not create a password connection');},
   async probeConnection(id,body){calls.push(['probe',id,body]);return record;},
   async selectConnection(id,body){calls.push(['select',id,body]);return {...record,revision:3};},
   async syncConnectionMail(id,body){calls.push(['read',id,body]);return{connection:record,accepted:1,more_available:false};}};
  await setup.verifyMailAccount({api,hub:cloudHub,connection:record});
  await setup.saveMailFolders({api,hub:cloudHub,connection:record,folderIds:['inbox']});
  await setup.importMailSelection({api,hub:cloudHub,connection:record,folderIds:['inbox']});
  assert.deepEqual(calls,[['probe','one',{expected_revision:2}],['select','one',{folder_ids:['inbox'],calendar_ids:[],expected_revision:2}],['read','one',{expected_revision:2}]]);
 }
});

test('cloud OAuth sends only the chosen provider and optional label then validates the returned HTTPS URL',async()=>{
 const calls=[];
 await setup.beginMailOAuth({api:{async startMailOAuth(provider,body){calls.push([provider,body]);return{authorization_url:'https://identity.example.invalid/authorize?state=synthetic'};}},hub:cloudHub,provider:'google',label:' Compte travaux ',redirect:url=>calls.push(url)});
 assert.deepEqual(calls,[['google',{label:'Compte travaux'}],'https://identity.example.invalid/authorize?state=synthetic']);
});

test('OAuth cannot start in demo, without permission or provider configuration, and never exposes raw provider failures',async()=>{
 for(const restricted of [{...cloudHub,public_demo:true},{...cloudHub,can_manage:false},{...cloudHub,external_connections_enabled:false},hub]){
  let called=false;
  await assert.rejects(()=>setup.beginMailOAuth({api:{startMailOAuth(){called=true;}},hub:restricted,provider:'google',redirect(){assert.fail('must not redirect');}}));
  assert.equal(called,false);
 }
 for(const response of [{authorization_url:'http://identity.example.invalid/'},{authorization_url:'https://user:secret@identity.example.invalid/'},null]){
  await assert.rejects(()=>setup.beginMailOAuth({api:{async startMailOAuth(){return response;}},hub:cloudHub,provider:'google',redirect(){assert.fail('unsafe redirect');}}),error=>error.message===setup.MAIL_OAUTH_ERROR);
 }
 await assert.rejects(()=>setup.beginMailOAuth({api:{async startMailOAuth(){throw Error('synthetic-secret-provider-token');}},hub:cloudHub,provider:'google',redirect(){}}),error=>error.message===setup.MAIL_OAUTH_ERROR);
});

test('identity revoked during OAuth start prevents navigation',async()=>{
 let current=true,redirected=false;
 await assert.rejects(()=>setup.beginMailOAuth({api:{async startMailOAuth(){current=false;return{authorization_url:'https://identity.example.invalid/'};}},hub:cloudHub,provider:'microsoft365',redirect(){redirected=true;},assertCurrent(){if(!current)throw Error('active identity changed');}}),/active identity changed/u);
 assert.equal(redirected,false);
});

test('OAuth callback copy is generic, contains no query code and claims no verified mailbox from the marker alone',()=>{
 assert.equal(setup.mailOAuthFeedback('#/connexions?oauth=failed&code=synthetic-secret').kind,'error');
 assert.equal(setup.mailOAuthFeedback('#/connexions?oauth=cancelled').kind,'cancelled');
 assert.equal(setup.mailOAuthFeedback('#/connexions?oauth=connected').kind,'success');
 assert.equal(setup.mailOAuthFeedback('#/other?oauth=connected'),null);
 assert.equal(setup.mailOAuthFeedback('#/connexions?oauth=unknown'),null);
 assert.equal(JSON.stringify(setup.mailOAuthFeedback('#/connexions?oauth=failed&code=synthetic-secret')).includes('synthetic-secret'),false);
});

test('public Microsoft setup explains the block and points to the connection page without promising activation',()=>{
 const access=setup.mailSetupAccess({...cloudHub,public_demo:true},'microsoft365');
 assert.equal(access.live,false);assert.equal(access.blockedBy,'public_demo');
 assert.match(access.reason,/démonstration publique/u);
 assert.match(access.nextAction,/administrateur|service informatique/u);
 assert.equal(access.privateAccessHref,'/connexion.html');
 assert.doesNotMatch(access.nextAction,/déjà activé|compte connecté/u);
});

test('administrator and server configuration blocks give distinct recovery actions',()=>{
 const noRole=setup.mailSetupAccess({...cloudHub,can_manage:false},'microsoft365');
 const noServer=setup.mailSetupAccess({...cloudHub,external_connections_enabled:false},'microsoft365');
 assert.equal(noRole.blockedBy,'administrator');assert.match(noRole.nextAction,/administrateur/u);
 assert.equal(noServer.blockedBy,'server_configuration');assert.match(noServer.nextAction,/configuration|serveur/u);
 assert.equal(noRole.privateAccessHref,null);assert.equal(noServer.privateAccessHref,null);
 assert.equal(setup.mailSetupAccess(cloudHub,'microsoft365').blockedBy,null);
});

test('Microsoft administrator instructions are read-only and use a clearly fictional private callback',()=>{
 assert.equal(typeof setup.mailProviderConfiguration,'function');
 const guide=setup.mailProviderConfiguration('microsoft365');
 assert.equal(guide.title,'Configuration Microsoft 365');
 assert.equal(guide.callbackPath,'/api/v1/integrations/oauth/microsoft365/callback');
 assert.equal(new URL(guide.callbackExample).hostname,'espace-prive.example');
 assert.match(guide.steps.join(' '),/tenant|Entra/u);
 assert.match(guide.steps.join(' '),/secret|coffre/u);
 assert.match(guide.steps.join(' '),/DSI/u);
 assert.match(guide.steps.join(' '),/Mail\.Read/u);
 assert.doesNotMatch(JSON.stringify(guide),/Mail\.ReadWrite|Mail\.Send|authorization_url|client_secret=/u);
 assert.equal(setup.mailProviderConfiguration('exchange'),null);
 assert.equal(setup.mailProviderConfiguration('<script>'),null);
});

test('OAuth returns to the exact active mailbox, even with older connected accounts',()=>{
 const id='a2b6bb6a-ab97-491f-bd08-ac6e788d6745';
 const record={...connection,id,provider:'microsoft365',status:'not_tested'};
 const existing={...record,id:'b3c7cc7b-bc08-402a-883f-cd7f899e7856'};
 const connectedHub={...cloudHub,connections:[existing,record]};
 const hash=`#/connexions?oauth=connected&connection=${id}&code=private`;
 const feedback=setup.mailOAuthFeedback(hash);
 assert.equal(feedback.connectionId,id);
 assert.doesNotMatch(JSON.stringify(feedback),/private/u);
 assert.equal(setup.mailOAuthConnection(connectedHub,feedback),record);
 assert.equal(setup.mailOAuthConnection({...connectedHub,connections:[existing]},feedback),undefined);
 assert.equal(setup.mailOAuthConnection({...connectedHub,connections:[{...record,status:'disconnected'}]},feedback),undefined);
 assert.equal(setup.mailOAuthConnection({...connectedHub,connections:[{...record,has_secret:false}]},feedback),undefined);
 assert.equal(setup.mailOAuthConnection({...connectedHub,connections:[{...record,provider:'exchange'}]},feedback),undefined);
 assert.equal(setup.mailOAuthConnection({...connectedHub,can_manage:false},feedback),undefined);
 for(const invalid of [`#/connexions?oauth=cancelled&connection=${id}`,`#/connexions?oauth=connected&connection=${id}&connection=${id}`,'#/connexions?oauth=connected&connection=%2Fmalformed']){
  assert.equal(setup.mailOAuthConnection(connectedHub,setup.mailOAuthFeedback(invalid)),undefined);
 }
});

test('Mairie test cannot start Outlook OAuth, even with inconsistent client capability values',async()=>{
 const fictional={...cloudHub,test_organization:true};
 const access=setup.mailSetupAccess(fictional,'microsoft365');
 assert.equal(access.blockedBy,'test_organization');
 assert.equal(access.live,false);
 assert.match(access.reason,/Mairie test/u);
 await assert.rejects(()=>setup.beginMailOAuth({api:{startMailOAuth(){assert.fail('no provider call');}},hub:fictional,provider:'microsoft365',redirect:()=>assert.fail('no redirect')}),/Mairie test/u);
});
