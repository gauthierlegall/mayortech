import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {Archive,FileEdit,Forward,HardHat,Inbox,Mail as MailIcon,Plus,Reply,ReplyAll,Send,Sparkles,Trash2} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogDescription,DialogTitle} from '@/components/ui/dialog';
import {useWorkspace} from './context';
import {SourcePreview} from './SourcePreview';
import {MailComposer,type MailComposerInitial} from './MailComposer';
import {createNativeAction} from './native-actions';
import {preservePanels,registerPreserver} from './panel-lifecycle';
import {workspaceMailIdentity} from './mail-navigation-state.mjs';
import {MayorValidationLaunchModal} from '../workflow/validation/MayorValidationLaunchModal';
import {toast} from 'sonner';
// @ts-ignore Shared, framework-neutral module; no remote client or gateway.
import {mountMailbox,parseRecipients,readMailboxLocation,mailboxDestination} from '../../../../web/mailbox.js';
// @ts-ignore Same audited read-only project mail view used by the original app.
import {mountMailView,normalizeMail} from '../../../../web/mail.js';
import './mail-layout.css';
import '../../../../web/mail-splitter.css';

const mailboxFolders=[{id:'inbox',title:'Boîte de réception',icon:Inbox},{id:'sent',title:'Envoyés',icon:Send},{id:'drafts',title:'Brouillons',icon:FileEdit},{id:'archive',title:'Archives',icon:Archive},{id:'trash',title:'Corbeille',icon:Trash2},{id:'all',title:'Tous les messages',icon:MailIcon}];
type MailController={destroy:()=>void;flush?:()=>Promise<void>;readonly dirty?:boolean};
type LegacyMount=(container:HTMLElement,options:any)=>MailController|Promise<MailController>;
const mountProjectMail=mountMailView as unknown as LegacyMount;
const mountGlobalMail=mountMailbox as unknown as LegacyMount;
export function prepareProjectReply(source:any,mode:MailComposerInitial['mode']):MailComposerInitial{
 const mail=normalizeMail(source),read=(value:any):string=>Array.isArray(value)?value.map(read).filter(Boolean).join(', '):typeof value==='string'?value:value&&typeof value==='object'?String(value.address||value.email||''):'';
 const recipients=(value:string)=>{try{return parseRecipients(value);}catch{return [];}};
 const to=mode==='forward'?'':Array.from(new Set([...recipients(mail.sender),...(mode==='reply-all'?recipients(mail.to):[])])).join(', ');
 const cc=mode==='reply-all'?read(source.cc||source.metadata?.cc):'';
 const subject=mail.subject.replace(/^(?:(?:re|tr|fw|fwd)\s*:\s*)+/i,'');
 const quote=`\n\n----- Message d’origine -----\nDe : ${mail.sender}\nObjet : ${mail.subject}\n\n${mail.body}`;
 return {sourceId:mail.id,to,cc,subject:`${mode==='forward'?'Tr':'Re'} : ${subject}`,body:(mode==='suggested'?'Bonjour,\n\nMerci pour votre message. Je reviens vers vous après vérification des informations du dossier.\n\n':'')+quote,mode};
}
export function projectMailDestination(projectId:string,href:string){
 const match=/^#\/(?:mail|messagerie)(?:\/([^/?]+))?(?:\?.*)?$/.exec(href);
 if(!match)return href;
 const query=new URLSearchParams({view:'exchanges'});
 if(match[1]){try{query.set('mail',decodeURIComponent(match[1]));}catch{return href;}}
 return `#/chantiers/${encodeURIComponent(projectId)}?${query}`;
}
export function readMailLocation(hash:string,search=''){
 return readMailboxLocation(hash,search);
}

export function Mail({projectId,initialId}:{projectId?:string;initialId?:string}){
 const {state,api,session,bootstrap,refresh}=useWorkspace();
 const identity=workspaceMailIdentity(session);
 const Surface=projectId?'section':'main';
 const container=useRef<HTMLDivElement>(null),[location,setLocation]=useState(()=>readMailLocation(window.location.hash,window.location.search));
 const [error,setError]=useState(''),[retry,setRetry]=useState(0),[source,setSource]=useState<{id:string;focus:HTMLElement|null}|null>(null);
 const [selectedMessage,setSelectedMessage]=useState<any>(null),[actionsTarget,setActionsTarget]=useState<HTMLElement|null>(null),[compose,setCompose]=useState<MailComposerInitial|null>(null),[notice,setNotice]=useState('');
 const [folderTarget,setFolderTarget]=useState<HTMLElement|null>(null),[folderCounts,setFolderCounts]=useState<any[]>([]);
 const [actionOpen,setActionOpen]=useState(false),[actionBusy,setActionBusy]=useState(false),[actionError,setActionError]=useState('');
 const [validationMail,setValidationMail]=useState<any>(null);
 const actionPending=useRef(false),actionFocus=useRef<HTMLElement|null>(null);
 const canWrite=bootstrap?.permissions?.workspace?.write===true,publicDemo=Boolean(session?.public_demo||(session?.demo&&!session?.auth_required));
 useEffect(()=>{const changed=()=>setLocation(readMailLocation(window.location.hash,window.location.search));window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed);},[]);
 useEffect(()=>{
  const handleLaunch=(e:Event)=>{if(e instanceof CustomEvent&&e.detail?.mail)setValidationMail(e.detail.mail);};
  window.addEventListener('mayortech:launch-validation-from-mail',handleLaunch);
  return ()=>window.removeEventListener('mayortech:launch-validation-from-mail',handleLaunch);
 },[]);
 useEffect(()=>{
  if(!container.current)return;
  let disposed=false,handle:MailController|null=null,messageEpoch=0;
  const surface=document.createElement('div');surface.className='integrated-mail-surface';
  container.current.replaceChildren(surface);setError('');setSelectedMessage(null);setActionsTarget(null);setFolderTarget(null);
  const keepContextLinks=()=>{if(!projectId||disposed)return;for(const anchor of surface.querySelectorAll<HTMLAnchorElement>('a[href]')){const current=anchor.getAttribute('href')||'',next=projectMailDestination(projectId,current);if(next!==current)anchor.setAttribute('href',next);}const article=surface.querySelector('.mail-message');let target=article?.querySelector<HTMLElement>('[data-context-mail-actions]')??null;if(article&&!target){target=document.createElement('div');target.dataset.contextMailActions='';target.className='flex flex-wrap gap-2 border-t pt-4 mt-4';article.append(target);}setActionsTarget(previous=>previous===target?previous:target);};
  const contextLinks=new MutationObserver(keepContextLinks);if(projectId)contextLinks.observe(surface,{subtree:true,childList:true});
  const projects=state.projects.map((project:any)=>({...project,name:project.name??project.title,reference:project.reference??project.ref}));
  const showSource=(id:string)=>{if(!disposed)setSource({id,focus:document.activeElement instanceof HTMLElement?document.activeElement:null});};
  const mounted:Promise<MailController|null>=Promise.resolve().then(()=>{
   if(disposed)return null;
   return projectId?mountProjectMail(surface,{api:{...api,assign:bootstrap?.permissions?.mail?.write===true?api.assign:undefined,mailMessage:async(id:string,options:any)=>{const epoch=++messageEpoch;const response=await api.mailMessage(id,options),raw=response?.source??response,mail=normalizeMail(raw);if(!disposed&&epoch===messageEpoch)setSelectedMessage(mail.id===id&&mail.projectIds.includes(projectId)&&typeof raw.body==='string'?raw:null);return response;}},projects,mailId:initialId??null,initialFilters:{project_id:projectId},contextual:true,demo:Boolean(session?.demo),onNavigate:(href:string)=>{window.location.hash=projectMailDestination(projectId,href);}}):mountGlobalMail(surface,{api,projects,folder:location.folder,projectId:location.projectId,mailId:initialId??location.mailId,publicDemo,demo:Boolean(session?.demo),layout:'lovable',onLayout:({folderTarget:target}:{folderTarget:HTMLElement})=>{if(!disposed)setFolderTarget(target);},onSource:showSource,onFolders:(items:any[])=>{if(!disposed){setFolderCounts(items);window.dispatchEvent(new CustomEvent('travaux:mail-folders',{detail:{identity,items}}));}},onNavigate:(href:string)=>{window.location.hash=href;}});
  }).then(instance=>{if(disposed){instance?.destroy();return null;}handle=instance;return instance;}).catch(cause=>{if(!disposed)setError(cause instanceof Error?cause.message:'La messagerie ne peut pas être chargée. Réessayez.');return null;});
  // The shared shell awaits this before changing the hash or removing this view.
  const unregister=registerPreserver(async()=>{const current=handle??await mounted;await current?.flush?.();},()=>Boolean(handle?.dirty));
  return()=>{disposed=true;contextLinks.disconnect();unregister();handle?.destroy();surface.remove();};
 },[api,projectId,initialId,location.folder,location.projectId,location.mailId,retry,identity,session?.public_demo,session?.demo,session?.auth_required,bootstrap?.permissions?.mail?.write]);
 const startReply=(mode:MailComposerInitial['mode'])=>{if(!selectedMessage)return;const mail=normalizeMail(selectedMessage),warning=mode==='reply-all'&&!mail.to&&!selectedMessage.cc&&!selectedMessage.metadata?.cc?'Les autres destinataires ne sont pas conservés dans cet extrait. Vérifiez les destinataires du brouillon.':'';setNotice(warning);setCompose({...prepareProjectReply(selectedMessage,mode),...(warning?{warning}:{})});};
 return <Surface className={projectId?'mail-section integrated-panel':'mail-page integrated-panel'} aria-label={projectId?'Courriels du chantier':'Messagerie'}>
  {error&&<div className="source-callout" role="alert"><p>{error}</p><Button variant="outline" onClick={()=>setRetry(value=>value+1)}>Réessayer</Button></div>}
  <div ref={container} onClickCapture={event=>{const button=(event.target as Element).closest<HTMLElement>('[data-mail-source]');if(!button?.dataset.mailSource)return;event.preventDefault();event.stopPropagation();setSource({id:button.dataset.mailSource,focus:button});}}/>
  {folderTarget&&!projectId&&createPortal(<><nav className="mail-folder-options" aria-label="Dossiers de courrier">{mailboxFolders.map(folder=>{const count=folderCounts.find(item=>item.id===folder.id);return <a key={folder.id} className={location.folder===folder.id?'selected':''} aria-current={location.folder===folder.id?'page':undefined} href={mailboxDestination({folder:folder.id,projectId:location.projectId})}><folder.icon size={17} aria-hidden="true"/><span>{folder.title}</span>{typeof count?.unread==='number'&&count.unread>0&&<small aria-label={`${count.unread} non lus`}>{count.unread}</small>}</a>;})}</nav><nav className="mail-project-options" aria-label="Courriels par chantier"><div className="nav-label">DOSSIERS</div><a className={!location.projectId?'selected':''} aria-current={!location.projectId?'page':undefined} href={mailboxDestination({folder:location.folder})}><HardHat size={16} aria-hidden="true"/><span>Tous les chantiers</span></a>{state.projects.map(project=><a key={project.id} className={location.projectId===project.id?'selected':''} aria-current={location.projectId===project.id?'page':undefined} href={mailboxDestination({folder:location.folder==='drafts'?'inbox':location.folder,projectId:project.id})} title={project.title}><HardHat size={16} aria-hidden="true"/><span>{project.location?.split(' · ')[0]||project.title}<small>{project.ref}</small></span></a>)}</nav><label className="mail-mobile-project"><span>Chantier</span><select aria-label="Filtrer les courriels par chantier" value={location.projectId||''} onChange={event=>{const destination=mailboxDestination({folder:location.folder==='drafts'?'inbox':location.folder,projectId:event.target.value||null});void preservePanels().then(()=>{window.location.hash=destination;}).catch(failure=>setError(failure instanceof Error?failure.message:'Conservez le brouillon avant de changer de dossier.'));}}><option value="">Tous les chantiers</option>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select></label></>,folderTarget)}
  {!projectId&&<div className="mail-history-link"><a href="#/connexions">Connexions et reprise des courriels</a></div>}
  {actionsTarget&&selectedMessage&&createPortal(<><Button variant="outline" size="sm" onClick={()=>startReply('reply')}><Reply size={15}/>Répondre</Button><Button variant="outline" size="sm" onClick={()=>startReply('reply-all')}><ReplyAll size={15}/>À tous</Button><Button variant="outline" size="sm" onClick={()=>startReply('forward')}><Forward size={15}/>Transférer</Button><Button variant="outline" size="sm" onClick={()=>startReply('suggested')}><Sparkles size={15}/>Préparer une réponse</Button><Button variant="default" size="sm" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-1.5" onClick={()=>setValidationMail(selectedMessage)}><Plus size={15}/>Lancer une validation</Button><Button variant="outline" size="sm" disabled={!canWrite} onClick={event=>{actionFocus.current=event.currentTarget;setActionError('');setActionOpen(true);}}><Plus size={15}/>Créer une action</Button>{notice&&<p className="w-full text-sm text-muted-foreground" role="status">{notice}</p>}{actionError&&!actionOpen&&<p className="w-full text-sm" role="status">{actionError}</p>}</>,actionsTarget)}
  {compose&&<MailComposer api={api} open onClose={()=>setCompose(null)} initial={compose} publicDemo={publicDemo}/>}
  <Dialog open={actionOpen} onOpenChange={open=>{if(!actionPending.current)setActionOpen(open);}}><DialogContent className="max-h-[90dvh] overflow-y-auto" onCloseAutoFocus={event=>{event.preventDefault();actionFocus.current?.focus();}}><DialogTitle>Créer une action</DialogTitle><DialogDescription>Action du chantier reliée à ce courriel. Le message et les faits du dossier restent inchangés.</DialogDescription>{selectedMessage&&<form className="form-stack" onSubmit={async event=>{event.preventDefault();if(actionPending.current||!canWrite||!projectId)return;const data=new FormData(event.currentTarget),mail=normalizeMail(selectedMessage);if(!mail.projectIds.includes(projectId))return;actionPending.current=true;setActionBusy(true);setActionError('');try{await createNativeAction(api,projectId,{title:String(data.get('title')||'').trim(),description:String(data.get('description')||''),owner:String(data.get('owner')||''),dueDate:String(data.get('due')||''),priority:String(data.get('priority')||'Normale'),status:'À faire',sourceUrl:`#/mail/${encodeURIComponent(mail.id)}`});setActionOpen(false);setNotice('Action créée dans le chantier, avec le courriel d’origine.');void refresh().catch(()=>{});}catch(failure){setActionError(failure instanceof Error?failure.message:'L’action n’a pas pu être créée.');}finally{actionPending.current=false;setActionBusy(false);}}}><label>Titre<input name="title" required maxLength={500} defaultValue={`Suivre : ${normalizeMail(selectedMessage).subject}`}/></label><label>Responsable<input name="owner" maxLength={200}/></label><label>Échéance<input type="date" name="due"/></label><label>Priorité<select name="priority"><option>Normale</option><option>Haute</option><option>Basse</option></select></label><label>Description<textarea name="description" maxLength={4000} rows={4} defaultValue={normalizeMail(selectedMessage).body.slice(0,4000)}/></label><p className="muted-label">Source : {normalizeMail(selectedMessage).subject}</p>{actionError&&<p className="form-error" role="alert">{actionError}</p>}<Button type="submit" disabled={actionBusy||!canWrite}>{actionBusy?'Création…':'Créer l’action'}</Button></form>}</DialogContent></Dialog>
  {validationMail&&(
   <MayorValidationLaunchModal
    isOpen={Boolean(validationMail)}
    onClose={()=>setValidationMail(null)}
    onLaunch={(newDossier)=>{
     setValidationMail(null);
     toast.success(`Circuit « ${newDossier.title} » initialisé depuis le courriel.`);
     window.location.hash='/workflows';
    }}
   />
  )}
  <SourcePreview api={api} sourceId={source?.id??null} returnFocus={source?.focus??null} onClose={()=>setSource(null)}/>
 </Surface>;
}
