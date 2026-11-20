import {escapeHtml as e,dateLabel,listOf} from './model.js';
import {normalizeMail,renderMailMessage} from './mail.js';
import addressparser from './vendor/nodemailer-addressparser.js';
import {mountMailSplitter} from './mail-splitter.js';

const folders=[['inbox','Boîte de réception'],['drafts','Brouillons'],['sent','Envoyés'],['archive','Archives'],['trash','Corbeille'],['all','Tous les messages']];
const localKey='travaux:mail-drafts:v1';
/** @param {{folder?:string,projectId?:string|null,mailId?:string|null}} options */
export function mailboxDestination({folder='inbox',projectId=null,mailId=null}={}){
  if(!folders.some(([id])=>id===folder))folder='inbox';
  const params=new URLSearchParams({folder});
  // A draft is actor-owned correspondence, not an imported project source.
  if(projectId&&folder!=='drafts')params.set('project',projectId);
  return `#/messagerie${mailId?`/${encodeURIComponent(mailId)}`:''}?${params}`.replace('#/messagerie/','#/mail/');
}
export function readMailboxLocation(hash,search=''){
  const [path,query='']=hash.replace(/^#/,'').split('?'),params=new URLSearchParams(query||search.replace(/^\?/,''));
  const requested=params.get('folder')||'inbox',folder=folders.some(([id])=>id===requested)?requested:'inbox';
  let mailId=null;const match=path.match(/^\/mail\/([^/?]+)/);
  if(match)try{mailId=decodeURIComponent(match[1]);}catch{/* Never pass malformed encoded IDs. */}
  const candidate=params.get('project'),projectId=folder!=='drafts'&&candidate&&candidate.length<=100&&!/[\x00-\x1f\x7f]/.test(candidate)?candidate:null;
  return {folder,projectId,mailId};
}
export function mailFolderLinks(selected='inbox',counts=[]){return folders.map(([id,label])=>{const count=counts.find(item=>item.id===id);return `<a href="#/mail?folder=${id}"${id===selected?' class="selected" aria-current="page"':''}><span>${label}</span>${count?.unread?`<span class="folder-count">${count.unread}</span>`:''}</a>`;}).join('');}
export function parseRecipients(value){
  if(typeof value!=='string'||value.length>4000||/[\r\n\0]/.test(value))throw new Error('Vérifiez les adresses des destinataires.');
  if(!value.trim())return [];
  const recipients=addressparser(value,{flatten:true});
  if(!recipients.length||recipients.length>50||recipients.some(item=>!item.address||!/^[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+$/u.test(item.address)))throw new Error('Une adresse de destinataire est incomplète.');
  return recipients.map(item=>item.address);
}
function localDrafts(){try{return listOf(JSON.parse(localStorage.getItem(localKey)||'[]')).filter(x=>x&&typeof x.id==='string');}catch{return [];}}
function writeDrafts(items){localStorage.setItem(localKey,JSON.stringify(items));}
const field=value=>Array.isArray(value)?value.join(', '):String(value||'');

// Explicit writable fields: a loaded draft also contains readonly server metadata.
export function draftPayload(draft,validate=false){
  const value={subject:field(draft.subject),body:field(draft.body),in_reply_to:draft.in_reply_to||null,mode:draft.mode||'compose'};
  for(const key of ['to','cc','bcc']){try{value[key]=parseRecipients(field(draft[key]));}catch(error){if(validate)throw error;value[key]=field(draft[key]).trim()?[field(draft[key]).trim()]:[];}}
  return value;
}
const draftSignature=value=>JSON.stringify(['to','cc','bcc','subject','body','in_reply_to','mode'].map(key=>field(value[key])));

// One queue drains every edit made during an in-flight request before navigation.
// Keep the first create payload after an ambiguous network failure: replaying that
// same client_id/body acknowledges one creation, then PATCH applies newer text.
export function createDraftSaveQueue({api,getDraft,isDirty,markClean,collect=()=>{},isServer=()=>true,saveLocal=()=>{},onSaved=()=>{}}){
  let running=null;const pendingCreates=new WeakMap();
  async function drain(){
    while(true){
      collect();const current=getDraft();if(!current||!isDirty())return;
      let snapshot=draftSignature(current);const payload=draftPayload(current);
      if(isServer()){
        const creating=current.id.startsWith('local-');
        if(creating&&!pendingCreates.has(current))pendingCreates.set(current,{payload:{...payload,client_id:current.id.slice(6)},signature:snapshot});
        if(creating)snapshot=pendingCreates.get(current).signature;
        const saved=creating?await api.createMailDraft(pendingCreates.get(current).payload):await api.saveMailDraft(current.id,{...payload,expected_revision:current.revision});
        if(typeof saved?.id!=='string'||!saved.id||!Number.isSafeInteger(saved.revision)||saved.revision<1)throw new Error('La sauvegarde du brouillon n’a pas été confirmée. Votre texte est conservé.');
        if(creating&&saved.revision!==1)throw new Error('Ce brouillon a été modifié dans un autre onglet. Votre texte reste ouvert ; rechargez les brouillons avant de choisir la version à conserver.');
        current.id=saved.id;current.revision=saved.revision;pendingCreates.delete(current);
      }else await saveLocal(current);
      collect();if(getDraft()===current&&snapshot===draftSignature(current))markClean();
      onSaved();
    }
  }
  function flush(){collect();if(!running)running=drain().finally(()=>{running=null;});return running;}
  return {flush,get running(){return running;}};
}

export async function mountMailbox(container,{api,projects=[],folder='inbox',mailId=null,projectId=null,publicDemo=false,demo=false,layout='classic',onLayout,onSource,onNavigate,onFolders}={}){
  if(!folders.some(([id])=>id===folder))folder='inbox';
  let disposed=false,listEpoch=0,readerEpoch=0,items=[],selected=null,draft=null,dirty=false,saveTimer=null,search='',offset=0,total=0;
  let serverDrafts=false,canSend=false,canCompose=publicDemo,canManageFlags=false;
  const root=document.createElement('div');root.className=`inbox-workspace${layout==='lovable'?' lovable-mail':''}`;
  root.innerHTML=`<header class="inbox-heading"><h1>Messagerie</h1><div><button class="btn primary" data-inbox="compose">+ Nouveau message</button><button class="btn" data-inbox="refresh" aria-label="Actualiser la messagerie">Actualiser</button></div></header><div class="inbox-status" role="status"></div><div class="inbox-layout"><section class="inbox-list" aria-label="Messages"><form class="inbox-search" role="search"><label class="visually-hidden" for="inbox-search">Rechercher les messages</label><input class="input" id="inbox-search" type="search" name="q" placeholder="Rechercher un message…"><button class="btn" type="submit">Chercher</button></form><div class="inbox-list-title"><h2>${e(folders.find(([id])=>id===folder)[1])}</h2><span data-inbox-total></span></div><div class="inbox-items" role="list"></div><div class="inbox-pagination"></div></section><section class="inbox-reader" aria-label="Message sélectionné"><div class="inbox-empty"><p>Sélectionnez un message pour le lire.</p></div></section></div>`;
  container.replaceChildren(root);
  if(layout==='lovable'){
    const aside=document.createElement('aside');aside.className='inbox-folders';aside.setAttribute('aria-label','Dossiers de la messagerie');
    root.querySelector('.inbox-layout').prepend(aside);onLayout?.({folderTarget:aside});
    const caption=document.createElement('p');caption.className='inbox-caption';caption.textContent=demo?'Boîte de démonstration · Aucun envoi réel':'Vos échanges, dans leur contexte';root.querySelector('.inbox-heading h1').after(caption);
    const title=root.querySelector('.inbox-heading h1');const headingGroup=document.createElement('div');headingGroup.className='inbox-heading-copy';title.before(headingGroup);headingGroup.append(title,caption);
    const connect=document.createElement('a');connect.href='#/connexions';connect.className='btn inbox-connect';connect.textContent='Relier ma messagerie';root.querySelector('.inbox-heading>div:last-child').prepend(connect);
    root.querySelector('.inbox-empty').innerHTML='<div class="inbox-empty-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg></div><h3>Vos échanges, dans leur contexte</h3><p>Sélectionnez une conversation.</p>';
  }
  const reader=root.querySelector('.inbox-reader'),list=root.querySelector('.inbox-items'),status=root.querySelector('.inbox-status');
  const splitter=mountMailSplitter(root.querySelector('.inbox-layout'),{list:root.querySelector('.inbox-list'),reader,preferenceKey:'travaux:mail-list-width:global:v1',breakpoint:layout==='lovable'?950:800});
  function message(text,error=false){if(disposed)return;status.textContent=text;status.classList.toggle('error',error);}
  function persistLocal(current=draft){const previous=localDrafts().filter(item=>item.id!==current.id);writeDrafts([{...current,updated_at:new Date().toISOString()},...previous].slice(0,100));}
  function collectDraft(){const form=reader.querySelector('[data-compose-form]');if(!form||!draft)return;const data=new FormData(form);for(const key of ['to','cc','bcc','subject','body'])draft[key]=String(data.get(key)||'');}
  const saves=createDraftSaveQueue({api,getDraft:()=>draft,isDirty:()=>dirty,markClean:()=>{dirty=false;},collect:collectDraft,isServer:()=>serverDrafts,saveLocal:persistLocal,onSaved:()=>{if(!disposed)message(serverDrafts?'Brouillon enregistré.':'Brouillon enregistré sur cet appareil.');}});
  async function flush(){
    clearTimeout(saveTimer);collectDraft();if(!canCompose&&dirty)throw new Error('Ce compte ne peut pas conserver de brouillon. Votre texte reste ouvert.');
    await saves.flush();
  }
  async function refreshFolders(){try{const data=await api.mailboxFolders();if(disposed)return;serverDrafts=Boolean(data.capabilities?.server_drafts);canSend=Boolean(data.capabilities?.can_send);canCompose=publicDemo||Boolean(data.capabilities?.can_compose);canManageFlags=Boolean(data.capabilities?.can_manage_flags);root.querySelector('[data-inbox="compose"]').hidden=!canCompose;onFolders?.(data.items||[]);}catch(error){root.querySelector('[data-inbox="compose"]').hidden=!canCompose;message(error.message,true);}}
  function renderList(){
    if(disposed)return;
    root.querySelector('[data-inbox-total]').textContent=String(total);
    list.innerHTML=items.length?items.map(item=>{const mail=normalizeMail(item);const isDraft=folder==='drafts';return `<div class="inbox-row${item.read===false?' unread':''}${String(item.id)===String(selected?.id)?' selected':''}" role="listitem">${!isDraft?`<button class="inbox-star"${canManageFlags?'':' disabled'} data-inbox="star" data-id="${e(item.id)}" aria-label="${item.starred?'Retirer des favoris':'Marquer comme favori'}" aria-pressed="${Boolean(item.starred)}">${item.starred?'★':'☆'}</button>`:''}<button class="inbox-message-link" data-inbox="open" data-id="${e(item.id)}"><span class="inbox-row-top"><strong>${e(isDraft?field(item.to)||'Sans destinataire':mail.sender)}</strong><time>${e(dateLabel(item.updated_at||mail.receivedAt))}</time></span><span class="inbox-subject">${e(item.subject||mail.subject)}</span><span class="inbox-preview">${e(mail.preview||String(item.body||'').replace(/\s+/g,' ').slice(0,100))}</span></button></div>`;}).join(''):`<div class="inbox-empty"><p>${folder==='sent'?'Les messages envoyés apparaîtront ici une fois la messagerie connectée.':folder==='drafts'?'Vous n’avez pas de brouillon.':'Aucun message dans ce dossier.'}</p></div>`;
    root.querySelector('.inbox-pagination').innerHTML=folder!=='drafts'&&total>50?`<button class="btn" data-inbox="previous"${offset===0?' disabled':''}>Précédents</button><span>${offset+1}–${Math.min(offset+50,total)} sur ${total}</span><button class="btn" data-inbox="next"${offset+50>=total?' disabled':''}>Suivants</button>`:'';
    if(layout==='lovable'&&folder!=='drafts')for(const button of list.querySelectorAll('[data-inbox="open"]')){
      const item=items.find(value=>value.id===button.dataset.id),references=normalizeMail(item).projectIds.map(id=>projects.find(project=>project.id===id)?.reference).filter(Boolean);
      if(references.length){const tag=document.createElement('span');tag.className='inbox-project-reference';tag.textContent=references.join(' · ');button.append(tag);}
    }
  }
  async function loadList(){const token=++listEpoch;list.setAttribute('aria-busy','true');try{const data=folder==='drafts'?(serverDrafts?await api.mailDrafts():{items:publicDemo?localDrafts():[]}):await api.mailboxMessages({folder,q:search,...(projectId?{project_id:projectId}:{}),limit:'50',offset:String(offset)});if(disposed||token!==listEpoch)return;items=listOf(data.items||data);if(folder==='drafts'&&search)items=items.filter(x=>`${x.subject} ${x.body} ${field(x.to)}`.toLocaleLowerCase('fr').includes(search.toLocaleLowerCase('fr')));total=data.total??items.length;renderList();}catch(error){message(error.message,true);}finally{if(!disposed&&token===listEpoch)list.removeAttribute('aria-busy');}}
  function compose(value={}){
    if(!canCompose)throw new Error('Ce compte ne peut pas rédiger de brouillon.');
    readerEpoch++;reader.removeAttribute('aria-busy');
    draft={id:`local-${crypto.randomUUID()}`,to:'',cc:'',bcc:'',subject:'',body:'',...value};dirty=!value.id&&Boolean(value.in_reply_to||value.subject||value.body);selected=null;
    const extra=field(draft.cc)||field(draft.bcc);
    reader.innerHTML=`<form data-compose-form class="mail-composer"><div class="compose-heading"><h2>${draft.mode==='forward'?'Transfert':draft.in_reply_to?'Réponse':'Nouveau message'}</h2><button class="btn" type="button" data-inbox="close-compose">Fermer</button></div><div class="compose-address"><label for="compose-to">À</label><input class="input" id="compose-to" name="to" value="${e(field(draft.to))}" maxlength="4000" autocomplete="off" placeholder="nom@exemple.fr"><button class="compose-cc-button" data-inbox="extra-recipients" type="button">Cc / Cci</button></div><div class="compose-extra"${extra?'':' hidden'}><label for="compose-cc">Cc</label><input class="input" id="compose-cc" name="cc" value="${e(field(draft.cc))}" maxlength="4000"><label for="compose-bcc">Cci</label><input class="input" id="compose-bcc" name="bcc" value="${e(field(draft.bcc))}" maxlength="4000"></div><label class="visually-hidden" for="compose-subject">Objet</label><input class="input compose-subject" id="compose-subject" name="subject" value="${e(draft.subject)}" placeholder="Objet" maxlength="500"><label class="visually-hidden" for="compose-body">Votre message</label><textarea id="compose-body" name="body" maxlength="50000" placeholder="Votre message…">${e(draft.body)}</textarea><div class="compose-footer"><button class="btn primary" type="submit">${canSend?'Envoyer':'Enregistrer le brouillon'}</button><button class="btn" data-inbox="discard-draft" type="button">Supprimer</button><span>${serverDrafts?'':'Brouillon sur cet appareil'}</span></div><p class="compose-feedback" role="status">${canSend?'':'L’envoi sera disponible après connexion de la messagerie institutionnelle.'}</p></form>`;
    reader.classList.add('has-selection');reader.querySelector('#compose-to').focus({preventScroll:true});
  }
  async function open(id){
    await flush();draft=null;
    if(folder==='drafts'){const item=items.find(x=>x.id===id);if(item)compose(item);return;}
    const token=++readerEpoch;reader.setAttribute('aria-busy','true');
    try{const response=await api.mailMessage(id);if(disposed||token!==readerEpoch)return;const source=response.source||response;if(projectId&&!normalizeMail(source).projectIds.includes(projectId))throw new Error('Ce courriel n’appartient pas au chantier sélectionné. Revenez à tous les chantiers pour le consulter.');selected={...(items.find(x=>x.id===id)||{id}),source};
      reader.innerHTML=`<div class="inbox-message-toolbar"><button class="btn inbox-back" data-inbox="back">Messages</button><div${canCompose?'':' hidden'}><button class="btn" data-inbox="reply">Répondre</button><button class="btn" data-inbox="forward">Transférer</button><button class="btn" data-inbox="launch-validation" style="border-color:#102A4C;color:#102A4C;font-weight:600;margin-left:4px;">Transformer en circuit</button></div><details class="workspace-options"${canManageFlags?'':' hidden'}><summary aria-label="Actions sur le message">···</summary><div><button data-inbox="unread">Marquer non lu</button><button data-inbox="archive">Archiver</button><button data-inbox="trash">Mettre à la corbeille</button><button data-inbox="restore">Déplacer dans la réception</button></div></details></div>${renderMailMessage(source,{idPrefix:'inbox',compact:true,showBack:false})}<div class="inbox-project-links">${normalizeMail(source).projectIds.map(projectId=>`<a class="btn" href="#/project/${encodeURIComponent(projectId)}?view=exchanges&mail=${encodeURIComponent(id)}">Ouvrir le chantier</a>`).join('')}</div>`;
      reader.classList.add('has-selection');
      reader.querySelector('.mail-message-title')?.focus({preventScroll:true});
      if(window.matchMedia('(max-width:800px)').matches)reader.querySelector('.inbox-back')?.scrollIntoView({block:'nearest',behavior:'auto'});
      if(selected.read===false&&canManageFlags){const updated=await api.mailboxFlags(id,{read:true});Object.assign(items.find(x=>x.id===id)||{},updated);if(token===readerEpoch)Object.assign(selected,updated);renderList();refreshFolders();}
    }catch(error){message(error.message,true);}finally{if(!disposed&&token===readerEpoch)reader.removeAttribute('aria-busy');}
  }
  async function flags(id,change){if(!canManageFlags)throw new Error('Ce compte ne peut pas modifier les indicateurs de courrier.');const item=items.find(x=>x.id===id);const updated=await api.mailboxFlags(id,{...change,...(Number.isSafeInteger(item?.mailbox_revision)?{expected_revision:item.mailbox_revision}:{})});Object.assign(item||{},updated);await loadList();refreshFolders();}
  const click=async event=>{const source=event.target.closest('[data-mail-source]');if(source){onSource?.(source.dataset.mailSource);return;}
    const control=event.target.closest('[data-inbox]');if(!control)return;
    try{switch(control.dataset.inbox){
      case 'compose':await flush();compose();break;
      case 'refresh':await flush();await refreshFolders();await loadList();break;
      case 'open':await open(control.dataset.id);break;
      case 'launch-validation':{
        window.dispatchEvent(new CustomEvent('mayortech:launch-validation-from-mail', { detail: { mail: selected?.source || selected } }));
        break;
      }
      case 'star':{const item=items.find(x=>x.id===control.dataset.id);await flags(item.id,{starred:!item.starred});break;}
      case 'archive':case 'trash':case 'restore':await flags(selected.id,{folder:control.dataset.inbox==='restore'?'inbox':control.dataset.inbox});reader.innerHTML='<div class="inbox-empty"><p>Message déplacé.</p></div>';reader.classList.remove('has-selection');break;
      case 'unread':await flags(selected.id,{read:false});break;
      case 'reply':case 'forward':{const mail=normalizeMail(selected.source);const reply=control.dataset.inbox==='reply';const sourceId=selected.id;await flush();compose({to:reply?mail.sender:'',subject:`${reply?'Re':'Tr'} : ${mail.subject.replace(/^(Re|Tr|Fwd)\s*:\s*/i,'')}`,body:`\n\nLe ${dateLabel(mail.receivedAt,true)}, ${mail.sender} :\n${mail.body.split('\n').map(line=>'> '+line).join('\n')}`,in_reply_to:sourceId,mode:reply?'reply':'forward'});break;}
      case 'extra-recipients':reader.querySelector('.compose-extra').hidden=!reader.querySelector('.compose-extra').hidden;break;
      case 'close-compose':await flush();draft=null;reader.innerHTML='<div class="inbox-empty"><p>Brouillon conservé.</p></div>';reader.classList.remove('has-selection');await loadList();refreshFolders();break;
      case 'discard-draft':clearTimeout(saveTimer);if(saves.running)await saves.running;if(serverDrafts&&!draft.id.startsWith('local-'))await api.deleteMailDraft(draft.id);else if(!serverDrafts)writeDrafts(localDrafts().filter(x=>x.id!==draft.id));draft=null;dirty=false;reader.innerHTML='<div class="inbox-empty"><p>Brouillon supprimé.</p></div>';reader.classList.remove('has-selection');await loadList();refreshFolders();break;
      case 'back':reader.classList.remove('has-selection');[...list.querySelectorAll('[data-inbox="open"]')].find(button=>button.dataset.id===selected?.id)?.focus({preventScroll:true});break;
      case 'next':offset+=50;await loadList();break;
      case 'previous':offset=Math.max(0,offset-50);await loadList();break;
    }}catch(error){message(error.message,true);}
  };
  const input=event=>{if(!event.target.closest('[data-compose-form]'))return;collectDraft();dirty=true;clearTimeout(saveTimer);if(!serverDrafts){try{persistLocal();dirty=false;}catch{message('Le brouillon ne peut pas être conservé sur cet appareil. Copiez votre texte avant de quitter.',true);}}else saveTimer=setTimeout(()=>flush().catch(error=>message(error.message,true)),1500);};
  const submit=async event=>{event.preventDefault();if(event.target.matches('.inbox-search')){search=String(new FormData(event.target).get('q')||'');offset=0;await loadList();return;}if(!event.target.matches('[data-compose-form]'))return;
    const feedback=reader.querySelector('.compose-feedback');try{collectDraft();if(canSend){const payload=draftPayload(draft,true);if(!payload.to.length)throw new Error('Ajoutez un destinataire.');await flush();await api.sendMail({draft_id:draft.id,expected_revision:draft.revision});feedback.textContent='Message envoyé.';}else{dirty=true;await flush();feedback.textContent='Brouillon enregistré. La messagerie institutionnelle doit être connectée pour l’envoyer.';}}catch(error){feedback.textContent=error.message;}};
  root.addEventListener('click',click);root.addEventListener('input',input);root.addEventListener('submit',submit);
  await refreshFolders();await loadList();if(mailId)await open(mailId);
  return{flush,get dirty(){return dirty;},destroy(){disposed=true;splitter.destroy();listEpoch++;readerEpoch++;clearTimeout(saveTimer);root.removeEventListener('click',click);root.removeEventListener('input',input);root.removeEventListener('submit',submit);root.remove();}};
}
