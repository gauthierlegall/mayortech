import {mount} from './editor';
const status = document.querySelector('#status')!;
const pageId = new URLSearchParams(location.search).get('page') ?? 'native-editor-fixture';
mount(document.querySelector('#editor') as HTMLElement, {
  pageId, title: 'École des Ajoncs — notes',
  onDirty: dirty => { status.textContent = dirty ? 'Modifications non enregistrées' : 'Enregistré'; },
  onMetadata: snapshot => { globalThis['nativeMetadata'] = snapshot; },
  onStructureChange: open => { (globalThis['nativeStructureChanges'] ??= []).push(open); },
}).then(editor => {
  (window as any).nativeEditor = editor;
  document.querySelector('#database')!.addEventListener('click', () => editor.addDatabase({title: 'Actions fictives', seedRows: true}));
  document.querySelector('#save')!.addEventListener('click', () => editor.save().catch(error => { status.textContent = error.message; }));
  const tools = document.createElement('nav'); tools.setAttribute('aria-label', 'Commandes natives, preuve fictive');
  for (const [kind, label] of [['h1', 'Ajouter un titre'], ['bulleted', 'Ajouter une liste'], ['todo', 'Ajouter une case à cocher'], ['quote', 'Ajouter une citation'], ['divider', 'Ajouter une séparation']]) {
    const button = document.createElement('button'); button.textContent = label;
    button.addEventListener('click', () => editor.addBlock(kind, kind === 'divider' ? '' : `Bloc fictif ${kind}`));
    tools.append(button);
  }
  for (const [mode, label] of [['table', 'Voir le tableau natif'], ['kanban', 'Voir le Kanban natif']]) {
    const button = document.createElement('button'); button.textContent = label;
    button.addEventListener('click', () => editor.setDatabaseView(mode).catch(error => { status.textContent = error.message; }));
    tools.append(button);
  }
  document.querySelector('header').append(tools);
}).catch(error => { console.error(error.stack); status.textContent = error.message; });
