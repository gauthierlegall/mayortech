import {build} from 'esbuild';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const own=path.dirname(fileURLToPath(import.meta.url));
const frontend=path.resolve(own,'../../..');
const project=path.resolve(frontend,'..');
const output=path.resolve(process.argv[2]||path.join(project,'test-results/native-session-react/site'));
const baseline=process.argv[3]&&!process.argv[3].startsWith('--')?path.resolve(process.argv[3]):null;
const negativeControl=process.argv.includes('--unsafe-lifecycle-control');
const negativeWorkspaceObservation=process.argv.includes('--unsafe-workspace-observation-control');
await mkdir(path.join(output,'native'),{recursive:true});
const plugin={name:'explicit-native-fixture',setup(build){
 build.onResolve({filter:/^\.\/context$/},args=>args.importer.endsWith('AuthGate.tsx')||args.importer.endsWith(path.sep+'Actions.tsx')?{path:path.join(own,'context-mock.tsx')}:undefined);
 build.onResolve({filter:/web\/native\.js$/},()=>({path:path.join(own,'native-page-mock.ts')}));
 build.onResolve({filter:/^\.\/native-actions$/},args=>args.importer.endsWith(path.sep+'Actions.tsx')?{path:path.join(own,'actions-store-mock.ts')}:undefined);
 build.onResolve({filter:/^@\/components\/ui\/button$/},()=>({path:'button',namespace:'fixture'}));
 build.onResolve({filter:/^@\/components\/ui\/dialog$/},()=>({path:'dialog',namespace:'fixture'}));
 build.onResolve({filter:/^\.\/OrganizationJoin$/},args=>args.importer.endsWith('AuthGate.tsx')?{path:'join',namespace:'fixture'}:undefined);
 build.onLoad({filter:/.*/,namespace:'fixture'},args=>({loader:'tsx',resolveDir:frontend,contents:args.path==='button'?'export function Button({variant,size,...props}){return <button {...props}/>;}':args.path==='dialog'?'export function Dialog({open,children}){return open?<div>{children}</div>:null;}export function DialogContent({children}){return <div>{children}</div>;}export function DialogTitle({children}){return <h2>{children}</h2>;}export function DialogDescription({children}){return <p>{children}</p>;}':'export function OrganizationJoin(){return <p>Choix d’organisation simulé</p>;}'}));
 if(baseline||negativeControl)build.onLoad({filter:/(?:BlockEditor|AuthGate)\.tsx$/},async args=>{
  let contents=await readFile(baseline?path.join(baseline,path.basename(args.path)):args.path,'utf8');
  if(negativeControl){
   // Test-bundle mutation only; never edit the production modules on disk.
   if(args.path.endsWith('BlockEditor.tsx')){
    const safe='},[api,project.id,view,canWrite]);';
    if(!contents.includes(safe))throw Error('Negative remount control no longer matches the production mount effect');
    contents=contents.replace(safe,'},[api,project.id,project.name,view,actions,canWrite]);');
   }else{
    const key=/<Fragment key=\{(?:JSON\.stringify\(\[[^\]]*\]\)|workspaceIdentity\(session\))\}>/;
    if(!key.test(contents))throw Error('Negative account-key control no longer matches AuthGate');
    contents=contents.replace(key,'<Fragment>');
   }
  }
  return {loader:'tsx',resolveDir:path.dirname(args.path),contents};
 });
 }};
await build({entryPoints:[path.join(own,'fixture.tsx')],bundle:true,format:'esm',platform:'browser',jsx:'automatic',outfile:path.join(output,'fixture.js'),plugins:[plugin],logLevel:'silent'});
await writeFile(path.join(output,'index.html'),'<!doctype html><html lang="fr"><meta charset="utf-8"><title>Recette React contrôlée</title><style>body{font:18px system-ui;margin:0;background:#f3f5f7;color:#17243b}main{max-width:1100px;margin:70px auto;background:white;padding:36px;border-radius:18px;border:1px solid #ccd7df}h1{font-size:30px}.notice{background:#edf4ff;padding:16px}textarea{width:95%;min-height:200px;padding:18px;font:20px system-ui;border:2px solid #557ba5;border-radius:10px}</style><div id="root"></div><script type="module" src="/fixture.js"></script></html>');
await writeFile(path.join(output,'native/editor.js'),'export async function mount(host,options){return {dirty:false,revisionHash:null,getText:async()=>"",getNotesText:async()=>"",getMetadata:()=>({databases:[]}),unmount(){},save:async()=>{},importActions(){}};}');
const workspacePlugin={name:'explicit-workspace-api-fixture',setup(build){
 build.onResolve({filter:/web\/api\.js$/},()=>({path:path.join(own,'workspace-api-mock.ts')}));
 build.onResolve({filter:/^@\/components\/ui\/button$/},()=>({path:'button',namespace:'workspace-fixture'}));
 build.onLoad({filter:/.*/,namespace:'workspace-fixture'},()=>({loader:'tsx',resolveDir:frontend,contents:'export function Button({variant,size,...props}){return <button {...props}/>;}'}));
 if(negativeWorkspaceObservation)build.onLoad({filter:/[\\/]data\.ts$/},async args=>{
  let contents=await readFile(args.path,'utf8');
  const original='identity=observeWorkspaceIdentity(session)';
  if(!contents.includes(original))throw Error('Negative workspace observation control no longer matches loadWorkspace');
  contents="import {workspaceIdentity as fixtureSessionIdentity} from './workspace-scope.mjs';\n"+contents.replace(original,"identity=(session?.actor?.actor_id==='account-b'?fixtureSessionIdentity(session):observeWorkspaceIdentity(session))");
  return {loader:'ts',resolveDir:path.dirname(args.path),contents};
 });
}};
await build({entryPoints:[path.join(own,'workspace-provider-fixture.tsx')],bundle:true,format:'esm',platform:'browser',jsx:'automatic',outfile:path.join(output,'workspace-provider.js'),plugins:[workspacePlugin],logLevel:'silent'});
await writeFile(path.join(output,'workspace-provider.html'),(await readFile(path.join(output,'index.html'),'utf8')).replace('src="/fixture.js"','src="/workspace-provider.js"'));
console.log(JSON.stringify({output,fixture:true,baseline:Boolean(baseline),negative_control:negativeControl,negative_workspace_observation:negativeWorkspaceObservation,productionComponents:['AuthGate','BlockEditor','Actions','WorkspaceProvider','loadWorkspace'],mocked:['workspace context (native cases only)','native page controller','Actions projection/transport','API transport (WorkspaceProvider case only)'],network:'local static assets only'}));
