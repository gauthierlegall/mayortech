import {escapeHtml as escape} from './model.js';
import {mountMailSplitter} from './mail-splitter.js';

/* Read-only correspondence inside the shared Travaux workspace.
 * The only mutation is an explicit source-to-project assignment through api.assign.
 * No HTML email, remote media, compose/send action, credential or endpoint setting.
 */
const preferences = new WeakMap();
let instanceSequence = 0;
const paths = {
  mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
  back:'<path d="M20 12H4m6-6-6 6 6 6"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  attachment:'<path d="m8 13 6-6a3 3 0 0 1 4 4l-8 8a5 5 0 0 1-7-7l8-8a7 7 0 0 1 10 10l-8 8"/>',
  file:'<path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6"/>',
  project:'<path d="M4 21V8l8-5 8 5v13M2 21h20M9 21v-5h6v5M8 10h1m6 0h1M8 13h1m6 0h1"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  warning:'<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v.5"/>',
  refresh:'<path d="M20 7V3l-4 1M4 17v4l4-1M20 7a9 9 0 0 0-16 1m0 9a9 9 0 0 0 16-1"/>',
};
const icon = name=>`<svg class="mail-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
const text = value=>typeof value==='string' ? value : typeof value==='number' ? String(value) : '';
const array = value=>Array.isArray(value) ? value : [];
const projectName = project=>text(project?.name || project?.title || project?.reference) || 'Chantier sans nom';
const projectLink = id=>`#/project/${encodeURIComponent(id)}`;
const mailLink = id=>`#/mail/${encodeURIComponent(id)}`;
const responseSource = payload=>payload?.source || payload;

function address(value) {
  if (Array.isArray(value)) return value.map(address).filter(Boolean).join(', ');
  if (typeof value==='object' && value) {
    const name=text(value.name || value.display_name);
    const email=text(value.address || value.email);
    return name && email ? `${name} <${email}>` : name || email;
  }
  return text(value);
}

function formatDate(value, compact=false) {
  if (!value) return 'Date non renseignée';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return text(value) || 'Date non renseignée';
  return new Intl.DateTimeFormat('fr-FR', compact
    ? {day:'numeric',month:'short'}
    : {day:'numeric',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(date);
}

export function normalizeMail(source={}) {
  const metadata = source.metadata && typeof source.metadata==='object' ? source.metadata : {};
  const projectIds = [...new Set([...array(source.project_ids), source.project_id].filter(value=>value!==null && value!==undefined && text(value)).map(String))];
  const relatives = array(source.related_sources || source.relative_sources || metadata.related_sources);
  const attachments = array(metadata.attachments || source.attachments).map((item,index)=>{
    const attachment = typeof item==='string' ? {filename:item} : item || {};
    const filename = text(attachment.filename || attachment.name) || `Pièce jointe ${index+1}`;
    const related = relatives.find(relative=>text(relative.filename || relative.metadata?.filename || relative.name)===filename);
    return {
      filename,
      status:text(attachment.status || related?.status),
      sourceId:text(attachment.source_id || related?.source_id || related?.id),
      sha256:text(attachment.raw_sha256 || attachment.sha256),
    };
  });
  // Some APIs expose extracted attachments only as related sources.
  for (const related of relatives) {
    if (related.kind==='email' || related.id===source.id || related.source_id===source.id) continue;
    const filename=text(related.filename || related.metadata?.filename || related.name);
    if (filename && !attachments.some(item=>item.filename===filename)) attachments.push({filename,status:text(related.status),sourceId:text(related.source_id || related.id),sha256:''});
  }
  return {
    id:text(source.id || source.source_id),
    subject:text(source.subject || metadata.subject) || 'Sans objet',
    sender:address(source.sender || source.from || metadata.sender || metadata.from) || 'Expéditeur non renseigné',
    to:address(source.to || source.recipients || metadata.to),
    receivedAt:text(source.received_at || source.sent_at || metadata.received_at || source.created_at),
    body:text(source.body ?? source.text ?? source.content),
    preview:text(source.preview || source.snippet || source.body || source.text).replace(/\s+/g,' ').slice(0,170),
    projectIds,
    matchStatus:text(source.match_status || metadata.match_status) || (projectIds.length ? 'matched' : 'unmatched'),
    attachments,
    raw:source,
  };
}

export function normalizeMailList(payload) {
  const items = Array.isArray(payload) ? payload : array(payload?.items || payload?.sources);
  const totalKnown=Number.isSafeInteger(payload?.total) && payload.total>=0;
  return {items:items.map(normalizeMail),total:totalKnown ? payload.total : items.length,totalKnown};
}

function matchLabel(mail) {
  if (mail.matchStatus==='ambiguous') return {label:'Chantier à départager',tone:'attention'};
  if (mail.matchStatus==='unmatched' || !mail.projectIds.length) return {label:'À rattacher',tone:'attention'};
  if (['matched','manual','manually_assigned','assigned'].includes(mail.matchStatus)) return {label:'Rattaché',tone:'linked'};
  return {label:'Rattachement à vérifier',tone:'attention'};
}

function attachmentStatus(status, sourceId) {
  const labels = {extracted:'Texte extrait',processed:'Traité',pending:'Extraction en attente',queued:'Extraction en attente',failed:'Extraction en échec',error:'Extraction en échec',unsupported:'Format non pris en charge',blocked:'Pièce bloquée',encrypted:'Pièce chiffrée',empty:'Aucun texte extrait'};
  return labels[status] || (sourceId ? 'Ouvrir le détail de la pièce' : 'Texte non disponible');
}

export function renderMailMessage(source, {idPrefix='mail',showBack=true,compact=false}={}) {
  const mail = normalizeMail(source);
  const match = matchLabel(mail);
  return `<article class="mail-message" aria-labelledby="${escape(idPrefix)}-message-title">
    ${showBack?`<button type="button" class="mail-back mail-mobile-only" data-mail-action="back">${icon('back')}Tous les courriers</button>`:''}
    ${compact?'':`<div class="mail-message-kicker"><span class="mail-tag ${match.tone}">${escape(match.label)}</span><span>Lecture seule</span></div>`}
    <h2 id="${escape(idPrefix)}-message-title" class="mail-message-title" tabindex="-1">${escape(mail.subject)}</h2>
    <dl class="mail-envelope"><div><dt>De</dt><dd>${escape(mail.sender)}</dd></div>${mail.to?`<div><dt>À</dt><dd>${escape(mail.to)}</dd></div>`:''}<div><dt>Reçu le</dt><dd>${escape(formatDate(mail.receivedAt))}</dd></div></dl>
    ${mail.attachments.length?`<section class="mail-attachments" aria-label="Pièces jointes"><h3>${icon('attachment')}${mail.attachments.length} pièce${mail.attachments.length>1?'s jointes':' jointe'}</h3><ul>${mail.attachments.map(item=>`<li>${item.sourceId?`<button type="button" class="mail-attachment" data-mail-source="${escape(item.sourceId)}" data-mail-filename="${escape(item.filename)}">${icon('file')}<span><strong>${escape(item.filename)}</strong><small>${escape(attachmentStatus(item.status,item.sourceId))}</small></span>${icon('arrow')}</button>`:`<div class="mail-attachment unavailable">${icon('file')}<span><strong>${escape(item.filename)}</strong><small>${escape(attachmentStatus(item.status,item.sourceId))}</small></span></div>`}</li>`).join('')}</ul></section>`:''}
    <section class="mail-body-section" aria-label="Contenu du courrier">${mail.body?`<div class="mail-body">${escape(mail.body)}</div>`:'<p class="mail-body-empty">Le texte de ce message n’est pas disponible dans cet espace.</p>'}</section>
    ${compact?'':'<p class="mail-source-footnote">Contenu affiché en texte brut. Les images et liens distants du message ne sont pas chargés.</p>'}
  </article>`;
}

/**
 * Mounts within the existing Travaux shell; does not own account/navigation chrome.
 * Required API: mail(filters,{signal}), mailMessage(id,{signal}).
 * Optional API: source(id,{signal}), assign(sourceId,projectId).
 * onNavigate receives a shared-workspace hash URL, not an external app URL.
 */
export function mountMailView(container, {api,projects=[],mailId=null,onNavigate,onUnauthorized,demo=false,initialFilters,onFiltersChange,contextual=false}={}) {
  if (!container?.replaceChildren || !api) throw new TypeError('Un conteneur et le client API sont nécessaires.');
  const uid=`travaux-mail-${++instanceSequence}`;
  const projectItems=Array.isArray(projects) ? projects : array(projects?.items || projects?.projects);
  const remembered=contextual?{}:preferences.get(api) || {};
  let listScrollY=remembered.documentScrollTop || 0;
  let listScrollTop=remembered.scrollTop || 0;
  let messageScrollY=0;
  const state={filters:{q:'',project_id:'',match_status:'',...(initialFilters || remembered.filters)},items:[],total:0,totalKnown:false,selectedId:mailId ? String(mailId) : null,message:null,listLoading:false,messageLoading:false,listError:null,messageError:null,assignmentError:'',assignmentSuccess:'',assigning:false,assignmentOpen:false,evidence:null,evidenceError:'',evidenceLoading:false,evidenceTitle:'',evidenceSourceId:'',destroyed:false};
  const lifetime=new AbortController();
  const requests={list:null,message:null,evidence:null};
  const epochs={list:0,message:0,evidence:0};
  const root=document.createElement('section');
  root.className='mail-workspace'+(contextual?' mail-contextual':'');
  root.setAttribute('aria-label','Courriers des chantiers');
  root.innerHTML=`<header class="mail-heading"><div><span class="mail-eyebrow">Espace de travail</span><h2>Messages des chantiers</h2><p>Les messages disponibles dans cet espace, reliés à vos chantiers.</p></div><div class="mail-heading-meta"><span class="mail-tag">Lecture seule</span>${demo?'<span class="mail-tag">Données fictives</span>':''}<button type="button" class="mail-button mail-icon-button" data-mail-action="refresh" aria-label="Actualiser les courriers">${icon('refresh')}</button></div></header>
    <form class="mail-filterbar" data-mail-form="search" role="search" aria-label="Rechercher les courriers"><div class="mail-search"><label for="${uid}-search">Rechercher dans les messages</label><div class="mail-search-field">${icon('search')}<input id="${uid}-search" name="q" type="search" value="${escape(state.filters.q)}" placeholder="Objet, expéditeur, texte…" autocomplete="off"><button type="submit" class="mail-button">Rechercher</button></div></div><div class="mail-filter"><label for="${uid}-project">Chantier</label><select id="${uid}-project" name="project_id"><option value="">Tous les chantiers</option>${projectItems.map(project=>`<option value="${escape(project.id)}"${String(project.id)===state.filters.project_id?' selected':''}>${escape(project.reference ? `${project.reference} · ${projectName(project)}` : projectName(project))}</option>`).join('')}</select></div><div class="mail-filter"><label for="${uid}-match">Rattachement</label><select id="${uid}-match" name="match_status">${[['','Tous les courriers'],['matched','Rattachés'],['unmatched','Sans chantier'],['ambiguous','À départager']].map(([value,label])=>`<option value="${value}"${value===state.filters.match_status?' selected':''}>${label}</option>`).join('')}</select></div></form>
    <p class="mail-live" role="status" aria-live="polite" data-mail-live></p><div class="mail-layout"><section class="mail-list-pane" aria-label="Liste des courriers"></section><section class="mail-message-pane" aria-label="Courrier sélectionné"></section><aside class="mail-context-pane" aria-label="Contexte du courrier"></aside></div>`;
  container.replaceChildren(root);
  const listPane=root.querySelector('.mail-list-pane');
  const messagePane=root.querySelector('.mail-message-pane');
  const splitter=mountMailSplitter(root.querySelector('.mail-layout'),{list:listPane,reader:messagePane,preferenceKey:'travaux:mail-list-width:project:v1',breakpoint:760});
  const contextPane=root.querySelector('.mail-context-pane');
  const live=root.querySelector('[data-mail-live]');
  const searchForm=root.querySelector('[data-mail-form="search"]');

  function remember() {
    if(!state.selectedId){listScrollY=window.scrollY;listScrollTop=listPane.scrollTop;}
    if(!contextual)preferences.set(api,{filters:{...state.filters},scrollTop:listScrollTop,documentScrollTop:listScrollY});
    onFiltersChange?.({...state.filters});
  }
  function navigate(href) {
    if (onNavigate) onNavigate(href);
    else if (typeof location!=='undefined') location.hash=href;
  }
  function errorText(error) {
    if (error?.status===401) {onUnauthorized?.();return 'Votre session a expiré. Reconnectez-vous pour consulter les courriers.';}
    if (error?.status===403) return 'Vous n’avez pas accès à ce courrier ou à ce périmètre.';
    if (error?.status===404) return 'Ce courrier n’est plus disponible dans cet espace.';
    return text(error?.message) || 'Les messages ne peuvent pas être chargés. Réessayez.';
  }
  function startRequest(kind) {
    requests[kind]?.abort();
    const controller=new AbortController();
    requests[kind]=controller;
    const epoch=++epochs[kind];
    return {signal:controller.signal,current:()=>!state.destroyed && !controller.signal.aborted && epochs[kind]===epoch};
  }
  function syncLayout() {
    root.dataset.selected=String(Boolean(state.selectedId));
    root.dataset.evidence=String(Boolean(state.evidenceSourceId));
  }
  function restoreListPosition() {
    listPane.scrollTop=listScrollTop;
    if(window.matchMedia('(max-width:760px)').matches)requestAnimationFrame(()=>{if(!state.destroyed && !state.selectedId)window.scrollTo({top:listScrollY,behavior:'auto'});});
  }
  function focusMessage() {
    if(window.matchMedia('(max-width:760px)').matches)messagePane.querySelector('.mail-back')?.scrollIntoView({block:'start',behavior:'auto'});
    messagePane.querySelector('.mail-message-title')?.focus({preventScroll:true});
  }
  function emptyMarkup(title,description,symbol='mail',action='') {
    return `<div class="mail-empty">${icon(symbol)}<h2>${escape(title)}</h2><p>${escape(description)}</p>${action}</div>`;
  }
  function renderList() {
    listPane.setAttribute('aria-busy',String(state.listLoading));
    if (state.listLoading && !state.items.length) {listPane.innerHTML='<div class="mail-list-heading">Chargement des courriers…</div><div class="mail-loading-lines" aria-hidden="true"><span></span><span></span><span></span></div>';return;}
    if (state.listError) {listPane.innerHTML=emptyMarkup('Courriers indisponibles',state.listError,'warning',`<button type="button" class="mail-button" data-mail-action="retry-list">Réessayer</button>`);return;}
    const total=state.totalKnown?state.total:state.items.length;
    const filtered=Boolean(state.filters.q || state.filters.project_id || state.filters.match_status);
    if (!state.items.length) {listPane.innerHTML=emptyMarkup(filtered?'Aucun courrier ne correspond':'Aucun courrier disponible',filtered?'Essayez un autre mot ou élargissez les filtres.':'Les messages autorisés apparaîtront ici après leur récupération ou leur import.','mail',filtered?'<button type="button" class="mail-button" data-mail-action="clear-filters">Effacer les filtres</button>':'');return;}
    listPane.innerHTML=`<div class="mail-list-heading"><span>${escape(total)} courrier${total>1?'s':''}${state.totalKnown?'':' affichés'}</span>${state.listLoading?'<span>Actualisation…</span>':''}</div><ul class="mail-list">${state.items.map(mail=>{
      const selected=mail.id===state.selectedId;
      const match=matchLabel(mail);
      const project=projectItems.find(item=>mail.projectIds.includes(String(item.id)));
      return `<li><a class="mail-list-item${selected?' selected':''}" href="${escape(mailLink(mail.id))}" data-mail-id="${escape(mail.id)}"${selected?' aria-current="true"':''}><div class="mail-item-top"><span class="mail-item-sender">${escape(mail.sender)}</span><time datetime="${escape(mail.receivedAt)}">${escape(formatDate(mail.receivedAt,true))}</time></div><h3>${escape(mail.subject)}</h3>${mail.preview?`<p class="mail-item-preview">${escape(mail.preview)}</p>`:''}<div class="mail-item-bottom">${project?`<span class="mail-item-project">${escape(project.reference || projectName(project))}${mail.projectIds.length>1?` +${mail.projectIds.length-1}`:''}</span>`:`<span class="mail-tag ${match.tone}">${escape(match.label)}</span>`}${mail.attachments.length?`<span class="mail-attachment-count">${icon('attachment')}<span>${mail.attachments.length}<span class="mail-sr-only"> pièce${mail.attachments.length>1?'s jointes':' jointe'}</span></span></span>`:''}</div></a></li>`;
    }).join('')}</ul>`;
  }
  function renderMessage() {
    syncLayout();
    messagePane.setAttribute('aria-busy',String(state.messageLoading));
    if (!state.selectedId) {messagePane.innerHTML=emptyMarkup('Les échanges, dans leur contexte','Choisissez un courrier pour lire son contenu et retrouver son chantier.');return;}
    if (state.messageLoading) {messagePane.innerHTML=`<button type="button" class="mail-back mail-mobile-only" data-mail-action="back">${icon('back')}Tous les courriers</button><p class="mail-loading-copy">Chargement du message…</p><div class="mail-loading-lines" aria-hidden="true"><span></span><span></span><span></span></div>`;return;}
    if (state.messageError) {messagePane.innerHTML=`<button type="button" class="mail-back" data-mail-action="back">${icon('back')}Tous les courriers</button>${emptyMarkup('Message indisponible',state.messageError,'warning','<button type="button" class="mail-button" data-mail-action="retry-message">Réessayer</button>')}`;return;}
    messagePane.innerHTML=renderMailMessage(state.message?.raw || {},{idPrefix:uid,compact:contextual});
  }
  function renderContext() {
    syncLayout();
    contextPane.hidden=!state.message || Boolean(state.messageError) || state.messageLoading;
    if (contextPane.hidden) {contextPane.replaceChildren();return;}
    const mail=state.message;
    const linkedProjects=projectItems.filter(project=>mail.projectIds.includes(String(project.id)));
    const unresolved=mail.projectIds.filter(id=>!linkedProjects.some(project=>String(project.id)===id));
    contextPane.innerHTML=`<section class="mail-project-context"><span class="mail-eyebrow">Dans le même espace</span><h2>Chantier${mail.projectIds.length>1?'s':''} lié${mail.projectIds.length>1?'s':''}</h2>${linkedProjects.map(project=>`<a class="mail-project-card" href="${escape(projectLink(project.id))}" data-mail-project="${escape(project.id)}">${icon('project')}<span><small>${escape(project.reference || 'Chantier')}</small><strong>${escape(projectName(project))}</strong><span>Ouvrir le chantier ${icon('arrow')}</span></span></a>`).join('')}${unresolved.length?'<p class="mail-context-copy">Le détail de certains chantiers liés n’est pas disponible dans votre périmètre actuel.</p>':''}${!mail.projectIds.length?'<p class="mail-context-copy">Ce courrier n’est pas encore rattaché à un chantier.</p>':''}${state.assignmentSuccess?`<p class="mail-feedback success" role="status">${icon('check')}${escape(state.assignmentSuccess)}</p>`:''}${typeof api.assign==='function'&&projectItems.length ? (state.assignmentOpen || !mail.projectIds.length ? `<form data-mail-form="assignment" class="mail-assignment"><label for="${uid}-assignment">${mail.projectIds.length?'Affecter à un autre chantier':'Choisir le chantier'}</label><select id="${uid}-assignment" name="project_id" required${state.assigning?' disabled':''}><option value="">Sélectionner un chantier</option>${projectItems.map(project=>`<option value="${escape(project.id)}">${escape(project.reference ? `${project.reference} · ${projectName(project)}` : projectName(project))}</option>`).join('')}</select><p>Ce rattachement concerne le courrier et ses pièces traitées.</p><button type="submit" class="mail-button primary"${state.assigning?' disabled':''}>${state.assigning?'Rattachement…':'Rattacher au chantier'}</button>${mail.projectIds.length?'<button type="button" class="mail-button quiet" data-mail-action="cancel-assignment">Annuler</button>':''}${state.assignmentError?`<p class="mail-feedback error" role="alert">${escape(state.assignmentError)}</p>`:''}</form>` : '<button type="button" class="mail-button quiet" data-mail-action="change-assignment">Modifier le rattachement</button>') : !mail.projectIds.length?'<p class="mail-context-copy">Le rattachement nécessite un accès autorisé et une liste de chantiers disponible.</p>':''}<div class="mail-context-note"><h3>Le message reste une source</h3><p>Son rattachement ne valide pas automatiquement les informations qu’il contient. Retrouvez les propositions dans le chantier.</p></div></section>${state.evidenceSourceId?`<section class="mail-evidence" aria-labelledby="${uid}-evidence-title"><button type="button" class="mail-back" data-mail-action="close-evidence">${icon('back')}Revenir au courrier</button><span class="mail-eyebrow">Pièce jointe · texte extrait</span><h3 id="${uid}-evidence-title" tabindex="-1">${escape(state.evidenceTitle || 'Pièce jointe')}</h3>${state.evidenceLoading?'<p class="mail-loading-copy" role="status">Chargement du texte extrait…</p>':state.evidenceError?`<p class="mail-feedback error" role="alert">${escape(state.evidenceError)}</p><button type="button" class="mail-button" data-mail-action="retry-evidence">Réessayer</button>`:`<div class="mail-evidence-body">${escape(text(state.evidence?.body || state.evidence?.text || state.evidence?.content) || 'Aucun texte extrait disponible pour cette pièce.')}</div><p class="mail-source-footnote">Le texte extrait peut être incomplet. Il ne remplace pas l’original pour une vérification exhaustive.</p>`}</section>`:''}`;
  }
  async function loadList({restoreScroll=false}={}) {
    const request=startRequest('list');
    state.listLoading=true;state.listError=null;renderList();
    try {
      if (typeof api.mail!=='function') throw new Error('La lecture des courriers n’est pas disponible dans cette version du serveur.');
      const result=normalizeMailList(await api.mail({...state.filters},{signal:request.signal}));
      if (!request.current()) return;
      state.items=result.items;state.total=result.total;state.totalKnown=result.totalKnown;
      live.textContent=`${result.total} courrier${result.total>1?'s':''} disponible${result.total>1?'s':''}${state.filters.q?' pour cette recherche':''}.`;
    } catch(error) {if (!request.current()) return;state.listError=errorText(error);live.textContent='La liste des courriers n’a pas pu être chargée.';}
    finally {if(request.current()){state.listLoading=false;renderList();if(restoreScroll && !state.selectedId)restoreListPosition();}}
  }
  async function loadMessage(id,{focus=false}={}) {
    const request=startRequest('message');
    requests.evidence?.abort();++epochs.evidence;
    state.selectedId=id ? String(id) : null;state.message=null;state.messageError=null;state.evidenceSourceId='';state.evidence=null;state.assignmentError='';state.assignmentSuccess='';state.assignmentOpen=false;
    state.messageLoading=Boolean(id);renderList();renderMessage();renderContext();
    if (!id) {restoreListPosition();return;}
    try {
      if (typeof api.mailMessage!=='function') throw new Error('La lecture de ce courrier n’est pas disponible dans cette version du serveur.');
      const source=responseSource(await api.mailMessage(String(id),{signal:request.signal}));
      if (!request.current()) return;
      state.message=normalizeMail(source || {});
    } catch(error) {if (!request.current()) return;state.messageError=errorText(error);}
    finally {if(request.current()){state.messageLoading=false;renderMessage();renderContext();if(focus)focusMessage();}}
  }
  async function openEvidence(sourceId,title) {
    const request=startRequest('evidence');
    if(!state.evidenceSourceId)messageScrollY=window.scrollY;
    state.evidenceSourceId=sourceId;state.evidenceTitle=title;state.evidence=null;state.evidenceError='';state.evidenceLoading=true;renderContext();
    try {
      if (typeof api.source!=='function') throw new Error('Le texte de cette pièce n’est pas accessible dans cette version.');
      const source=responseSource(await api.source(sourceId,{signal:request.signal}));
      if (!request.current()) return;
      state.evidence=source;
    } catch(error) {if (!request.current()) return;state.evidenceError=errorText(error);}
    finally {if(request.current()){state.evidenceLoading=false;renderContext();if(window.matchMedia('(max-width:760px)').matches)contextPane.querySelector('.mail-evidence')?.scrollIntoView({block:'start',behavior:'auto'});contextPane.querySelector('.mail-evidence h3')?.focus({preventScroll:true});}}
  }
  function closeEvidence() {
    const sourceId=state.evidenceSourceId;
    requests.evidence?.abort();++epochs.evidence;
    state.evidenceSourceId='';state.evidence=null;state.evidenceError='';renderContext();
    [...messagePane.querySelectorAll('[data-mail-source]')].find(button=>button.dataset.mailSource===sourceId)?.focus({preventScroll:true});
    if(window.matchMedia('(max-width:760px)').matches)requestAnimationFrame(()=>{if(!state.destroyed && !state.evidenceSourceId)window.scrollTo({top:messageScrollY,behavior:'auto'});});
  }
  async function assign(form) {
    const projectId=new FormData(form).get('project_id');
    if (!projectId || state.assigning || !state.message) return;
    const selectedId=state.selectedId;
    state.assigning=true;state.assignmentError='';renderContext();
    try {
      await api.assign(selectedId,String(projectId));
      if (state.destroyed || state.selectedId!==selectedId) return;
      await Promise.all([loadList(),loadMessage(selectedId)]);
      if (state.destroyed || state.selectedId!==selectedId) return;
      state.assignmentSuccess='Courrier rattaché. Les informations restent à vérifier dans le chantier.';
      live.textContent='Le rattachement du courrier a été enregistré.';
    } catch(error) {if(!state.destroyed && state.selectedId===selectedId)state.assignmentError=errorText(error);}
    finally {state.assigning=false;if(!state.destroyed && state.selectedId===selectedId)renderContext();}
  }
  function filtersFromForm() {
    const values=new FormData(searchForm);
    state.filters={q:String(values.get('q') || '').trim(),project_id:String(values.get('project_id') || ''),match_status:String(values.get('match_status') || '')};
    remember();loadList();
  }
  root.addEventListener('submit',event=>{
    const form=event.target.closest('form');
    if (!form || !root.contains(form)) return;
    event.preventDefault();
    if (form.dataset.mailForm==='search') filtersFromForm();
    if (form.dataset.mailForm==='assignment') assign(form);
  },{signal:lifetime.signal});
  root.addEventListener('change',event=>{
    if (searchForm.contains(event.target) && event.target.tagName==='SELECT') filtersFromForm();
  },{signal:lifetime.signal});
  root.addEventListener('click',event=>{
    if (event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const project=event.target.closest('[data-mail-project]');
    if(project){event.preventDefault();remember();navigate(projectLink(project.dataset.mailProject));return;}
    const item=event.target.closest('[data-mail-id]');
    if(item){event.preventDefault();remember();const id=item.dataset.mailId;loadMessage(id,{focus:true});navigate(mailLink(id));return;}
    const attachment=event.target.closest('[data-mail-source]');
    if(attachment){openEvidence(attachment.dataset.mailSource,attachment.dataset.mailFilename);return;}
    const action=event.target.closest('[data-mail-action]')?.dataset.mailAction;
    if (!action) return;
    if(action==='back'){remember();loadMessage(null);navigate('#/mail');}
    if(action==='refresh'){loadList();if(state.selectedId)loadMessage(state.selectedId);}
    if(action==='retry-list')loadList();
    if(action==='retry-message')loadMessage(state.selectedId,{focus:true});
    if(action==='change-assignment'){state.assignmentOpen=true;state.assignmentSuccess='';renderContext();contextPane.querySelector('select')?.focus();}
    if(action==='cancel-assignment'){state.assignmentOpen=false;state.assignmentError='';renderContext();contextPane.querySelector('[data-mail-action="change-assignment"]')?.focus();}
    if(action==='close-evidence')closeEvidence();
    if(action==='retry-evidence')openEvidence(state.evidenceSourceId,state.evidenceTitle);
    if(action==='clear-filters'){state.filters={q:'',project_id:contextual?initialFilters.project_id:'',match_status:''};searchForm.reset();searchForm.elements.q.value='';searchForm.elements.project_id.value=state.filters.project_id;searchForm.elements.match_status.value='';remember();loadList();}
  },{signal:lifetime.signal});
  root.addEventListener('keydown',event=>{if(event.key==='Escape' && state.evidenceSourceId){event.preventDefault();closeEvidence();}},{signal:lifetime.signal});
  renderMessage();renderContext();loadList({restoreScroll:true});if(state.selectedId)loadMessage(state.selectedId,{focus:true});
  return {
    destroy(){remember();state.destroyed=true;splitter.destroy();lifetime.abort();for(const request of Object.values(requests))request?.abort();root.remove();},
    setMailId(id){if(String(id || '')!==String(state.selectedId || ''))return loadMessage(id,{focus:true});},
    refresh(){return Promise.all([loadList(),state.selectedId?loadMessage(state.selectedId):Promise.resolve()]);},
  };
}

export const mount=mountMailView;
