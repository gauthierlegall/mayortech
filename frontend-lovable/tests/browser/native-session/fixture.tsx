import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AuthGate} from '../../../src/features/workspace/AuthGate';
import BlockEditor from '../../../src/features/workspace/BlockEditor';
import {Actions} from '../../../src/features/workspace/Actions';
import * as nativeScope from '../../../src/features/workspace/native-actions';
import {preservePanels} from '../../../src/features/workspace/panel-lifecycle';
import {FixtureWorkspace} from './context-mock';

const fixtureWindow=window as any;
const api={project:async(id:string)=>({id,name:'Dossier fictif '+id,actions:[]}),nativePage:async(id:string)=>({id:'page-'+id})};
const scope=(actor:string)=>JSON.stringify([true,'fixture-tenant',actor,'editor',actor]);
function Fixture(){
 const [actor,setActor]=useState('account-a'),[allowed,setAllowed]=useState(['retained','neighbor']);
 const [project,setProject]=useState<any>({id:'retained',name:'Dossier fictif initial',actions:[],notes:[]});
 const [stage,setStage]=useState('Prêt');
 const [mode,setMode]=useState<'notes'|'actions'>('notes');
 const session={authenticated:true,auth_required:true,organization_required:false,actor:{tenant_id:'fixture-tenant',actor_id:actor,role:'editor'},account:{id:actor,display_name:actor},auth:{method:'oidc',sso_available:true,signup_available:true}};
 const workspace={session,api,refresh:async()=>{},bootstrap:{permissions:{workspace:{write:true}}},state:{projects:allowed.map(id=>({id,title:'Dossier fictif '+id,owner:''}))}};
 const all=()=>fixtureWindow.__nativeControllers||[];
 fixtureWindow.lab={
  async preserveBeforeReload(){await preservePanels();setStage('Réponse réseau simulée en attente');},
  receiveChangedActions(){setProject((before:any)=>({...before,name:'Dossier fictif renommé',actions:[{id:'assistant-action-fixture',value:'Action fictive reçue pendant la saisie'}]}));setStage('Nouvelles actions reçues');},
  switchAccount(){nativeScope.scopeNativeActions(scope('account-b'),allowed);setActor('account-b');setStage('Compte B actif');},
  revokeCurrent(){nativeScope.scopeNativeActions(scope(actor),['neighbor']);setAllowed(['neighbor']);setStage('Accès du dossier courant retiré');},
  async revokeNeighbor(){await nativeScope.loadNativeActions(api,['neighbor'],false);nativeScope.scopeNativeActions(scope(actor),['retained']);setAllowed(['retained']);setStage('Dossier voisin retiré ; dossier courant conservé');},
  showActions(){setMode('actions');},
  revokeNeighborWithFailedActionLoad(){fixtureWindow.__failActionLoad=true;nativeScope.scopeNativeActions(scope(actor),['retained']);setAllowed(['retained']);setStage('Dossier voisin retiré ; rechargement actions en échec');},
  beginDeferredSave(){const controller=all().at(-1);fixtureWindow.pendingController=controller;fixtureWindow.pendingSave=controller.beginDeferredSave().then(()=>({ok:true}), (error:Error)=>({ok:false,error:error.message}));},
  async releaseDeferredSave(){fixtureWindow.pendingController.release();return await fixtureWindow.pendingSave;},
  diagnostics(){return all().map((item:any)=>({id:item.id,text:item.text,dirty:item.dirty,destroyed:item.destroyed,flushes:item.flushes,updates:item.updates,writes:item.writes,blocked:item.blocked}));},
 };
 return <FixtureWorkspace.Provider value={workspace}><main><h1>Recette React — contrôleur natif simulé</h1><p className="notice">Données fictives. Aucun compte, fournisseur ou serveur métier réel. AuthGate, BlockEditor et Actions proviennent du projet.</p><p>Compte actif : <strong>{actor}</strong> · Accès : {allowed.join(', ')}</p><p role="status">{stage}</p><AuthGate><section aria-label="Zone métier protégée">{mode==='notes'?<BlockEditor api={api as any} project={project} view="page" canWrite={true}/>:<Actions/>}</section></AuthGate><p>Les changements et sauvegardes différées sont pilotés par le test navigateur.</p></main></FixtureWorkspace.Provider>;
}
fixtureWindow.__actionFixtureRows=['retained','neighbor'].map((projectId,index)=>({id:'action-'+projectId,projectId,databaseId:'db-fixture',title:index?'Action fictive du dossier révoqué':'Action fictive du dossier conservé',description:'',status:'À faire',owner:'',due:'',priority:'Normale',fingerprint:'fictional-'+projectId}));
nativeScope.scopeNativeActions(scope('account-a'),['retained','neighbor']);
createRoot(document.getElementById('root')!).render(<Fixture/>);
