import {useEffect,useRef,useState} from 'react';
import {mountNativePage} from '../../../../web/native.js';
import {actionInputs} from '../../../../web/workspace-model.js';
import {registerPreserver} from './panel-lifecycle';
import {nativeAccessGuard} from './native-actions';
import type {NativeMetadata,ProjectApi,ProjectRecord} from './ProjectPanels.types';

interface Props {api:ProjectApi;project:ProjectRecord;view:'page'|'table'|'kanban';canWrite:boolean;onSaved?:()=>void;onMetadata?:(value:NativeMetadata)=>void}
interface NativeController {flush():Promise<unknown>;updateActions(actions:unknown[]):Promise<unknown>;destroy():void;readonly dirty:boolean;getMetadata?():NativeMetadata|undefined}
type MountPage=(host:HTMLElement,options:{api:ProjectApi;project:{id:string;name:string};view:string;actions:unknown[];beforeSave:()=>void;onSaved:()=>void;onDirty:(dirty:boolean)=>void;onMetadata:(value:NativeMetadata)=>void})=>Promise<NativeController|undefined>;
const mountPage=mountNativePage as unknown as MountPage;
export default function BlockEditor({api,project,view,canWrite,onSaved,onMetadata}:Props){
  const host=useRef<HTMLDivElement>(null),callbacks=useRef({onSaved,onMetadata});callbacks.current={onSaved,onMetadata};
  const [error,setError]=useState('');
  const actions=JSON.stringify(actionInputs(project.actions));
  const current=useRef({name:project.name,actions});current.current={name:project.name,actions};
  const liveController=useRef<NativeController|undefined>(undefined),readyController=useRef<Promise<unknown>|null>(null);
  useEffect(()=>{
    if(!host.current||!canWrite)return;
    let disposed=false,pendingDirty=false,controller:NativeController|undefined;
    setError('');
    const ready=mountPage(host.current,{api,project:{id:project.id,name:current.current.name},view,actions:JSON.parse(current.current.actions),beforeSave:nativeAccessGuard(project.id),onSaved:()=>callbacks.current.onSaved?.(),onDirty:dirty=>{pendingDirty=dirty;},onMetadata:value=>callbacks.current.onMetadata?.(value)})
      .then(value=>{controller=value;if(disposed)value?.destroy();else {liveController.current=value;const metadata=value?.getMetadata?.();if(metadata)callbacks.current.onMetadata?.(metadata);}})
      .catch(()=>{if(!disposed)setError('Les notes ne peuvent pas être ouvertes. Les versions sauvegardées restent conservées. Rechargez ce dossier pour réessayer.');});
    readyController.current=ready;
    const unregister=registerPreserver(async()=>{await ready;await controller?.flush();},()=>Boolean(controller?.dirty||pendingDirty));
    return()=>{disposed=true;unregister();if(liveController.current===controller)liveController.current=undefined;controller?.destroy();};
  },[api,project.id,view,canWrite]);
  useEffect(()=>{let active=true;const ready=readyController.current;void Promise.resolve(ready).then(async()=>{if(active&&canWrite)await liveController.current?.updateActions(JSON.parse(actions));}).catch(cause=>{if(active)setError(cause instanceof Error?cause.message:'Les actions ne peuvent pas être actualisées. Vos notes restent ouvertes.');});return()=>{active=false;};},[api,project.id,view,canWrite,actions]);
  if(!canWrite)return <section className="note-preview" aria-label={view==='page'?'Notes en lecture seule':'Suivi en lecture seule'}><p className="muted-label">Lecture seule</p>{project.notes.length?project.notes.map(note=><article key={note.id}><p className="whitespace-pre-wrap">{note.content}</p></article>):<p>Aucune note enregistrée dans ce dossier.</p>}</section>;
  return <div className="block-editor native-document-panel integrated-panel">{error&&<p role="alert">{error}</p>}<div ref={host} data-project-id={project.id} aria-label={view==='page'?'Notes du chantier':'Actions du chantier'}/></div>;
}
