import {escapeHtml as escape} from './model.js';

export async function mountNativePage(container, {api, project, view='page', actions=[], onSaved, onDirty,onMetadata,beforeSave=()=>{}}) {
  let editor = null, disposed = false, timer = null, saving = null;
  const isData=view==='table'||view==='kanban';
  const blocks=[['h1','Titre principal'],['h2','Sous-titre'],['text','Texte'],['bulleted','Liste à puces'],['todo','Case à cocher'],['quote','Citation'],['divider','Séparateur']];
  container.innerHTML = `<div class="native-page-toolbar" aria-label="Outils du document"><div class="native-page-actions">${isData?`<div class="action-view-switch" aria-label="Présentation des actions"><a href="#/project/${encodeURIComponent(project.id)}?view=table"${view==='table'?' aria-current="true"':''}>Liste</a><a href="#/project/${encodeURIComponent(project.id)}?view=kanban"${view==='kanban'?' aria-current="true"':''}>Kanban</a></div><button class="btn primary" type="button" data-native="new-action" disabled>+ Nouvelle action</button>`:`<details class="native-block-menu"><summary>+ Ajouter un bloc</summary><div class="native-block-options">${blocks.map(([kind,label])=>`<button type="button" data-native="block" data-kind="${kind}" disabled>${label}</button>`).join('')}<button type="button" data-native="database" disabled>Base de données</button></div></details>`}</div><div class="native-save-controls"><span class="native-save-status" role="status">Ouverture…</span><details class="native-block-menu native-more-menu"><summary aria-label="Options du document">···</summary><div class="native-block-options">${isData?'<button type="button" data-native="structure" aria-expanded="false" disabled>Structure du tableau</button>':''}<button type="button" data-native="save" disabled>Enregistrer maintenant</button></div></details></div></div><form class="native-action-form" data-native-form hidden><label for="native-action-title">Intitulé de l’action</label><div><input class="input" id="native-action-title" name="title" required maxlength="500" placeholder="Ex. : confirmer les accès"><button class="btn primary" type="submit">Ajouter</button><button class="btn" type="button" data-native="cancel-action">Annuler</button></div></form><div class="native-page-error" role="alert" hidden></div><div class="native-page-host" data-view="${view}" aria-label="${isData?'Actions du chantier':'Document du chantier'}"></div>`;
  const status = container.querySelector('.native-save-status');
  const error = container.querySelector('.native-page-error');
  const host = container.querySelector('.native-page-host');
  host.inert = true;
  const decorateSources=()=>{
    for(const link of host.querySelectorAll('a[href]')){
      let target;
      try{target=new URL(link.getAttribute('href'),location.href);}catch{continue;}
      if(target.origin===location.origin&&target.hash.startsWith('#/mail/')){
        link.classList.add('native-mail-link');
        link.setAttribute('aria-label','Voir le courriel source');
        link.title='Voir le courriel source';
      }
    }
  };
  const sourceObserver=new MutationObserver(decorateSources);
  sourceObserver.observe(host,{childList:true,subtree:true});
  const buttons = [...container.querySelectorAll('button')];
  const showError = failure => {
    if (disposed) return;
    error.hidden = false;
    error.textContent = failure?.message === 'page_revision_conflict' ? 'Cette page a changé dans un autre onglet. Votre saisie reste ici. Copiez-la avant de recharger la page pour comparer les versions.' : 'La page n’a pas pu être enregistrée. Votre saisie reste ici. Vérifiez la connexion puis utilisez Enregistrer.';
    status.textContent = 'Modifications non enregistrées';
  };
  async function flush() {
    clearTimeout(timer);
    beforeSave();
    if (!editor || !editor.dirty) return;
    if (saving) return saving;
    status.textContent = 'Enregistrement…';
    error.hidden = true;
    saving = (async () => {
      let value;
      // A second edit can arrive while the first PUT is in flight. Navigation
      // waits for every generation, not only for the first request's ACK.
      while (editor.dirty) {
        beforeSave();
        value = await editor.save();
        beforeSave();
        onSaved?.(value);
        if (disposed) return value;
      }
      status.textContent = '';
      return value;
    })().catch(failure => { showError(failure); throw failure; }).finally(() => {
      saving = null;
      if (!disposed && editor?.dirty && error.hidden) timer = setTimeout(() => flush().catch(() => {}), 1200);
    });
    return saving;
  }
  try {
    beforeSave();
    const page = await api.nativePage(project.id);
    beforeSave();
    if (disposed) return;
    const nativeEndpoint = '/native/editor.js';
    const native = await import(/* @vite-ignore */ nativeEndpoint);
    beforeSave();
    if (disposed) return;
    editor = await native.mount(host, {pageId: page.id, title: project.name,beforeSave,onMetadata, onStructureChange(open){container.querySelector('[data-native=structure]')?.setAttribute('aria-expanded',String(open));}, onDirty(dirty) {
      onDirty?.(dirty);
      if (dirty && !disposed) {
        status.textContent = 'Modifications en cours…';
        clearTimeout(timer);
        timer = setTimeout(() => flush().catch(() => {}), 1200);
      }
    }});
    if (disposed) { editor.unmount(); return; }
    for(let offset=0;offset<actions.length;offset+=100)editor.importActions(actions.slice(offset,offset+100));
    if(isData)await editor.setDatabaseView(view);
    editor.setPresentation(view);
    host.inert=false;
    decorateSources();
    buttons.forEach(button => { button.disabled = false; });
    status.textContent = editor.dirty ? 'Modifications…' : '';
  } catch (failure) {
    error.hidden = false;
    error.textContent = 'La page native n’a pas pu être ouverte. Rechargez ce dossier ou consultez sa mémoire et ses sources.';
    status.textContent = 'Ouverture interrompue';
    host.innerHTML = `<p class="subtle-copy">${escape(failure?.message === 'session_required' ? 'Votre session a expiré.' : 'Le service de documents est indisponible.')}</p>`;
  }
  const click = async event => {
    const control = event.target.closest('[data-native]');
    const action = control?.dataset.native;
    if (!action || !editor) return;
    if (action === 'paragraph') editor.addBlock('text');
    if (action === 'block') {editor.addBlock(control.dataset.kind);control.closest('details').open=false;}
    if (action === 'database') {editor.addDatabase();control.closest('details').open=false;await flush();}
    if (action === 'structure') {editor.setStructureOpen(control.getAttribute('aria-expanded')!=='true');control.closest('details').open=false;}
    if (action === 'new-action') {const form=container.querySelector('.native-action-form');form.hidden=false;form.querySelector('input').focus();}
    if (action === 'cancel-action') {container.querySelector('.native-action-form').hidden=true;container.querySelector('[data-native=new-action]')?.focus();}
    if (action === 'save') await flush().catch(() => {});
  };
  container.addEventListener('click', click);
  const submit=async event=>{
    if(!event.target.matches('[data-native-form]')||!editor)return;
    event.preventDefault();const form=event.target;const title=String(new FormData(form).get('title')||'').trim();if(!title)return;
    try{editor.addAction({title});await flush();form.reset();form.hidden=true;container.querySelector('[data-native=new-action]')?.focus();}catch(failure){showError(failure);}
  };
  container.addEventListener('submit',submit);
  const closeBlockMenu=event=>{
    const menu=container.querySelector('.native-block-menu');
    if(!menu?.open)return;
    if(event.type==='keydown'&&event.key==='Escape'){
      event.preventDefault();event.stopPropagation();menu.open=false;menu.querySelector('summary').focus();
    }else if(event.type==='click'&&!menu.contains(event.target))menu.open=false;
  };
  container.addEventListener('keydown',closeBlockMenu);
  document.addEventListener('click',closeBlockMenu);
  return {
    flush,
    async updateActions(next) {if(disposed||!editor)return;beforeSave();for(let offset=0;offset<next.length;offset+=100)editor.importActions(next.slice(offset,offset+100));decorateSources();return flush();},
    get dirty() { return Boolean(editor?.dirty); },
    getMetadata(){return editor?.getMetadata?.();},
    destroy() { disposed = true; clearTimeout(timer); sourceObserver.disconnect(); container.removeEventListener('click', click); container.removeEventListener('submit',submit); container.removeEventListener('keydown',closeBlockMenu); document.removeEventListener('click',closeBlockMenu); editor?.unmount(); },
  };
}
