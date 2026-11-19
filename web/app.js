import {api, ApiError} from './api.js';
import {mountMailView} from './mail.js';
import {mountNativePage} from './native.js';
import {mountMailbox,mailFolderLinks} from './mailbox.js';
import {mountSettings,settingsMarkup} from './settings.js';
import {applyAppearance} from './appearance.js';
import {actionInputs,workspaceView,fileSize} from './workspace-model.js';
import {escapeHtml as e, safeUrl, statusLabel, statusTone, displayValue, dateLabel, canApprove, listOf, projectTitle, projectPendingCount, prioritizeProjects, filterProjects} from './model.js';

const paths = {
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  building:'<path d="M4 21V8l8-5 8 5v13M2 21h20M9 21v-5h6v5M8 10h1m6 0h1M8 13h1m6 0h1"/>',
  review:'<rect x="4" y="4" width="16" height="17" rx="2"/><path d="M9 4V2h6v2M8 10h8m-8 4h5m-5 4h3"/>',
  inbox:'<path d="M4 4h16l2 13v3H2v-3L4 4Z"/><path d="M2 15h6l2 3h4l2-3h6M12 6v6m-3-3 3 3 3-3"/>',
  document:'<path d="M14 2H5v20h14V7l-5-5Z"/><path d="M14 2v6h5M8 12h8m-8 4h8"/>',
  settings:'<path d="m9 3-1 3-3 1 1 3-2 2 2 2-1 3 3 1 1 3h6l1-3 3-1-1-3 2-2-2-2 1-3-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',
  arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>', chevron:'<path d="m9 5 7 7-7 7"/>',
  external:'<path d="M14 3h7v7m0-7L10 14M10 3H3v18h18v-7"/>',
  plus:'<path d="M12 5v14M5 12h14"/>', check:'<path d="m5 12 4 4L19 6"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>', search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18m-14 4h3m4 0h3m-10 4h3"/>',
  pin:'<path d="M19 10c0 6-7 11-7 11S5 16 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  shield:'<path d="m12 2 8 3v6c0 6-8 11-8 11S4 17 4 11V5l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  refresh:'<path d="M20 7V3l-4 1M4 17v4l4-1M20 7a9 9 0 0 0-16 1m0 9a9 9 0 0 0 16-1"/>',
  warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3v.5"/>',
  mail:'<rect x="2" y="5" width="20" height="15" rx="2"/><path d="m2 7 10 7L22 7"/>',
  link:'<path d="m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 1 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  note:'<path d="M4 3h16v12l-6 6H4V3Z"/><path d="M14 21v-6h6M8 8h8m-8 4h5"/>',
  logout:'<path d="M9 3H3v18h6m5-15 6 6-6 6M8 12h12"/>',
  folder:'<path d="M3 5h7l2 3h9v12H3V5Z"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.5"/>',
  table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
  kanban:'<rect x="3" y="4" width="5" height="12" rx="1"/><rect x="10" y="4" width="5" height="16" rx="1"/><rect x="17" y="4" width="4" height="9" rx="1"/>',
};
const icon = name=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name]||paths.document}</svg>`;
const badge = status=>`<span class="badge ${statusTone(status)}">${e(statusLabel(status))}</span>`;
const projectHref = id=>`#/project/${encodeURIComponent(id)}`;
const summaryHref = id=>`#/summary/${encodeURIComponent(id)}`;
const state = {session:null,bootstrap:{},projects:[],reviews:[],summaries:[],current:null,projectTab:'page',selectedReview:null,importFile:null,summaryDirty:false,summaryDrafts:{},noteDrafts:{},routeToken:0,renderEpoch:0};
let dialogReturnFocus = null;
applyAppearance();
let activeSettings=null;
let activeNative = null, activeMail = null, nativeDirty = false, lastStableHash = location.hash || '#/overview';
async function preserveNativePage(){if(activeNative?.dirty)await activeNative.flush();if(activeMail?.dirty)await activeMail.flush();}
function clearWorkspace(){activeNative?.destroy();activeNative=null;nativeDirty=false;activeMail?.destroy();activeMail=null;activeSettings?.destroy();activeSettings=null;}
const mobileNavigation=window.matchMedia('(max-width:800px)');
let navigationOpen=false;
function setNavigationOpen(open,{focus=false}={}) {
  const sidebar=document.querySelector('.sidebar'),menu=document.querySelector('.menu-toggle');
  if(!sidebar||!menu)return;
  const wasInside=sidebar.contains(document.activeElement);
  navigationOpen=mobileNavigation.matches&&Boolean(open);
  sidebar.classList.toggle('open',navigationOpen);
  document.querySelector('.mobile-overlay')?.classList.toggle('open',navigationOpen);
  sidebar.inert=mobileNavigation.matches&&!navigationOpen;
  if(sidebar.inert)sidebar.setAttribute('aria-hidden','true');else sidebar.removeAttribute('aria-hidden');
  document.querySelector('.main-shell').inert=navigationOpen;
  document.querySelector('.mobile-nav').inert=navigationOpen;
  menu.setAttribute('aria-expanded',String(navigationOpen));
  menu.setAttribute('aria-label',navigationOpen?'Fermer la navigation':'Ouvrir la navigation');
  if(navigationOpen&&focus)sidebar.querySelector('button,a')?.focus();
  else if(mobileNavigation.matches&&!navigationOpen&&(focus||wasInside))menu.focus();
  else if(!mobileNavigation.matches&&document.activeElement===menu)sidebar.querySelector('[aria-current="page"],a')?.focus();
}
function hasUnsavedNotes(){return Object.values(state.noteDrafts).some(draft=>String(draft.body||'').trim());}
mobileNavigation.addEventListener('change',()=>setNavigationOpen(false));
function startRender(section,id=null){
  const parts=(location.hash||'#/overview').replace(/^#\/?/,'').split('?')[0].split('/');
  if(parts[0]!==section || (id!==null && decodeURIComponent(parts[1]||'')!==String(id)))return null;
  return ++state.renderEpoch;
}
function currentRender(token){return token!==null&&token===state.renderEpoch;}


function toast(message, error=false) {
  const element=document.createElement('div'); element.className=`toast${error?' error':''}`; element.setAttribute('role',error?'alert':'status');
  element.innerHTML=`${icon(error?'warning':'check')}<span>${e(message)}</span><button type="button" aria-label="Fermer la notification">${icon('close')}</button>`;
  element.querySelector('button').addEventListener('click',()=>element.remove());
  document.getElementById('notifications').append(element); setTimeout(()=>element.remove(),error?12000:6500);
}
function nativeSettings(){return state.bootstrap.capabilities?.native_editor || {};}
function nativeUrl(){return '';}
function nativeButton(project=null,label='Ouvrir la page'){
  return project?`<button class="btn" data-action="project-tab" data-tab="page" data-id="${e(project.id)}">${icon('note')}${e(label)}</button>`:'<a class="btn" href="#/projects">Ouvrir les chantiers</a>';
}
function heading(title,subtitle='',actions='',editorial=false) {
  return `<header class="page-heading"><div><h1${editorial?' class="editorial-heading"':''}>${e(title)}</h1>${subtitle?`<p>${e(subtitle)}</p>`:''}</div>${actions?`<div class="heading-actions">${actions}</div>`:''}</header>`;
}
function shell(content,active='overview',breadcrumb='Mon espace') {
  clearWorkspace();
  const demo=state.session?.demo ?? state.bootstrap.demo ?? false;
  const actor=state.session?.actor; const actorName=typeof actor==='string'?actor:actor?.name||actor?.display_name||'Responsable travaux';
  const nav=[['mail','mail','Messagerie'],['review','review','À vérifier']];
  const count=state.bootstrap.stats?.pending_reviews ?? 0;
  const projects=prioritizeProjects(state.projects);
  const currentId=location.hash.startsWith('#/project/')?state.current?.id:null;
  document.getElementById('app').innerHTML=`<div class="app-shell workspace-shell">
    <button class="mobile-overlay" data-action="close-menu" aria-label="Fermer la navigation"></button>
    <aside class="sidebar" id="primary-navigation" aria-label="Navigation principale">
      <button class="sidebar-close icon-button" data-action="close-menu" aria-label="Fermer la navigation">${icon('close')}</button>
      <a class="brand" href="#/overview"><span class="brand-symbol">${icon('building')}</span><span class="brand-name">Travaux</span></a>
      <nav class="nav-group">${nav.map(([route,symbol,label])=>`<a class="nav-link${active===route?' active':''}" href="#/${route}"${active===route?' aria-current="page"':''}>${icon(symbol)}<span>${label}</span>${route==='review'&&count?`<span class="nav-count">${e(count)}</span>`:''}</a>`).join('')}</nav>
      ${active==='mail'?'<nav class="mail-folder-navigation" aria-label="Dossiers de la messagerie" id="mail-folders">'+mailFolderLinks(new URLSearchParams(location.hash.split('?')[1]||'').get('folder')||'inbox')+'</nav>':''}
      <div class="sidebar-projects-heading"><a href="#/projects">Chantiers <span>${projects.length}</span></a><button class="icon-button" data-action="create-project" aria-label="Créer un chantier">${icon('plus')}</button></div>
      <nav class="project-navigation" aria-label="Mes chantiers">${projects.map(project=>`<a class="project-nav-link${currentId===project.id?' active':''}" href="${projectHref(project.id)}"${currentId===project.id?' aria-current="page"':''}><span class="project-nav-mark">${icon('note')}</span><span>${e(projectTitle(project))}</span>${projectPendingCount(project)?'<span class="project-nav-update" aria-label="Informations à vérifier"></span>':''}</a>`).join('')||'<a class="project-nav-link" href="#/projects">Créer mon premier chantier</a>'}</nav>
      <nav class="nav-group nav-secondary"><a class="nav-link${active==='summaries'?' active':''}" href="#/summaries">${icon('document')}<span>Récapitulatifs</span></a></nav>
      <div class="sidebar-bottom"><a class="nav-link${active==='settings'?' active':''}" href="#/settings">${icon('settings')}<span>Paramètres</span></a><div class="account">${demo?'<span class="demo-caption">Démo · données fictives</span>':`<span>${e(actorName)}</span><button class="logout" data-action="logout" aria-label="Se déconnecter">${icon('logout')}</button>`}</div></div>
    </aside>
    <div class="main-shell"><header class="topbar"><button class="menu-toggle" data-action="open-menu" aria-label="Ouvrir la navigation" aria-controls="primary-navigation" aria-expanded="false">${icon('menu')}</button><div class="breadcrumbs"><a href="#/projects">${active==='projects'?'Chantiers':e(breadcrumb)}</a></div></header><main class="content" id="main" tabindex="-1">${content}</main></div>
    <nav class="mobile-nav" aria-label="Navigation rapide">${[['projects','building','Chantiers'],['mail','mail','Courriels'],['review','review','À vérifier'],['summaries','document','Récaps']].map(([route,symbol,label])=>`<a href="#/${route}"${active===route?' class="active" aria-current="page"':''}>${icon(symbol)}<span>${label}</span></a>`).join('')}</nav>
  </div>`;
  setNavigationOpen(false); document.title=`${breadcrumb} — Travaux`;
}
function loading(active,breadcrumb) {
  shell(`<div aria-busy="true" aria-label="Chargement"><div class="skeleton skeleton-title"></div><div class="panel">${[1,2,3].map(()=>'<div class="skeleton-row"><div class="skeleton wide"></div><div class="skeleton short"></div></div>').join('')}</div><p class="loading-copy" role="status">Chargement des informations…</p></div>`,active,breadcrumb);
}
function empty(title,message,symbol='folder',action='') { return `<div class="empty-state">${icon(symbol)}<h2>${e(title)}</h2><p>${e(message)}</p>${action?`<div class="button-row">${action}</div>`:''}</div>`; }
function errorScreen(error,active,breadcrumb) {
  if(error.status===401){renderLogin();return;}
  const recovery=error.status===404?'<a class="btn primary" href="#/projects">Retour aux chantiers</a>':'<button class="btn primary" data-action="retry">Réessayer</button>';
  shell(heading('Informations indisponibles','La page n’a pas pu être chargée.')+`<div class="panel">${empty(error.status===403?'Accès non autorisé':error.status===404?'Dossier introuvable':'Impossible de charger cette page',error.message,'warning',recovery)}</div>`,active,breadcrumb);
}
function projectRow(project) {
  const pending=projectPendingCount(project);
  return `<a class="project-row" href="${projectHref(project.id)}"><span class="project-symbol">${icon(project.category==='voirie'?'pin':'building')}</span><div class="project-row-content"><div class="project-reference">${e(project.reference||project.code||'Dossier travaux')}</div><h3>${e(projectTitle(project))}</h3>${project.progress?`<p class="project-progress"><span class="progress-state">Avancement confirmé</span>${e(project.progress)}</p>`:''}<div class="row-meta">${project.location?`<span class="meta-pair">${icon('pin')}${e(project.location)}</span>`:''}<span class="meta-pair">${icon('clock')}${e(dateLabel(project.updated_at||project.last_updated||project.created_at))}</span></div></div><div class="project-row-end">${badge(project.status||'active')}${pending?`<span class="badge warning">${e(pending)} à vérifier</span>`:''}<span class="project-open">Ouvrir ${icon('chevron')}</span></div></a>`;
}
function projectActions(project) { return listOf(project.actions||[]); }
function reviewTitle(review) { return review.title || review.label || review.field_label || fieldLabel(review.field||review.kind||review.predicate) || 'Information à confirmer'; }
function fieldLabel(field) {
  const labels={delivery_date:'Date de livraison',acceptance_date:'Date de réception',deadline:'Échéance',deadline_date:'Échéance',budget:'Montant',budget_raw:'Budget annoncé',amount:'Montant',progress:'Avancement',status:'État du chantier',action:'Action proposée',task:'Action proposée',contractor:'Entreprise',location:'Localisation',summary:'Information reçue'};
  if(String(field||'').startsWith('action.'))return 'Action proposée';
  return labels[field]||String(field||'Information à confirmer').replaceAll('_',' ');
}
function reviewValue(review) { return review.proposed_value ?? review.value ?? review.value_text ?? review.text ?? review.claim ?? ''; }
function reviewQuote(review) { return review.quote || review.evidence?.[0]?.quote || review.evidence?.quote || review.citations?.[0]?.quote || review.source_quote || ''; }
function sourceId(record) { return record.source_id || record.evidence?.[0]?.source_id || record.evidence?.source_id || record.citations?.[0]?.source_id || record.source?.id; }
function sourceControl(id,label='Ouvrir la source') { return id?`<button class="source-button" data-action="source" data-id="${e(id)}">${e(label)}</button>`:'<span class="subtle-copy">Source non renseignée</span>'; }

async function renderOverview() {
  const renderToken=startRender('activity');if(renderToken===null)return;
  const [projectData,reviewData]=await Promise.all([api.projects(),api.reviews()]);
  if(!currentRender(renderToken))return;state.projects=listOf(projectData); state.reviews=listOf(reviewData);
  const pending=state.reviews.filter(x=>!['accepted','rejected','corrected'].includes(x.status));
  const details=await Promise.all(state.projects.slice(0,12).map(async p=>{try{return await api.project(p.id);}catch{return p;}}));
  const actions=details.flatMap(p=>projectActions(p).map(a=>({...a,title:a.title||a.value,project_name:projectTitle(p),project_id:p.id}))).filter(a=>!['done','completed','cancelled'].includes(a.status));
  const dated=actions.filter(a=>a.due_date||a.deadline||a.due_at).sort((a,b)=>String(a.due_date||a.deadline||a.due_at).localeCompare(String(b.due_date||b.deadline||b.due_at))).slice(0,4);
  const recent=prioritizeProjects(state.projects).slice(0,6);
  const updated=state.bootstrap.last_sync_at || state.bootstrap.sync?.last_success_at;
  const banner=pending.length?`<div class="attention-banner"><span class="attention-icon">${icon('review')}</span><div><h2>${pending.length} information${pending.length>1?'s':''} à vérifier</h2><p>Des changements attendent votre lecture et votre confirmation.</p></div><a class="btn" href="#/review">Consulter ${icon('arrow')}</a></div>`:`<div class="notice neutral">${icon('check')}Aucune proposition en attente. Les nouvelles informations apparaîtront ici après import.</div>`;
  if(!currentRender(renderToken))return;
  shell(heading('Le point sur les travaux.','Vos chantiers, les dernières informations et les décisions à prendre.',`<a class="btn" href="#/imports">${icon('inbox')}Importer un mail</a>`,true)+`
  <div class="metrics-line"><div class="metric"><strong>${state.projects.length}</strong><span>chantiers suivis</span></div><div class="metric"><strong>${pending.length}</strong><span>à vérifier</span></div><div class="metric"><strong>${actions.length}</strong><span>actions ouvertes</span></div></div>
  <div class="overview-layout"><div>${banner}<section class="activity-list"><div class="section-title"><h2>Les changements à relire</h2></div>${pending.slice(0,3).map(r=>{const p=state.projects.find(p=>p.id===r.project_id);return `<a class="activity-item" href="#/review/${encodeURIComponent(r.id)}">${icon(r.status==='contradiction'?'warning':'mail')}<div><p class="activity-project">${e(r.project_name||projectTitle(p))}${p?.reference?` · ${e(p.reference)}`:''}</p><p class="activity-proposal">Proposition · ${e(reviewTitle(r))}</p><p class="activity-value">${e(displayValue(reviewValue(r)))}</p><small>${e(dateLabel(r.created_at,true))} · À confirmer</small></div>${icon('chevron')}</a>`;}).join('')||'<p class="subtle-copy">Les informations nouvelles sont toujours soumises à votre vérification.</p>'}</section><section><div class="section-title"><h2>Les chantiers suivis</h2><a href="#/projects">Voir tous les chantiers</a></div><div class="project-list">${recent.length?recent.map(projectRow).join(''):empty('Aucun chantier pour le moment','Importez un premier mail pour proposer son rattachement à un chantier.','building','<a class="btn primary" href="#/imports">Importer un mail</a>')}</div></section></div>
  <aside class="side-column"><section class="side-section"><h2>Les prochaines échéances</h2>${dated.length?`<ol class="timeline-list">${dated.map(a=>`<li><p class="event-title">${e(a.title||a.description||'Action à traiter')}</p><p class="event-meta">${e(dateLabel(a.due_date||a.deadline||a.due_at))}<br><a href="${projectHref(a.project_id)}">${e(a.project_name)}</a></p></li>`).join('')}</ol>`:'<p class="subtle-copy">Aucune échéance confirmée à afficher. Les dates proposées restent dans la revue.</p>'}</section>
  <section class="side-section sync-note"><h3>${icon('shield')}Vos sources, vos décisions</h3><p>La mémoire des chantiers conserve les preuves. Une proposition de l’IA reste à vérifier jusqu’à votre décision.</p><a href="#/settings">Voir les connexions ${icon('arrow')}</a></section>
  <section class="side-section"><h2>Dernière synchronisation</h2><p class="subtle-copy">${updated?e(dateLabel(updated,true)):'Aucune connexion Exchange active n’est présumée.'}</p><a class="source-button" href="#/imports">Consulter les imports</a></section></aside></div>`,'activity','Les évolutions');
}

async function renderProjects() {
  const renderToken=startRender('projects');if(renderToken===null)return;
  const projectsResponse=await api.projects();if(!currentRender(renderToken))return;state.projects=prioritizeProjects(listOf(projectsResponse));
  if(!currentRender(renderToken))return;
  shell(heading('Chantiers','Un état vérifié, des actions et une mémoire pour chaque opération.',`<button class="btn primary" data-action="create-project">${icon('plus')}Créer un chantier</button>${nativeButton()}`)+`
  <div class="filters"><div class="search-box">${icon('search')}<label class="visually-hidden" for="project-search">Rechercher un chantier</label><input class="input" id="project-search" type="search" placeholder="Nom, référence ou localisation…"></div><label class="visually-hidden" for="project-status">État des chantiers</label><select id="project-status"><option value="">Tous les états</option><option value="active">En cours</option><option value="planned">En préparation</option><option value="completed">Terminés</option></select><span class="subtle-copy" id="project-result-count" role="status" aria-live="polite" aria-atomic="true">${state.projects.length} chantier${state.projects.length>1?'s':''}</span></div><div class="project-list" id="project-results">${state.projects.length?state.projects.map(projectRow).join(''):empty('Aucun chantier suivi','Importez un mail pour commencer.','building','<a class="btn primary" href="#/imports">Importer un mail</a>')}</div>`,'projects','Chantiers');
}
function applyProjectFilters() {
  const term=document.getElementById('project-search')?.value.toLocaleLowerCase('fr').trim()||'';
  const status=document.getElementById('project-status')?.value||'';
  const results=filterProjects(state.projects,{term,status});
  document.getElementById('project-result-count').textContent=`${results.length} chantier${results.length>1?'s':''}`;
  document.getElementById('project-results').innerHTML=results.length?results.map(projectRow).join(''):empty('Aucun chantier correspondant','Modifiez votre recherche ou choisissez tous les états.','search');
}

async function renderProject(id) {
  const renderToken=startRender('project',id);if(renderToken===null)return;
  const [response,projectList]=await Promise.all([api.project(id),api.projects()]);if(!currentRender(renderToken))return;state.projects=listOf(projectList); const project=response.project?{...response.project,...response}:response; state.current=project; state.current.id=id;
  state.projectTab=workspaceView(new URLSearchParams(location.hash.split('?')[1]||'').get('view')||'kanban');
  const notes=listOf(project.human_notes||project.notes||project.observations||[]);
  const facts=listOf(project.facts||project.confirmed_facts||[]);
  const sources=listOf(project.sources||[]);
  const actions=projectActions(project);
  const summaries=listOf(project.summaries||[]);
  const pending=project.pending_reviews ?? project.pending_count ?? listOf(project.pending||project.reviews||project.candidates||[]).filter(x=>['proposed','pending'].includes(x.status)).length;
  const memory=project.memory?.content || project.memory?.summary || project.memory_text || project.memory_summary || (typeof project.memory==='string'?project.memory:'');
  const tabs=[['page','Page du chantier'],['memory','Mémoire du chantier'],['actions',`Actions (${actions.length})`],['sources',`Sources (${sources.length})`],['notes',`Notes humaines (${notes.length})`]];
  let body='';
  if(['page','table','kanban'].includes(state.projectTab))body='<div class="native-document-panel" id="native-document"></div>';
  if(state.projectTab==='memory') body=`<div class="panel"><div class="panel-heading"><h2>L’état vérifié</h2>${badge(project.status||'active')}</div><div class="panel-body">${memory?`<p class="memory-text">${e(memory)}</p>`:''}${facts.length?`<dl class="facts-grid${memory?' spaced':''}">${facts.map(f=>`<div class="fact"><dt>${e(f.label||fieldLabel(f.field||f.key||f.predicate))}</dt><dd>${e(displayValue(f.value??f.value_text??f.text))}${f.status?badge(f.status):''}<span class="fact-source">${sourceControl(sourceId(f),f.source_title||'Voir la preuve')}</span></dd></div>`).join('')}</dl>`:!memory?'<p class="subtle-copy">Aucun fait confirmé pour ce chantier. Consultez les propositions pour construire sa mémoire.</p>':''}</div></div>
    <div class="panel"><div class="panel-heading"><h2>Les récapitulatifs</h2><button class="btn small" data-action="generate-dialog" data-id="${e(id)}">${icon('plus')}Préparer un récap</button></div>${summaries.length?summaryTable(summaries):empty('Aucun récapitulatif','Préparez une première synthèse à partir des faits et décisions de ce chantier.','document')}</div>`;
  if(state.projectTab==='actions') body=`<div class="panel"><div class="panel-heading"><h2>Actions du chantier</h2></div>${actions.length?actionTable(actions):empty('Aucune action confirmée','Les actions explicites des mails seront proposées dans la revue.','review')}</div>`;
  if(state.projectTab==='sources') body=`<div class="panel"><div class="panel-heading"><h2>Mails et pièces sources</h2></div>${sources.length?`<div class="table-wrap" tabindex="0" aria-label="Sources du chantier, tableau défilant"><table><thead><tr><th>Source</th><th>Reçue le</th><th>Traitement</th><th>Preuve</th></tr></thead><tbody>${sources.map(s=>`<tr><td><strong>${e(s.subject||s.title||s.filename||'Document source')}</strong><div class="table-meta">${e(s.sender||s.from_address||s.kind||'Mail')}</div></td><td>${e(dateLabel(s.received_at||s.created_at,true))}</td><td>${badge(s.status||'imported')}</td><td>${sourceControl(s.id)}</td></tr>`).join('')}</tbody></table></div>`:empty('Aucune source rattachée','Les originaux autorisés et leurs extraits seront accessibles ici.','mail')}</div>`;
  if(state.projectTab==='notes') body=`<div class="panel"><div class="panel-heading"><h2>Notes humaines</h2><span class="badge neutral">Conservées dans la mémoire</span></div><div class="panel-body">${notes.length?notes.map(n=>`<article class="note"><div class="note-header"><span class="note-author">${e(n.author||n.actor_name||n.actor||n.actor_id||'Saisie humaine')}</span><time>${e(dateLabel(n.created_at||n.observed_at,true))}</time></div><p>${e(n.body||n.content||n.text||n.value_text||'')}</p><small class="subtle-copy">${e(n.origin==='appflowy'?'Saisie native AppFlowy':'Note ajoutée au dossier')}</small></article>`).join(''):'<p class="subtle-copy">Aucune note. Ajoutez un constat terrain : il gardera sa provenance humaine.</p>'}
    <form data-form="note" data-id="${e(id)}" class="note-form"><div class="form-field"><label for="note-body">Ajouter un constat ou une précision</label><textarea id="note-body" name="body" required maxlength="20000" aria-describedby="note-help note-draft-state" placeholder="Ex. : visite de chantier ce matin, accès piéton maintenu…">${e(state.noteDrafts[id]?.body||'')}</textarea><p class="help-text" id="note-help">La note enrichit la mémoire ; elle ne remplace pas une preuve documentaire.</p><p class="help-text" id="note-draft-state" role="status">${state.noteDrafts[id]?.body?'Brouillon non enregistré. Conservé pendant votre navigation dans cet espace.':''}</p></div><div class="form-error" role="alert" hidden></div><button class="btn primary" type="submit">${icon('plus')}Ajouter la note</button></form></div></div>`;
  if(!currentRender(renderToken))return;
  if(state.projectTab==='documents') {
    const response=await api.documents(id); if(!currentRender(renderToken))return;
    const files=listOf(response.items||response.documents||response).filter(file=>!['mail','email','eml'].includes(file.kind));
    body=`<div class="documents-header"><div><h2>Documents du chantier</h2><p>Les pièces, leur origine et leur fichier original lorsqu'il est disponible.</p></div>${state.bootstrap.access?.mail_import===false?'':`<a class="btn" href="#/imports">${icon('plus')}Importer un courriel</a>`}</div>${files.length?`<div class="document-list">${files.map(file=>`<article class="document-item"><span class="document-file-icon">${icon('document')}</span><div class="document-item-content"><h3>${e(file.filename||file.title||'Pièce jointe')}</h3><p>${e(fileSize(file.size))} · ${file.available?'Original conservé':'Extrait conservé, original indisponible'}</p>${file.created_at?`<time>${e(dateLabel(file.created_at,true))}</time>`:''}</div><div class="document-item-actions">${file.text_available?sourceControl(file.preview_source_id||file.source_id,'Lire l’extrait'):'<span class="subtle-copy">Texte non extrait</span>'}${file.available&&file.id?`<a class="btn small" href="/api/v1/documents/${encodeURIComponent(file.id)}/download" download>${icon('download')}Original</a>`:''}${file.parent_source_id?`<a class="btn small" href="#/mail/${encodeURIComponent(file.parent_source_id)}">${icon('mail')}Courriel</a>`:''}</div></article>`).join('')}</div>`:empty('Les pièces de ce chantier apparaîtront ici','Importez un courriel avec un devis, un plan ou un compte rendu. Le fichier restera relié à son échange.','document','<a class="btn primary" href="#/imports">Importer un courriel</a>')}`;
  }
  if(state.projectTab==='exchanges')body='<div id="project-mail-workspace"></div>';
  const actionView=['table','kanban'].includes(state.projectTab)?state.projectTab:'kanban';
  const views=[['page','note','Notes'],[actionView,'kanban','Actions'],['documents','folder','Documents'],['exchanges','mail','Courriels']];
  const repere=facts.filter(f=>!String(f.field).startsWith('action.')).slice(0,3);
  shell(`<section class="project-workspace"><header class="workspace-heading"><div class="workspace-title"><h1>${e(projectTitle(project))}</h1></div><div class="workspace-heading-actions"><details class="workspace-options"><summary aria-label="Options du chantier">···</summary><div><button data-action="generate-dialog" data-id="${e(id)}">Préparer un récapitulatif</button><a href="${projectHref(id)}?view=memory">Mémoire et informations</a><a href="${projectHref(id)}?view=sources">Sources du chantier</a></div></details></div></header>
    <div class="workspace-viewbar"><nav class="workspace-views" role="tablist" aria-label="Vues du chantier">${views.map(([value,symbol,label])=>`<a class="workspace-view${state.projectTab===value?' selected':''}" role="tab" id="tab-${value}" aria-selected="${state.projectTab===value}" tabindex="${state.projectTab===value||(!views.some(([v])=>v===state.projectTab)&&value==='page')?0:-1}" aria-controls="project-tab-content" href="${projectHref(id)}?view=${value}">${icon(symbol)}${label}</a>`).join('')}</nav><a class="workspace-review-link" href="#/review?project=${encodeURIComponent(id)}">${pending?`<span class="review-dot"></span>${e(pending)} à vérifier`:'État vérifié'}</a></div>
    <section id="project-tab-content" role="tabpanel" aria-labelledby="tab-${views.some(([v])=>v===state.projectTab)?state.projectTab:'page'}" class="workspace-canvas ${['table','kanban'].includes(state.projectTab)?'workspace-data-canvas':''}">${body}</section></section>`,'projects',projectTitle(project));
  if(['page','table','kanban'].includes(state.projectTab)){
    const controller=await mountNativePage(document.getElementById('native-document'),{api,project,view:state.projectTab,actions:actionInputs(actions),onDirty:dirty=>{nativeDirty=dirty;},onSaved:()=>refreshBootstrap()});
    if(!currentRender(renderToken)){controller?.destroy();return;}
    activeNative=controller;
  } else if(state.projectTab==='exchanges') {
    activeMail=mountMailView(document.getElementById('project-mail-workspace'),{api,projects:state.projects,contextual:true,initialFilters:{project_id:id},mailId:new URLSearchParams(location.hash.split('?')[1]||'').get('mail'),demo:state.session?.demo,onNavigate:href=>{location.hash=href.startsWith('#/mail')?`${projectHref(id)}?view=exchanges${href.startsWith('#/mail/')?'&mail='+encodeURIComponent(decodeURIComponent(href.slice(7))):''}`:href;},onUnauthorized:renderLogin});
  }
}

async function renderWorkspace(){
  state.projects=listOf(await api.projects());
  const preferred=prioritizeProjects(state.projects).find(project=>project.status==='active')||state.projects[0];
  if(!preferred)return renderProjects();
  state.projectTab='page';history.replaceState(null,'',projectHref(preferred.id));
  await renderProject(preferred.id);
}

function actionTable(actions) { return `<div class="table-wrap"><table class="mobile-records"><thead><tr><th>Action</th><th>Responsable</th><th>Échéance confirmée</th><th>État</th></tr></thead><tbody>${actions.map(a=>`<tr><td data-label="Action"><strong>${e(a.title||a.description||a.body||a.value||'Action à préciser')}</strong>${sourceId(a)?`<div class="table-meta">${sourceControl(sourceId(a))}</div>`:''}</td><td data-label="Responsable">${e(a.assignee||a.owner||a.responsible||'À attribuer')}</td><td data-label="Échéance confirmée">${e(dateLabel(a.due_date||a.deadline||a.due_at))}</td><td data-label="État">${badge(a.status||'open')}</td></tr>`).join('')}</tbody></table></div>`; }

async function renderReview(id=null) {
  const renderToken=startRender('review');if(renderToken===null)return;
  const filter=new URLSearchParams(location.hash.split('?')[1]||'').get('project');
  const reviewsResponse=await api.reviews(filter);if(!currentRender(renderToken))return;state.reviews=listOf(reviewsResponse);
  const pending=state.reviews.filter(r=>!['accepted','rejected','corrected','superseded'].includes(r.status));
  state.selectedReview=pending.find(r=>String(r.id)===String(id||state.selectedReview?.id))||pending[0]||null;
  const selected=state.selectedReview;
  const hasConflict=Boolean(selected?.conflict_with?.length||selected?.previous_values?.length||selected?.contradiction);
  if(selected){try{selected.project_revision=(await api.project(selected.project_id)).revision;}catch{}}
  if(!currentRender(renderToken))return;
  shell(heading('À vérifier','Lisez la preuve, puis confirmez, corrigez ou écartez la proposition.',`<a class="btn" href="#/imports">${icon('inbox')}Importer un mail</a>`)+(!selected?`<div class="panel">${empty('Tout est à jour','Aucune proposition n’attend de décision. Les nouveaux mails enrichiront cette file de revue.','check',`<a class="btn" href="#/projects">Voir les chantiers</a>`)}</div>`:`
  <div class="review-layout"><ul class="review-list" aria-label="Propositions à vérifier">${pending.map(r=>`<li><button class="review-item${r.id===selected.id?' selected':''}" data-action="select-review" data-id="${e(r.id)}"${r.id===selected.id?' aria-current="true"':''}><span class="review-item-title">${e(reviewTitle(r))}</span><span class="review-item-meta">${badge(r.conflict_with?.length?'contradiction':r.status||'proposed')}<span>${e(r.project_name||'Dossier travaux')}</span></span></button></li>`).join('')}</ul>
  <article class="review-detail panel"><div class="panel-body"><div class="review-intro"><h2>${e(reviewTitle(selected))}</h2>${badge(hasConflict?'contradiction':selected.status||'proposed')}</div><p class="subtle-copy">${selected.project_id?`<a href="${projectHref(selected.project_id)}">${e(selected.project_name||'Ouvrir le chantier')}</a>`:'Le chantier doit encore être précisé.'} · ${e(dateLabel(selected.created_at,true))}</p>
  ${hasConflict?`<div class="notice danger">${icon('warning')}Une information diffère de l’état confirmé. Comparez les deux annonces avant de retenir la nouvelle.</div><div class="previous-values"><h3>Informations précédemment confirmées</h3>${listOf(selected.previous_values||[]).map(previous=>`<div class="previous-value"><strong>${e(displayValue(previous.value))}</strong><p>${e(reviewQuote(previous))}</p>${sourceControl(sourceId(previous),'Consulter la preuve précédente')}</div>`).join('')}</div>`:''}
  <div class="review-value"><span>Valeur proposée</span><strong>${e(displayValue(reviewValue(selected)))}</strong></div>${selected.reason||selected.explanation?`<p class="subtle-copy">${e(selected.reason||selected.explanation)}</p>`:''}
  <div class="evidence-label">${icon('mail')}Extrait de la source</div>${reviewQuote(selected)?`<blockquote class="evidence-quote">${e(reviewQuote(selected))}</blockquote>`:'<div class="notice">Aucun extrait probant n’est disponible. Ouvrez la source ou écartez cette proposition.</div>'}<div class="space-top-small">${sourceControl(sourceId(selected),selected.source_title||'Ouvrir le mail source')}</div>
  <div class="review-actions"><button class="btn primary" data-action="${hasConflict?'replace-review':'accept-review'}" data-id="${e(selected.id)}"${!sourceId(selected)&&!reviewQuote(selected)?' disabled':''}>${icon('check')}${hasConflict?'Remplacer la valeur précédente':'Confirmer'}</button><button class="btn" data-action="correct-review" data-id="${e(selected.id)}">Corriger</button><button class="btn danger" data-action="reject-review" data-id="${e(selected.id)}">Écarter</button></div><p class="help-text">La décision est conservée avec la proposition et sa provenance.</p></div></article></div>`),'review','À vérifier');
}

async function renderImports() {
  if(state.session?.public_demo){shell(heading('Ajouter des courriels')+'<p class="settings-note">La démonstration utilise des messages fictifs. Les courriels de la mairie pourront être ajoutés dans son espace privé après raccordement de la messagerie.</p><a class="btn" href="#/mail">Ouvrir la messagerie</a>','mail','Messagerie');return;}
  const renderToken=startRender('imports');if(renderToken===null)return;
  let imports=[],jobs=[],importError='';
  try {const response=await api.imports();imports=listOf(response,'sources');jobs=listOf(response.jobs||[]);}catch(error){if(error.status===401)throw error;importError=error.message;}
  const demo=state.session?.demo??state.bootstrap.demo;
  if(!currentRender(renderToken))return;
  shell(heading('Imports de messagerie','Ajoutez un mail puis confirmez son chantier et ses informations.',demo?`<button class="btn" data-action="next-mail">${icon('plus')}Ajouter le mail fictif suivant</button>`:'')+`
  ${demo?'<div class="notice neutral">Démonstration locale : uniquement des mails entièrement fictifs. Aucune boîte de mairie n’est connectée par cette interface.</div>':''}
  <div class="two-col"><section class="panel"><div class="panel-heading"><h2>Importer un mail EML</h2></div><div class="panel-body"><form data-form="import"><div class="import-drop">${icon('inbox')}<h3>Choisir un fichier de messagerie</h3><p>Format .eml, 2 Mo maximum. Le traitement utilise le service configuré.</p><label class="visually-hidden" for="eml-file">Fichier EML à importer</label><input id="eml-file" name="file" type="file" accept=".eml,message/rfc822" required></div><div class="import-preview" id="import-preview" hidden><div class="form-field"><label for="eml-preview">Aperçu du texte EML</label><textarea id="eml-preview" readonly></textarea></div></div><div class="form-error" role="alert" hidden></div><div class="button-row space-top"><button class="btn primary" type="submit">${icon('inbox')}Importer et analyser</button><span class="help-text">Aucun envoi de courriel.</span></div><div id="import-result"></div></form></div></section>
  <aside><div class="panel"><div class="panel-heading"><h2>Du mail à la mémoire</h2></div><div class="panel-body"><ol class="timeline-list"><li><p class="event-title">Lire la source autorisée</p><p class="event-meta">Mail et pièces selon les capacités réellement activées.</p></li><li><p class="event-title">Proposer les changements</p><p class="event-meta">Faits et actions gardent leur provenance.</p></li><li><p class="event-title">Vous laisser confirmer</p><p class="event-meta">La mémoire validée reste distincte des propositions.</p></li></ol></div></div><div class="sync-note space-top"><h3>${icon('settings')}Exchange institutionnel</h3><p>La DSI prépare le serveur et le périmètre en lecture seule. Aucun mot de passe de messagerie n’est demandé ici.</p><a href="#/settings">Voir le connecteur ${icon('arrow')}</a></div></aside></div>
  <section class="section-spaced"><div class="section-title"><h2>Les mails reçus</h2></div>${importError?`<div class="notice danger">${e(importError)}</div>`:''}<div class="panel">${imports.length?`<div class="table-wrap"><table class="mobile-records"><thead><tr><th>Source</th><th>Date</th><th>Traitement</th><th>Consulter</th></tr></thead><tbody>${imports.map(item=>`<tr><td data-label="Source"><strong>${e(item.subject||item.filename||'Mail importé')}</strong><div class="table-meta">${e(item.sender||'')}</div></td><td data-label="Reçu le">${e(dateLabel(item.received_at||item.created_at,true))}</td><td data-label="Traitement">${badge(item.match_status==='matched'?item.status||'ready':item.match_status||'needs_match')}${item.metadata?.attachments?.some(a=>a.status==='not_extracted')?'<div class="table-meta">Pièce jointe non extraite</div>':''}</td><td data-label="Consulter"><button class="btn small" data-action="source" data-id="${e(item.id)}">${icon('mail')}${item.match_status!=='matched'?'Choisir le chantier':'Ouvrir le mail'}</button></td></tr>`).join('')}</tbody></table></div>`:empty('Aucun import à afficher','Choisissez un fichier EML pour commencer.','inbox')}</div></section>
  ${jobs.length?`<section class="section-spaced"><div class="section-title"><h2>Traitements</h2></div><div class="panel"><div class="table-wrap"><table class="mobile-records"><thead><tr><th>Traitement</th><th>État</th><th>Résultat</th></tr></thead><tbody>${jobs.slice(-12).reverse().map(job=>`<tr><td data-label="Traitement">Analyse d’une source<div class="table-meta">${e(dateLabel(job.created_at,true))}</div></td><td data-label="État">${badge(job.status)}</td><td data-label="Résultat">${e(job.error||job.last_error||'')}${job.status==='failed'?`<button class="btn small" data-action="retry-job" data-id="${e(job.id)}">Relancer le traitement</button>`:''}</td></tr>`).join('')}</tbody></table></div></div></section>`:''}`,'imports','Imports');
}

function summaryTable(summaries) { return `<div class="table-wrap"><table class="mobile-records"><thead><tr><th>Récapitulatif</th><th>Créé le</th><th>État</th><th>Version</th></tr></thead><tbody>${summaries.map(s=>`<tr><td data-label="Récapitulatif"><a class="table-title" href="${summaryHref(s.id)}">${e(s.title||s.project_name||'Récapitulatif de chantier')}</a><div class="table-meta">${s.stale?'Le chantier a évolué depuis cette version.':'Synthèse de la mémoire du chantier'}</div></td><td data-label="Créé le">${e(dateLabel(s.created_at,true))}</td><td data-label="État">${badge(s.status||'draft')}</td><td data-label="Version">${e(s.version||s.version_number||'1')}</td></tr>`).join('')}</tbody></table></div>`; }
async function renderSummaries() {
  const renderToken=startRender('summaries');if(renderToken===null)return;
  const summariesResponse=await api.summaries();if(!currentRender(renderToken))return;state.summaries=listOf(summariesResponse);
  if(!currentRender(renderToken))return;
  shell(heading('Récapitulatifs','Des synthèses relues, sourcées et identifiées par version.',`<button class="btn primary" data-action="generate-dialog">${icon('plus')}Préparer un récap</button>`)+`<div class="panel">${state.summaries.length?summaryTable(state.summaries):empty('Aucun récapitulatif','Choisissez un chantier pour préparer une synthèse de ses informations confirmées.','document','<button class="btn primary" data-action="generate-dialog">Préparer un récap</button>')}</div>`,'summaries','Récapitulatifs');
}
async function renderSummary(id) {
  const renderToken=startRender('summary',id);if(renderToken===null)return;
  const response=await api.summary(id);if(!currentRender(renderToken))return; const summary=response.summary?{...response.summary,...response}:response; state.current=summary; state.current.id=id; state.summaryDirty=Boolean(state.summaryDrafts[id]);
  const approved=['approved','validated','superseded'].includes(summary.status);
  const outdated=Boolean(summary.stale||summary.coverage_stale||summary.status==='stale');
  const native=nativeSettings();
  const publishAllowed=approved&&!outdated&&native.status==='configured'&&native.mode!=='fake'&&native.fake!==true;
  const citations=listOf(summary.citations||[]);
  const localDraft=state.summaryDrafts[id];
  const editorContent=localDraft?.content??summary.content;
  const draftConflict=localDraft&&localDraft.expectedHash!==summary.content_hash;
  if(!currentRender(renderToken))return;
  shell(`<a class="back-link" href="#/summaries">${icon('arrow')}Retour aux récapitulatifs</a>`+heading(summary.title||summary.project_name||'Récapitulatif de chantier','Relisez le contenu avec ses preuves avant de valider une version.',`${badge(summary.status||'draft')}${approved?`<a class="btn" href="${api.exportUrl(id,'md')}" download>${icon('download')}Exporter en Markdown</a>`:''}`)+`
  ${outdated?`<div class="notice danger">Le chantier ou ses sources ont évolué depuis cette synthèse. <button class="source-button" data-action="generate-dialog" data-id="${e(summary.project_id)}">Préparer une version actualisée</button></div>`:''}
  ${summary.coverage==='partial'||summary.coverage_complete===false||summary.coverage?.complete===false?'<div class="notice">Certaines sources ne sont pas traitées. Cette version doit signaler ce qui manque.</div>':''}
  ${summary.warnings?.length?`<div class="notice"><strong>${approved?'À connaître sur cette version':'Points à connaître avant validation'}</strong><ul>${summary.warnings.map(w=>`<li>${e(typeof w==='string'?w:w.message||JSON.stringify(w))}</li>`).join('')}</ul></div>`:''}
  ${draftConflict?'<div class="notice danger">Votre saisie est conservée, mais la version distante a changé. Gardez votre texte et comparez avant de réenregistrer.</div>':''}
  <div class="detail-layout"><div><form data-form="summary" data-id="${e(id)}"><div class="form-field"><div class="editor-label-row"><label for="summary-content">Contenu du récapitulatif${approved?' — version validée':''}</label><button class="btn small" type="button" data-action="show-citations">Voir les preuves (${citations.length})</button></div><textarea id="summary-content" class="summary-editor" name="content"${approved?' readonly':''} required>${e(editorContent||'')}</textarea></div><div class="form-error" role="alert" hidden></div><div class="summary-toolbar"><p id="summary-save-state">${approved?'Cette version validée est conservée.':'Brouillon chargé. Les modifications doivent être enregistrées.'}</p><div class="button-row">${!approved?`<button class="btn" type="submit">Enregistrer</button><button class="btn primary" type="button" data-action="approve-summary" data-id="${e(id)}"${!canApprove(summary)||state.summaryDirty?' disabled':''}>${icon('check')}Valider cette version</button>`:`<a class="btn" href="${api.exportUrl(id,'html')}" target="_blank" rel="noopener">${icon('download')}Export HTML</a>${publishAllowed?`<button class="btn primary" data-action="publish-summary" data-id="${e(id)}">${icon('external')}Publier dans AppFlowy</button>`:''}`}</div></div><div id="summary-publication-result" aria-live="polite"></div></form><div class="summary-meta"><span>Version ${e(summary.version||summary.version_number||'1')}</span><span>Créé le ${e(dateLabel(summary.created_at,true))}</span><span>Mémoire chantier : révision ${e(summary.project_revision??'non renseignée')}</span></div></div>
  <aside class="stack"><section class="panel" id="summary-citations" tabindex="-1"><div class="panel-heading"><h2>Sources citées</h2><span class="badge neutral">${citations.length}</span></div><div class="panel-body">${citations.length?citations.map((citation,index)=>`<div class="citation"><strong class="subtle-copy">Preuve ${index+1}</strong><p>${e(citation.quote||citation.excerpt||'Extrait non renseigné')}</p>${sourceControl(citation.source_id,citation.title||'Ouvrir la source')}</div>`).join(''):'<p class="subtle-copy">Aucune citation fournie par le service. Vérifiez les informations avant une diffusion.</p>'}</div></section><div class="sync-note"><h3>${icon('shield')}Une validation explicite</h3><p>Le contenu, les sources et la révision sont contrôlés à la validation. Une modification ultérieure crée une nouvelle version.</p></div>${summary.project_id?`<a class="btn" href="${projectHref(summary.project_id)}">${icon('building')}Revoir le chantier</a>`:''}</aside></div>`,'summaries','Récapitulatif');
}

function capabilityStatus(data) {
  if(!data) return 'not_configured';
  if(typeof data==='string') return data;
  return data.status || (data.configured===true?'ready':data.configured===false?'not_configured':data.mode||'unverified');
}
function capabilityRows(data) {
  const capabilities=data?.capabilities||{};
  return Object.entries(capabilities).length?`<ul class="capability-list">${Object.entries(capabilities).map(([name,value])=>`<li><span>${e(fieldLabel(name))}</span>${badge(typeof value==='boolean'?(value?'ready':'unavailable'):typeof value==='object'?value.status||'unverified':value)}</li>`).join('')}</ul>`:'';
}
async function renderSettings(section='appearance'){
  const renderToken=startRender('settings');if(renderToken===null)return;
  shell(heading('Paramètres')+settingsMarkup(section),'settings','Paramètres');
  const controller=await mountSettings(document.getElementById('settings-content'),{api,section});
  if(!currentRender(renderToken)){controller?.destroy();return;}activeSettings=controller;
}
async function renderMail(id=null){
  const renderToken=startRender('mail',id);if(renderToken===null)return;
  const folder=new URLSearchParams(location.hash.split('?')[1]||'').get('folder')||'inbox';
  shell('<section id="mail-workspace"></section>','mail','Messagerie');
  const controller=await mountMailbox(document.getElementById('mail-workspace'),{api,mailId:id,folder,publicDemo:Boolean(state.session?.demo&&!state.session?.auth_required),onSource:showSource,onNavigate:href=>{location.hash=href;},onFolders:items=>{const nav=document.getElementById('mail-folders');if(nav)nav.innerHTML=mailFolderLinks(folder,items);}});
  if(!currentRender(renderToken)){controller?.destroy();return;}activeMail=controller;
}

function showDialog(title,body,footer='') {
  const dialog=document.getElementById('app-dialog'); dialogReturnFocus=document.activeElement;
  dialog.innerHTML=`<div class="dialog-header"><h2 id="dialog-title">${e(title)}</h2><button class="icon-button" data-action="close-dialog" aria-label="Fermer la fenêtre">${icon('close')}</button></div><div class="dialog-body">${body}</div>${footer?`<div class="dialog-footer">${footer}</div>`:''}`;
  dialog.showModal();
}
function closeDialog() {document.getElementById('app-dialog').close();if(dialogReturnFocus?.isConnected)dialogReturnFocus.focus();}
async function showSource(id) {
  showDialog('Document source','<p class="loading-copy" role="status">Chargement de la source autorisée…</p>');
  try {
    const source=await api.source(id); const item=source.source||source;
    const needsAssignment=item.match_status&&item.match_status!=='matched';
    if(needsAssignment&&!state.projects.length)state.projects=listOf(await api.projects());
    const attachments=item.metadata?.attachments||[];
    const warnings=item.metadata?.warnings||[];
    const body=document.querySelector('#app-dialog .dialog-body');if(!body)return;
    body.innerHTML=`<p><strong>${e(item.subject||item.title||item.filename||'Source du dossier')}</strong></p><p class="subtle-copy">${e(item.sender||item.from_address||'')}${item.received_at?` · ${e(dateLabel(item.received_at,true))}`:''}</p>
      ${needsAssignment?`<div class="notice">${item.match_status==='ambiguous'?'Plusieurs chantiers peuvent correspondre à ce mail.':'Ce mail n’a pas encore de chantier confirmé.'} Choisissez le dossier avant l’analyse.</div><form data-form="assign" data-id="${e(id)}"><div class="form-field"><label for="source-project">Chantier concerné</label><select id="source-project" name="project_id" required><option value="">Choisir un chantier…</option>${state.projects.map(p=>`<option value="${e(p.id)}">${e(p.reference)} — ${e(projectTitle(p))}</option>`).join('')}</select></div><div class="form-error" role="alert" hidden></div><button class="btn primary" type="submit">Confirmer le chantier et analyser</button></form>`:''}
      ${warnings.length?`<div class="notice space-top">${warnings.map(w=>e(w)).join('<br>')}</div>`:''}
      ${attachments.length?`<div class="notice ${attachments.some(a=>a.status==='not_extracted')?'':'neutral'} space-top"><strong>Pièces jointes</strong><ul>${attachments.map(a=>`<li>${e(a.filename||'Fichier')} : ${a.status==='not_extracted'?'contenu non extrait, absent des propositions':e(statusLabel(a.status))}</li>`).join('')}</ul></div>`:''}
      <pre class="source-content space-top">${e(item.body_text||item.text||item.content||item.body||item.excerpt||'Le service n’a pas fourni de contenu lisible pour cette source.')}</pre>`;
  } catch(error) {const body=document.querySelector('#app-dialog .dialog-body');if(body)body.innerHTML=`<div class="notice danger" role="alert">${e(error.message)}</div>`;}
}
function showCreateProjectDialog() {
  showDialog('Créer un chantier',`<form id="create-project-form" data-form="create-project"><div class="form-field"><label for="project-reference">Référence du chantier</label><input class="input" id="project-reference" name="reference" maxlength="64" placeholder="TRV-2026-042" required></div><div class="form-field"><label for="project-name">Nom du chantier</label><input class="input" id="project-name" name="name" maxlength="200" placeholder="Aménagement de la place…" required></div><div class="form-field"><label for="project-description">Description</label><textarea id="project-description" name="description" maxlength="4000"></textarea></div><div class="form-error" role="alert" hidden></div></form>`,`<button class="btn" data-action="close-dialog">Annuler</button><button class="btn primary" type="submit" form="create-project-form">Créer le chantier</button>`);
}

async function showGenerateDialog(projectId='') {
  if(!state.projects.length)state.projects=listOf(await api.projects());
  if(!state.projects.length){toast('Importez une première source et créez un chantier avant de préparer un récapitulatif.',true);return;}
  showDialog('Préparer un récapitulatif',`<form id="generate-form" data-form="generate"><div class="form-field"><label for="generate-project">Chantier</label><select id="generate-project" name="project_id" required>${state.projects.map(p=>`<option value="${e(p.id)}"${String(p.id)===String(projectId)?' selected':''}>${e(projectTitle(p))}</option>`).join('')}</select></div><p class="help-text">Le brouillon utilise la mémoire complète du chantier : faits confirmés, notes humaines, sources et éléments encore à vérifier. Vous pourrez le relire avant validation.</p><div class="form-error" role="alert" hidden></div></form>`,`<button class="btn" data-action="close-dialog">Annuler</button><button class="btn primary" type="submit" form="generate-form">${icon('document')}Préparer le brouillon</button>`);
}
function showReviewDialog(kind,id) {
  const review=state.reviews.find(r=>String(r.id)===String(id));if(!review)return;
  const correcting=kind==='correct', replacing=kind==='replace';
  showDialog(correcting?'Corriger la proposition':replacing?'Remplacer la valeur précédente':'Écarter la proposition',`<form id="review-form" data-form="review-decision" data-id="${e(id)}" data-decision="${replacing?'replace':correcting?'accept':'reject'}"><p class="subtle-copy">${e(reviewTitle(review))}</p>${correcting?`<div class="form-field"><label for="corrected-value">Valeur à retenir</label><textarea id="corrected-value" name="corrected_value" required>${e(displayValue(reviewValue(review)))}</textarea></div>`:''}<div class="form-field"><label for="decision-reason">${correcting?'Motif de la correction':'Motif de la décision'}</label><textarea id="decision-reason" name="reason" required maxlength="2000" placeholder="Précisez ce que vous avez vérifié…"></textarea></div><div class="form-error" role="alert" hidden></div></form>`,`<button class="btn" data-action="close-dialog">Annuler</button><button class="btn ${correcting||replacing?'primary':'danger'}" type="submit" form="review-form">${correcting?'Confirmer la correction':replacing?'Confirmer le remplacement':'Écarter la proposition'}</button>`);
}
async function approveSummary(id) {
  if(state.summaryDirty){toast('Enregistrez vos modifications avant de valider cette version.',true);return;}
  const summary=state.current;if(!canApprove(summary)){toast('Cette version n’est pas validable. Rechargez son état ou préparez un nouveau récapitulatif.',true);return;}
  showDialog('Valider cette version ?',`<p>Le contenu actuel, ses sources et la révision ${e(summary.project_revision)} du chantier seront associés à cette version.</p><p class="subtle-copy">La validation ne déclenche aucun envoi. Une correction ultérieure devra produire une nouvelle version.</p><div class="form-error" role="alert" hidden></div>`,`<button class="btn" data-action="close-dialog">Continuer la relecture</button><button class="btn primary" data-action="confirm-approve" data-id="${e(id)}">${icon('check')}Valider cette version</button>`);
}

async function route() {
  const token=++state.routeToken;
  try{await preserveNativePage();}catch{history.replaceState(null,'',lastStableHash);toast('La page garde des modifications non enregistrées. Enregistrez-la avant de quitter ce dossier.',true);return;}
  if(token!==state.routeToken)return;state.renderEpoch++;

  const hash=(location.hash||'#/overview').replace(/^#\/?/,'').split('?')[0];
  const [section,encodedId]=hash.split('/');const id=encodedId?decodeURIComponent(encodedId):null;
  const routes={overview:['overview','Mon espace',renderWorkspace],activity:['activity','Les évolutions',renderOverview],projects:['projects','Chantiers',renderProjects],project:['projects','Chantier',()=>renderProject(id)],review:['review','À vérifier',()=>renderReview(id)],imports:['imports','Imports',renderImports],summaries:['summaries','Récapitulatifs',renderSummaries],summary:['summaries','Récapitulatif',()=>renderSummary(id)],mail:['mail','Courriels',()=>renderMail(id)],settings:['settings','Paramètres',()=>renderSettings(id||'appearance')]};
  const config=routes[section]||routes.overview;
  if(!state.session?.authenticated){renderLogin();return;}
  loading(config[0],config[1]);
  try {await config[2]();if(token===state.routeToken)lastStableHash=location.hash||'#/overview'; if(token===state.routeToken)document.getElementById('main')?.focus({preventScroll:true});}catch(error){if(token===state.routeToken){if(error.status===404&&section==='project'&&state.session?.public_demo){history.replaceState(null,'','#/overview');await route();}else errorScreen(error,config[0],config[1]);}}
}

function renderLogin(error='') {
  document.getElementById('app').innerHTML=`<main class="login-screen" id="main"><div class="boot-mark" aria-hidden="true">${icon('building')}</div><section class="login-card"><h1>Retrouver votre espace travaux.</h1><p>Connectez-vous au service privé configuré pour votre collectivité.</p><form data-form="login"><div class="form-field"><label for="login-password">Mot de passe d’accès</label><input class="input" id="login-password" type="password" name="password" autocomplete="current-password" required autofocus></div><div class="form-error" role="alert"${error?'':' hidden'}>${e(error)}</div><button class="btn primary" type="submit">Se connecter ${icon('arrow')}</button></form></section><p class="login-footer">L’accès est géré par votre exploitant. Aucun identifiant de messagerie ne doit être renseigné ici.</p></main>`;
  document.title='Connexion — Travaux';
}
async function initialize() {
  try {
    state.session=await api.session();
    if(!state.session?.authenticated){renderLogin();return;}
    try{const [bootstrap,projects]=await Promise.all([api.bootstrap(),api.projects()]);state.bootstrap=bootstrap;state.projects=listOf(projects);}catch(error){if(error.status===401){renderLogin();return;}state.bootstrap={};}
    await route();
  }catch(error){document.getElementById('app').innerHTML=`<main class="boot-screen" id="main">${empty('Le service est indisponible',error.message,'warning','<button class="btn primary" data-action="initialize">Réessayer la connexion</button>')}</main>`;}
}
function formError(form,error) {const element=form.querySelector('.form-error');if(element){element.textContent=error.message||String(error);element.hidden=false;element.focus?.();}else toast(error.message||String(error),true);}
async function busy(element,action) {
  const button=element?.closest?.('button')||element;if(button)button.disabled=true;
  try{return await action();}finally{if(button?.isConnected)button.disabled=false;}
}

document.addEventListener('click',async event=>{
  const control=event.target.closest('[data-action]');if(!control)return;
  const {action,id}=control.dataset;
  try {
    if(action==='open-menu'){setNavigationOpen(true,{focus:true});return;}
    if(action==='close-menu'){setNavigationOpen(false,{focus:true});return;}
    if(action==='close-dialog'){closeDialog();return;}
    if(action==='retry'){await route();return;}
    if(action==='initialize'){await initialize();return;}
    if(action==='source'){await showSource(id);return;}
    if(action==='create-project'){showCreateProjectDialog();return;}
    if(action==='retry-job'){await busy(control,()=>api.retryJob(id));toast('La relance du traitement a été demandée.');await renderImports();return;}
    if(action==='project-tab'){await preserveNativePage();state.projectTab=control.dataset.tab;location.hash=`${projectHref(id)}?view=${state.projectTab}`;return;}
    if(action==='select-review'){state.selectedReview=state.reviews.find(r=>String(r.id)===String(id));await renderReview(id);if(innerWidth<=640)document.querySelector('.review-detail')?.scrollIntoView({block:'start'});return;}
    if(action==='show-citations'){document.getElementById('summary-citations')?.scrollIntoView({block:'start'});document.getElementById('summary-citations')?.focus({preventScroll:true});return;}
    if(action==='generate-dialog'){await showGenerateDialog(id);return;}
    if(action==='replace-review'){showReviewDialog('replace',id);return;}
    if(action==='correct-review'||action==='reject-review'){showReviewDialog(action==='correct-review'?'correct':'reject',id);return;}
    if(action==='accept-review'){await busy(control,()=>api.decide(id,{decision:'accept',expected_revision:state.selectedReview?.project_revision}));toast('La proposition est confirmée. La mémoire du chantier a été actualisée.');await refreshBootstrap();await renderReview();return;}
    if(action==='next-mail'){const result=await busy(control,()=>api.nextMail());toast(result.message||'Le mail fictif suivant a été ajouté. Consultez les nouvelles propositions.');await refreshBootstrap();await renderImports();return;}
    if(action==='publish-summary'){
      const result=await busy(control,()=>api.publish(id,state.current.content_hash));
      const published=result.status==='published'||result.publication?.status==='published';
      const message=result.message||result.detail||(published?'La version a été publiée dans AppFlowy.':result.status==='uncertain'?'Publication incertaine : vérifiez l’espace natif avant de relancer.':'La publication n’est pas disponible pour cette configuration.');
      const target=document.getElementById('summary-publication-result');if(target)target.innerHTML=`<div class="notice ${published?'neutral':'danger'} space-top">${e(message)}</div>`;
      toast(message,!published);return;
    }
    if(action==='approve-summary'){await approveSummary(id);return;}
    if(action==='confirm-approve'){
      const summary=state.current;await busy(control,()=>api.approve(id,{expected_content_hash:summary.content_hash,expected_snapshot_hash:summary.snapshot_hash,expected_project_revision:summary.project_revision??summary.snapshot_revision}));
      closeDialog();toast('La version du récapitulatif est validée.');await renderSummary(id);return;
    }
    if(action==='logout'){if((hasUnsavedNotes()||state.summaryDirty)&&!window.confirm('Vos brouillons non enregistrés seront perdus. Voulez-vous vous déconnecter ?'))return;await preserveNativePage();await api.logout();state.session=null;state.summaryDrafts={};state.noteDrafts={};renderLogin();return;}
  }catch(error){if(document.getElementById('app-dialog').open){const target=document.querySelector('#app-dialog .form-error');if(target){target.textContent=error.message;target.hidden=false;}else toast(error.message,true);}else toast(error.message,true);}
});
async function refreshBootstrap(){try{state.bootstrap=await api.bootstrap();}catch{}}

document.addEventListener('submit',async event=>{
  const form=event.target.closest('form[data-form]');if(!form)return;event.preventDefault();
  const kind=form.dataset.form;const data=new FormData(form);const button=form.querySelector('button[type=submit]')||document.querySelector(`[form="${form.id}"][type=submit]`);
  const previous=form.querySelector('.form-error');if(previous)previous.hidden=true;
  try {
    if(kind==='login'){
      await busy(button,()=>api.login(data.get('password')));state.session=await api.session();state.bootstrap=await api.bootstrap();await route();return;
    }
    if(kind==='create-project'){
      const created=await busy(button,()=>api.createProject({reference:String(data.get('reference')).trim(),name:String(data.get('name')).trim(),description:String(data.get('description')||'').trim()}));
      closeDialog();await refreshBootstrap();state.projects=[];state.projectTab='memory';toast('Le chantier est créé.');location.hash=projectHref(created.id);return;
    }
    if(kind==='assign'){
      await busy(button,()=>api.assign(form.dataset.id,String(data.get('project_id'))));closeDialog();await refreshBootstrap();toast('Le chantier est confirmé. Consultez les propositions après traitement.');await renderImports();return;
    }
    if(kind==='note'){
      const body=String(data.get('body')||'').trim();if(!body)throw new Error('Saisissez une note avant de l’ajouter.');
      await busy(button,()=>api.note(form.dataset.id,body));delete state.noteDrafts[form.dataset.id];toast('La note humaine a été conservée dans le dossier.');await renderProject(form.dataset.id);return;
    }
    if(kind==='import'){
      const file=document.getElementById('eml-file').files[0];if(!file)throw new Error('Choisissez un fichier .eml.');
      if(file.size>2_000_000)throw new Error('Le fichier dépasse 2 Mo. Choisissez un fichier EML plus petit.');
      if(!file.name.toLowerCase().endsWith('.eml'))throw new Error('Choisissez un fichier au format .eml.');
      const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let offset=0;offset<bytes.length;offset+=32768)binary+=String.fromCharCode(...bytes.subarray(offset,offset+32768));
      const result=await busy(button,()=>api.importEml(file.name,btoa(binary),true));
      const needsAssignment=result.source?.match_status&&result.source.match_status!=='matched';
      const message=needsAssignment?'Le mail est conservé. Choisissez son chantier pour lancer l’analyse.':result.status==='succeeded'?'Le mail a été analysé. Ses informations attendent votre vérification.':'Le mail est conservé. Le traitement sera effectué par le worker configuré.';
      document.getElementById('import-result').innerHTML=`<div class="result-box" role="status">${e(result.message||message)}<div class="space-top-small">${needsAssignment?`<button class="btn primary" data-action="source" data-id="${e(result.source.id)}">Choisir le chantier</button>`:'<a href="#/review">Ouvrir les propositions</a>'}</div></div>`;toast('Import du mail terminé.');await refreshBootstrap();return;
    }
    if(kind==='review-decision'){
      const payload={decision:form.dataset.decision,reason:String(data.get('reason')||'').trim(),expected_revision:state.selectedReview?.project_revision};
      if(data.has('corrected_value'))payload.corrected_value=String(data.get('corrected_value')).trim();
      if(!payload.reason)throw new Error('Précisez le motif de votre décision.');
      await busy(button,()=>api.decide(form.dataset.id,payload));closeDialog();toast('La décision est conservée avec sa provenance.');await refreshBootstrap();await renderReview();return;
    }
    if(kind==='generate'){
      const result=await busy(button,async()=>{await preserveNativePage();return api.generate(data.get('project_id'),{});});const summary=result.summary||result;
      closeDialog();toast('Le brouillon est prêt pour la relecture.');location.hash=summaryHref(summary.id);return;
    }
    if(kind==='summary'){
      const content=String(data.get('content')||'').trim();if(!content)throw new Error('Le récapitulatif ne peut pas être vide.');
      const result=await busy(button,()=>api.saveSummary(form.dataset.id,{content,expected_content_hash:state.summaryDrafts[form.dataset.id]?.expectedHash||state.current.content_hash}));
      delete state.summaryDrafts[form.dataset.id];state.summaryDirty=false;
      const saved=result.summary||result;toast('Le brouillon a été enregistré dans une nouvelle version.');
      if(String(saved.id)!==String(form.dataset.id))location.hash=summaryHref(saved.id);else await renderSummary(saved.id);return;
    }
  }catch(error){formError(form,error);}
});
document.addEventListener('input',event=>{
  if(event.target.id==='project-search')applyProjectFilters();
  const noteForm=event.target.closest('form[data-form="note"]');
  if(noteForm&&event.target.name==='body'){
    if(event.target.value)state.noteDrafts[noteForm.dataset.id]={body:event.target.value};else delete state.noteDrafts[noteForm.dataset.id];
    const status=document.getElementById('note-draft-state');if(status)status.textContent=event.target.value?'Brouillon non enregistré. Conservé pendant votre navigation dans cet espace.':'';
  }
  if(event.target.id==='summary-content'&&!event.target.readOnly){state.summaryDirty=true;state.summaryDrafts[state.current.id]={content:event.target.value,expectedHash:state.summaryDrafts[state.current.id]?.expectedHash||state.current.content_hash};document.getElementById('summary-save-state').textContent='Modifications non enregistrées.';const approval=document.querySelector('[data-action="approve-summary"]');if(approval)approval.disabled=true;}
});
document.addEventListener('change',async event=>{
  if(event.target.id==='project-status')applyProjectFilters();
  if(event.target.id==='eml-file'){
    const file=event.target.files[0];const preview=document.getElementById('import-preview');
    if(!file){preview.hidden=true;return;}
    if(file.size>2_000_000){toast('Le fichier dépasse 2 Mo. Choisissez un EML plus petit.',true);event.target.value='';preview.hidden=true;return;}
    document.getElementById('eml-preview').value=(await file.text()).slice(0,12000);preview.hidden=false;
  }
});
document.addEventListener('keydown',event=>{
  if(event.target.matches?.('.workspace-view')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    const tabs=[...document.querySelectorAll('.workspace-view')];const index=tabs.indexOf(event.target);
    const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    event.preventDefault();tabs.forEach((tab,i)=>{tab.tabIndex=i===next?0:-1;});tabs[next]?.focus();return;
  }

  if(event.key==='Escape'&&navigationOpen){event.preventDefault();setNavigationOpen(false,{focus:true});}
  if(event.key==='Tab'&&navigationOpen){
    const controls=[...document.querySelectorAll('.sidebar a,.sidebar button')].filter(element=>!element.disabled&&element.getBoundingClientRect().width);
    const first=controls[0],last=controls.at(-1);
    if((event.shiftKey&&document.activeElement===first)||(!event.shiftKey&&document.activeElement===last)){event.preventDefault();(event.shiftKey?last:first)?.focus();}
  }
});
window.addEventListener('hashchange',route);
window.addEventListener('beforeunload',event=>{if(state.summaryDirty||hasUnsavedNotes()||nativeDirty||activeNative?.dirty||activeMail?.dirty){event.preventDefault();event.returnValue='';}});
document.getElementById('app-dialog').addEventListener('close',()=>{if(dialogReturnFocus?.isConnected)dialogReturnFocus.focus();});
initialize();
