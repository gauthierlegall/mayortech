import {getInternalStoreExtensions} from '@blocksuite/affine/extensions/store';
import {getInternalViewExtensions} from '@blocksuite/affine/extensions/view';
import {StoreExtensionManager, ViewExtensionManager} from '@blocksuite/affine/ext-loader';
import {FoundationViewExtension} from '@blocksuite/affine/foundation/view';
import {PlainTextAdapter} from '@blocksuite/affine/shared/adapters';
import {EditorSettingExtension} from '@blocksuite/affine/shared/services';
import {BlockStdScope} from '@blocksuite/affine/std';
import {Text} from '@blocksuite/affine/store';
import {DatabaseBlockDataSource, databaseBlockProperties} from '@blocksuite/affine/blocks/database';
import {ImageViewExtension} from '@blocksuite/affine/blocks/image/view';
import {AttachmentViewExtension} from '@blocksuite/affine/blocks/attachment/view';
import {BookmarkViewExtension} from '@blocksuite/affine/blocks/bookmark/view';
import {EmbedViewExtension} from '@blocksuite/affine/blocks/embed/view';
import {EmbedDocViewExtension} from '@blocksuite/affine/blocks/embed-doc/view';
import {propertyPresets} from '@blocksuite/data-view/property-presets';
import {groupTraitKey} from '@blocksuite/data-view';
import {focusBlockEnd} from '@blocksuite/affine/shared/commands';
import {signal} from '@preact/signals-core';
import * as Y from 'yjs';
import {NativeWorkspace} from './workspace';
import {databaseViewInitTemplate} from '../vendor/affine/database-view-init';
import {encodeState, normalizeStateResponse} from './state-codec.mjs';
import {blockSpec, mergeStatusOptions, normalizeActionImports, normalizeActionPatch, partitionActionImports, freezeSnapshot} from './native-commands.mjs';
import {compactGroupingExtension, configureGrouping, compactKanban} from './kanban-presentation';
import {notesSnapshot} from './notes-preview.mjs';
import './style.css';

export const EDITOR_VERSION = 'blocksuite-0.22.4';
export const capabilities = Object.freeze({
  engine: 'AFFiNE BlockSuite', version: '0.22.4', pages: true, blocks: true,
  database: true, table: true, kanban: true, typedProperties: true,
  relations: false, formulas: false, calendar: false, blobs: false, realtime: false,
});

export async function mount(container: HTMLElement, options: {
  pageId: string; title?: string; onSave?: (value: any) => void; onDirty?: (dirty: boolean) => void;
  beforeSave?: () => void;
  onMetadata?: (snapshot: any) => void;
  presentation?: 'page' | 'table' | 'kanban'; onStructureChange?: (open: boolean) => void;
}) {
  if (!(container instanceof HTMLElement) || !/^[A-Za-z0-9_-]{1,160}$/.test(options.pageId)) throw new Error('invalid_page_mount');
  const endpoint = `/api/v1/pages/${encodeURIComponent(options.pageId)}/state`;
  const response = await fetch(endpoint, {credentials: 'same-origin', headers: {Accept: 'application/json'}, redirect: 'error'});
  if (!response.ok) throw new Error(response.status === 401 ? 'session_required' : 'page_state_unavailable');
  const initial = normalizeStateResponse(await response.json());
  const ydoc = new Y.Doc({guid: options.pageId});
  if (initial.state.length) Y.applyUpdate(ydoc, initial.state, 'backend-load');
  const storeManager = new StoreExtensionManager(getInternalStoreExtensions());
  const workspace = new NativeWorkspace(ydoc, options.pageId, options.title ?? initial.title ?? 'Page', storeManager.get('store'));
  const doc = workspace.getDoc(options.pageId)!;
  const store = doc.getStore();
  store.load(() => {
    if (!store.root) {
      const root = store.addBlock('affine:page', {title: new Text(options.title ?? initial.title ?? 'Page')});
      store.addBlock('affine:surface', {}, root);
      const note = store.addBlock('affine:note', {}, root);
      store.addBlock('affine:paragraph', {text: new Text(initial.text ?? '')}, note);
      store.resetHistory();
    }
  });
  // Compare provider identities, never constructor names changed by minifiers.
  const omittedProviders = new Set([AttachmentViewExtension, ImageViewExtension, BookmarkViewExtension, EmbedViewExtension, EmbedDocViewExtension]);
  const views = new ViewExtensionManager(getInternalViewExtensions().filter(provider => !omittedProviders.has(provider as any)));
  views.configure(FoundationViewExtension, {fontConfig: [], telemetry: {track: () => {}}} as any);
  const std = new BlockStdScope({store, extensions: [...views.get('page'), EditorSettingExtension({setting$: signal({})}), compactGroupingExtension]});
  const host = std.render();
  container.classList.add('travaux-native-editor', 'affine-page-viewport');
  const previousPresentation = container.getAttribute('data-native-presentation');
  const previousStructure = container.getAttribute('data-native-structure-open');
  const previousTabindex = container.getAttribute('tabindex');
  const initialPresentation = options.presentation ?? container.dataset.view ?? 'page';
  let presentation: 'page' | 'table' | 'kanban' = ['page', 'table', 'kanban'].includes(initialPresentation) ? initialPresentation as any : 'page';
  let structureOpen = false;
  let structureTrigger: HTMLElement | null = null;
  container.dataset.nativePresentation = presentation;
  container.dataset.nativeStructureOpen = 'false';
  if (previousTabindex === null) container.tabIndex = -1;
  const mobileDatabases = document.createElement('section');
  mobileDatabases.className = 'travaux-native-mobile-databases';
  mobileDatabases.setAttribute('aria-label', 'Bases de cette page, lecture en fiches');
  container.replaceChildren(host, mobileDatabases);
  let revisionHash = initial.revision_hash;
  let generation = 0;
  let dirty = !initial.state.length;
  let disposed = false;
  let saving: Promise<any> | null = null;
  const selectedViews = ydoc.getMap<string>('travaux:database-views');
  const workspaceSettings = ydoc.getMap<string>('travaux:workspace');
  const actionBindings = ydoc.getMap<any>('travaux:action-bindings');
  const viewSubscriptions = new Map<string, {source: DatabaseBlockDataSource; dispose: () => void}>();
  let activeDatabaseId: string | null = null;
  let mobileRefreshScheduled = false;
  const change = () => {
    generation += 1; dirty = true; options.onDirty?.(true);
    scheduleMetadata();
  };
  ydoc.on('update', change);
  options.onDirty?.(dirty);

  function renderedSource(id: string): DatabaseBlockDataSource | undefined {
    const title = std.view.getBlock(id)?.querySelector('affine-database-title');
    // Public SDK component property, not the private lazy datasource field.
    return title?.dataViewLogic?.view?.manager?.dataSource as DatabaseBlockDataSource | undefined;
  }
  function sourceFor(model: any) { return renderedSource(model.id) ?? configureGrouping(new DatabaseBlockDataSource(model)); }
  function observeViews() {
    const ids = new Set(store.getBlocksByFlavour('affine:database').map(({model}) => model.id));
    for (const [id, subscription] of viewSubscriptions) {
      if (!ids.has(id) || renderedSource(id) !== subscription.source) { subscription.dispose(); viewSubscriptions.delete(id); }
    }
    for (const id of ids) {
      const source = renderedSource(id);
      if (!source || viewSubscriptions.has(id)) continue;
      const preferred = selectedViews.get(id);
      if (preferred && source.viewManager.viewGet(preferred)) source.viewManager.setCurrentView(preferred);
      const dispose = source.viewManager.currentViewId$.subscribe(value => {
        if (value && selectedViews.get(id) !== value) selectedViews.set(id, value);
        scheduleMetadata();
      });
      viewSubscriptions.set(id, {source, dispose});
    }
  }
  function scheduleMetadata() {
    if (mobileRefreshScheduled || disposed) return;
    mobileRefreshScheduled = true;
    queueMicrotask(() => {
      mobileRefreshScheduled = false;
      if (disposed) return;
      observeViews(); markPresentation(); markEmptyCardCells(); renderMobileDatabases(); options.onMetadata?.(getMetadata());
    });
  }
  const viewObserver = new MutationObserver(scheduleMetadata);
  viewObserver.observe(host, {childList: true, subtree: true});
  function markPresentation() {
    for (const title of host.querySelectorAll('doc-title')) title.setAttribute('data-native-project-title', '');
    for (const database of host.querySelectorAll('affine-database')) {
      database.toggleAttribute('data-native-managed-actions', workspaceSettings.get('actionDatabaseId') === database.blockId);
      database.toggleAttribute('data-native-active-database', activeDatabaseId === database.blockId);
      const title = database.querySelector('affine-database-title');
      const titleRow = title?.parentElement;
      const header = titleRow?.parentElement;
      if (header?.querySelector('data-view-header-views')) {
        header.setAttribute('data-native-db-header', '');
        header.setAttribute('role', 'region');
        header.setAttribute('aria-label', 'Structure et réglages de la base');
        header.tabIndex = -1;
        if (!header.id) header.id = `travaux-structure-${options.pageId}-${database.blockId}`;
        titleRow?.setAttribute('data-native-db-title-row', '');
      }
      const viewBar = database.querySelector('data-view-header-views');
      if (viewBar) {
        viewBar.setAttribute('data-native-viewbar', '');
        const wrapper = viewBar.parentElement?.tagName === 'UNI-LIT' ? viewBar.parentElement.parentElement : viewBar.parentElement;
        wrapper?.setAttribute('data-native-viewbar-container', '');
      }
    }
  }
  const setPresentation = (view: 'page' | 'table' | 'kanban') => {
    if (!['page', 'table', 'kanban'].includes(view)) throw new Error('invalid_presentation');
    if (disposed) throw new Error('editor_unmounted');
    presentation = view;
    container.dataset.nativePresentation = view;
    scheduleMetadata();
    return view;
  };
  const setStructureOpen = (open: boolean) => {
    if (typeof open !== 'boolean') throw new Error('invalid_structure_state');
    if (disposed) throw new Error('editor_unmounted');
    if (open === structureOpen) return structureOpen;
    if (open) structureTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    structureOpen = open;
    container.dataset.nativeStructureOpen = String(open);
    markPresentation();
    options.onStructureChange?.(open);
    scheduleMetadata();
    if (open) requestAnimationFrame(() => {
      if (!disposed && structureOpen) {
        const panels = [...host.querySelectorAll<HTMLElement>('[data-native-db-header]')];
        const panel = panels.find(panel => panel.closest('[data-native-active-database]') && panel.getClientRects().length)
          ?? panels.find(panel => panel.getClientRects().length);
        (panel ?? container).focus({preventScroll: true});
      }
    });
    else if (structureTrigger?.isConnected && structureTrigger.getClientRects().length) structureTrigger.focus({preventScroll: true});
    else container.focus({preventScroll: true});
    return structureOpen;
  };
  const structureKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && structureOpen && !event.defaultPrevented
        && event.target instanceof Element && event.target.closest('[data-native-db-header]')) {
      event.preventDefault(); event.stopPropagation(); setStructureOpen(false);
    }
  };
  host.addEventListener('keydown', structureKeydown);

  const getState = () => new Uint8Array(Y.encodeStateAsUpdate(ydoc));
  const exportText = async (notesOnly = false) => {
    const transformer = store.getTransformer();
    try {
      const fullSnapshot = transformer.docToSnapshot(store);
      if (!fullSnapshot) throw new Error('native_text_export_failed');
      const snapshot = notesOnly ? notesSnapshot(fullSnapshot, workspaceSettings.get('actionDatabaseId')) : fullSnapshot;
      // SDK 0.22.4 renders a synthetic fixed title property but omits that
      // header from its text adapter when columns lack an explicit title.
      // Normalize the export snapshot only; the native document is unchanged.
      const normalizeDatabaseHeaders = (node: any) => {
        if (node.flavour === 'affine:database' && Array.isArray(node.props?.columns)
            && !node.props.columns.some((column: any) => column.type === 'title')) {
          node.props.columns = [{id: 'title', type: 'title', name: 'Intitulé', data: {}}, ...node.props.columns];
        }
        for (const child of node.children ?? []) normalizeDatabaseHeaders(child);
      };
      normalizeDatabaseHeaders(snapshot.blocks);
      const output = await new PlainTextAdapter(transformer, store.provider).fromDocSnapshot({snapshot, assets: transformer.assets});
      if (typeof output.file !== 'string' || output.file.length > 200_000) throw new Error('native_text_export_limit');
      return output.file;
    } finally { transformer[Symbol.dispose](); }
  };
  const getText = () => exportText();
  const getNotesText = () => exportText(true);
  const save = () => {
    if (disposed) return Promise.reject(new Error('editor_unmounted'));
    if (saving) return saving;
    const snapshot = getState();
    const savedGeneration = generation;
    saving = (async () => {
      const text = await getText();
      options.beforeSave?.();
      const result = await fetch(endpoint, {
        method: 'PUT', credentials: 'same-origin', redirect: 'error',
        headers: {'Content-Type': 'application/json', 'X-Requested-With': 'Travaux', Accept: 'application/json'},
        body: JSON.stringify({state_base64: encodeState(snapshot), expected_revision_hash: revisionHash, text, editor_version: EDITOR_VERSION}),
      });
      if (!result.ok) throw new Error(result.status === 409 ? 'page_revision_conflict' : result.status === 401 ? 'session_required' : 'page_save_failed');
      const value = await result.json();
      if (!value || typeof value.revision_hash !== 'string' || !/^[a-f0-9]{64}$/.test(value.revision_hash)) throw new Error('invalid_save_ack');
      revisionHash = value.revision_hash;
      dirty = generation !== savedGeneration;
      options.onDirty?.(dirty); options.onSave?.(value);
      return value;
    })().finally(() => { saving = null; });
    return saving;
  };
  const addBlock = (kind: string, text = '') => {
    if (disposed) throw new Error('editor_unmounted');
    if (typeof text !== 'string' || text.length > 100_000) throw new Error('invalid_block_text');
    const spec = blockSpec(kind);
    const note = store.getBlocksByFlavour('affine:note')[0]?.model;
    if (!note) throw new Error('native_note_missing');
    const props = spec.flavour === 'affine:divider' ? {} : {type: spec.type, text: new Text(text), ...(spec.type === 'todo' ? {checked: false} : {})};
    const id = store.addBlock(spec.flavour, props, note.id);
    requestAnimationFrame(() => {
      if (disposed) return;
      const block = std.view.getBlock(id);
      if (block) { std.command.exec(focusBlockEnd, {focusBlock: block, force: true}); block.scrollIntoView({block: 'nearest'}); }
    });
    return id;
  };
  const addParagraph = (text = '') => addBlock('text', text);
  const getDatabases = () => store.getBlocksByFlavour('affine:database').map(({model}) => {
    const source = sourceFor(model);
    const properties = source.properties$.value.map(id => ({id, name: source.propertyNameGet(id), type: source.propertyTypeGet(id)}));
    const views = source.viewDataList$.value.map(view => ({id: view.id, name: view.name, mode: view.mode}));
    const activeViewId = source.viewManager.currentViewId$.value;
    const activeView = views.find(view => view.id === activeViewId)?.mode ?? 'table';
    const nativeGroups = source.viewManager.currentView$.value?.traitGet(groupTraitKey)?.groupsDataList$.value ?? [];
    const bindings = new Map([...actionBindings.entries()].map(([key, value]) => [value.rowId, {sourceKey: key, sourceUrl: value.sourceUrl}]));
    return {id: model.id, managedActions: workspaceSettings.get('actionDatabaseId') === model.id, title: (model.props as any).title?.toString() || 'Base de données',
      properties, views, activeViewId, activeView,
      groups: nativeGroups.map(group => ({id: group.key, name: group.name$.value || 'Sans statut', rowIds: group.rows.map(row => row.rowId)})),
      rows: source.rows$.value.map(id => ({id, ...bindings.get(id), fields: properties.map(property => {
        const value = source.cellValueGet(id, property.id);
        const meta = property.type ? source.propertyMetaGet(property.type) : undefined;
        const text = value == null ? '' : meta?.config.rawValue.toString({value, data: source.propertyDataGet(property.id), dataSource: source}) ?? '';
        return {...property, text};
      })})),
    };
  });
  const getMetadata = () => {
    const blocks: any[] = [];
    const visit = (model: any) => { if (!model) return; blocks.push({id: model.id, flavour: model.flavour, type: model.props?.type}); model.children.forEach(visit); };
    visit(store.root);
    const databases = getDatabases();
    const selected = databases.find(database => database.id === activeDatabaseId) ?? databases[0];
    return freezeSnapshot({pageId: options.pageId, presentation, structureOpen, managedActionDatabaseId: workspaceSettings.get('actionDatabaseId') ?? null, blocks, blockCount: blocks.length, databases,
      activeDatabaseId: selected?.id ?? null, activeView: selected?.activeView ?? null});
  };
  function markEmptyCardCells() {
    for (const cell of host.querySelectorAll<any>('affine-data-view-kanban-cell')) {
      const value = cell.column?.cellGetOrCreate(cell.cardId)?.stringValue$.value;
      cell.toggleAttribute('data-travaux-empty', !String(value ?? '').trim());
    }
  }
  function renderMobileDatabases() {
    const open = new Set([...mobileDatabases.querySelectorAll<HTMLDetailsElement>('details[open]')].map(item => item.dataset.rowId));
    mobileDatabases.replaceChildren();
    for (const database of getDatabases()) {
      const section = document.createElement('section');
      section.dataset.databaseId = database.id;
      section.toggleAttribute('data-native-managed-actions', database.managedActions);
      const heading = document.createElement('h3'); heading.textContent = database.title;
      heading.setAttribute('data-native-mobile-db-title', '');
      const help = document.createElement('p'); help.className = 'travaux-native-mobile-help';
      help.setAttribute('data-native-mobile-db-help', '');
      help.textContent = 'Lecture en fiches sur mobile. Les bases se modifient sur ordinateur.';
      section.append(heading, help);
      if (!database.rows.length) {
        const empty = document.createElement('p'); empty.textContent = 'Aucune fiche dans cette base.'; section.append(empty);
      }
      const groups = database.activeView === 'kanban' && database.groups.length ? database.groups : [{id: 'all', name: '', rowIds: database.rows.map(row => row.id)}];
      for (const group of groups) {
        const groupSection = document.createElement('section'); groupSection.dataset.groupId = group.id;
        if (group.name) { const groupHeading = document.createElement('h4'); groupHeading.textContent = `${group.name} · ${group.rowIds.length}`; groupSection.append(groupHeading); }
        for (const rowId of group.rowIds) {
        const row = database.rows.find(item => item.id === rowId);
        if (!row) continue;
        const card = document.createElement('article'); card.className = 'travaux-native-record'; card.dataset.rowId = row.id;
        const title = row.fields.find(field => field.type === 'title')?.text || 'Fiche sans titre';
        const rowHeading = document.createElement('h4'); rowHeading.textContent = title;
        card.append(rowHeading);
        if (row.sourceUrl && /^#\/mail\/[A-Za-z0-9_-]{1,160}$/.test(row.sourceUrl)) {
          const link = document.createElement('a'); link.href = row.sourceUrl; link.textContent = 'Voir l’échange'; card.append(link);
        }
        const detail = document.createElement('details'); detail.dataset.rowId = row.id; detail.open = open.has(row.id);
        const summary = document.createElement('summary'); summary.textContent = 'Voir tous les champs';
        const fields = document.createElement('dl');
        for (const field of row.fields) {
          const term = document.createElement('dt'); term.textContent = field.name;
          const description = document.createElement('dd');
          const mailLink = row.sourceUrl && /^#\/mail\/[A-Za-z0-9_-]{1,160}$/.test(row.sourceUrl) ? row.sourceUrl : null;
          if (field.type === 'link' && mailLink) {
            const link = document.createElement('a'); link.href = mailLink; link.textContent = 'Ouvrir le courriel lié'; description.append(link);
          } else description.textContent = field.text || 'Non renseigné';
          fields.append(term, description);
        }
        detail.append(summary, fields); card.append(detail); groupSection.append(card);
        }
        section.append(groupSection);
      }
      mobileDatabases.append(section);
    }
  }
  function statusProperty(source: DatabaseBlockDataSource) {
    let id = source.properties$.value.find(property => source.propertyTypeGet(property) === 'select' && /^statut(?: \d+)?$/u.test(source.propertyNameGet(property).trim().toLocaleLowerCase('fr')));
    if (!id) id = source.propertyAdd('end', {type: propertyPresets.selectPropertyConfig.type, name: 'Statut'});
    if (!id) throw new Error('native_status_property_unavailable');
    const data = source.propertyDataGet(id);
    const options = mergeStatusOptions(data.options ?? []);
    if (JSON.stringify(options) !== JSON.stringify(data.options)) source.propertyDataSet(id, {...data, options});
    return {id, options};
  }
  function propertyFor(source: DatabaseBlockDataSource, type: string, name: string) {
    const id = source.properties$.value.find(id => source.propertyTypeGet(id) === type && source.propertyNameGet(id) === name)
      ?? source.propertyAdd('end', {type, name});
    if (!id) throw new Error('native_property_unavailable');
    return id;
  }
  function databaseModel(id?: string) {
    const model = id ? store.getModelById(id) : store.getBlocksByFlavour('affine:database')[0]?.model;
    if (!model || model.flavour !== 'affine:database') throw new Error('native_database_missing');
    return model;
  }
  const addDatabase = ({title = 'Actions du dossier', seedRows = false} = {}) => {
    if (disposed) throw new Error('editor_unmounted');
    if (typeof title !== 'string' || !title.trim() || title.length > 500) throw new Error('invalid_database_title');
    const note = store.getBlocksByFlavour('affine:note')[0]?.model;
    if (!note) throw new Error('native_note_missing');
    const id = store.addBlock('affine:database', {columns: [], cells: {}, title: new Text(title)}, note.id);
    const model = store.getModelById(id) as any;
    const source = configureGrouping(new DatabaseBlockDataSource(model));
    if (seedRows) databaseViewInitTemplate(source, 'table');
    else source.viewManager.viewAdd('table');
    source.propertyNameSet('title', 'Intitulé');
    const table = source.viewManager.currentViewId$.value!;
    source.viewManager.viewGet(table)?.nameSet('Liste');
    const description = source.propertyAdd('end', {type: databaseBlockProperties.richTextColumnConfig.type, name: 'Description'});
    const status = statusProperty(source);
    const kanban = source.viewManager.viewAdd('kanban');
    source.viewManager.viewGet(kanban)?.nameSet('Cartes');
    source.viewManager.viewGet(kanban)?.traitGet(groupTraitKey)?.changeGroup(status.id);
    compactKanban(source, source.viewManager.viewGet(kanban));
    if (seedRows) {
      const amount = propertyFor(source, propertyPresets.numberPropertyConfig.type, 'Montant indiqué');
      const rows = [...source.rows$.value];
      source.rowDelete(rows.slice(2));
      for (const [index, [label, detail, value]] of ([['Visite fictive', 'Contrôler les accès à la cour', 12000], ['Devis fictif', 'Comparer la version reçue', 2400]] as const).entries()) {
        const row = rows[index];
        store.updateBlock(store.getModelById(row)!, {text: new Text(label)});
        if (description) source.cellValueChange(row, description, new Text(detail));
        if (amount) source.cellValueChange(row, amount, value);
        source.cellValueChange(row, status.id, status.options[index].id);
      }
    }
    activeDatabaseId = id;
    return id;
  };
  const ensureDatabase = ({title = 'Actions du dossier'} = {}) => {
    if (disposed) throw new Error('editor_unmounted');
    const managed = store.getModelById(workspaceSettings.get('actionDatabaseId') ?? '');
    if (managed?.flavour === 'affine:database') return managed.id;
    // Legacy/user-created bases are reused conservatively, never relabelled as
    // managed based on their title or on bindings. Only a new automatic base
    // receives the marker, so the Notes presentation cannot hide human data.
    const existing = store.getBlocksByFlavour('affine:database')[0]?.model;
    if (existing) return existing.id;
    const id = addDatabase({title});
    workspaceSettings.set('actionDatabaseId', id);
    return id;
  };
  const setDatabaseView = async (mode: 'table' | 'kanban', id?: string) => {
    if (mode !== 'table' && mode !== 'kanban') throw new Error('invalid_database_view');
    const model = databaseModel(id ?? ensureDatabase());
    activeDatabaseId = model.id;
    const source = sourceFor(model);
    const status = statusProperty(source);
    let view = source.viewDataList$.value.find(view => view.mode === mode);
    if (!view) {
      const viewId = source.viewManager.viewAdd(mode);
      source.viewManager.viewGet(viewId)?.nameSet(mode === 'table' ? 'Liste' : 'Cartes');
      view = source.viewDataList$.value.find(view => view.id === viewId);
    }
    if (!view) throw new Error('native_database_view_unavailable');
    if (mode === 'kanban') source.viewManager.viewGet(view.id)?.traitGet(groupTraitKey)?.changeGroup(status.id);
    if (mode === 'kanban') compactKanban(source, source.viewManager.viewGet(view.id));
    selectedViews.set(model.id, view.id);
    // The visible component owns its own manager. Wait for its public title
    // component rather than switching an unrelated temporary datasource.
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (disposed) throw new Error('editor_unmounted');
      const live = renderedSource(model.id);
      if (live) {
        live.viewManager.setCurrentView(view.id);
        scheduleMetadata();
        return model.id;
      }
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
    }
    throw new Error('native_database_view_not_rendered');
  };
  function prepareAction(source: DatabaseBlockDataSource, action: any, statusName = 'À faire') {
    const status = statusProperty(source);
    const selected = status.options.find(option => option.value === statusName);
    if (!selected) throw new Error('invalid_action_status');
    const values: {property: string; value: any}[] = [{property: status.id, value: selected.id}];
    if (action.description) values.push({property: propertyFor(source, databaseBlockProperties.richTextColumnConfig.type, 'Description'), value: new Text(action.description)});
    if (action.owner) values.push({property: propertyFor(source, databaseBlockProperties.richTextColumnConfig.type, 'Responsable'), value: new Text(action.owner)});
    if (action.priority) values.push({property: propertyFor(source, databaseBlockProperties.richTextColumnConfig.type, 'Priorité'), value: new Text(action.priority)});
    if (action.sourceUrl) values.push({property: propertyFor(source, databaseBlockProperties.linkColumnConfig.type, 'Échange'), value: new URL(action.sourceUrl, location.origin + '/').href});
    if (Number.isInteger(action.progress)) values.push({property:propertyFor(source,databaseBlockProperties.richTextColumnConfig.type,'Avancement'),value:new Text(String(action.progress))});
    for(const [key,name] of [['startDate','Début'],['dueDate','Échéance']]) if (action[key]) {
      const property = propertyFor(source, propertyPresets.datePropertyConfig.type, name);
      const meta = source.propertyMetaGet(propertyPresets.datePropertyConfig.type)!;
      const converted = meta.config.rawValue.fromString({value: action[key], data: source.propertyDataGet(property), dataSource: source});
      values.push({property, value: converted.value});
    }
    return {title: action.title, values};
  }
  function createAction(databaseId: string, source: DatabaseBlockDataSource, prepared: ReturnType<typeof prepareAction>, onCreated?: (id: string) => void) {
    // New models materialize only after Yjs observers flush. Supply title at
    // addBlock time instead of looking up an unmaterialized model mid-transaction.
    const rowId = store.addBlock('affine:paragraph', {text: new Text(prepared.title)}, databaseId);
    // Bind immediately inside the outer Yjs transaction. Even an unexpected
    // later cell failure cannot leave a saved row unbound and duplicated.
    onCreated?.(rowId);
    for (const {property, value} of prepared.values) source.cellValueChange(rowId, property, value);
    return rowId;
  }
  const addAction = (input: any, id?: string) => {
    const [action] = normalizeActionImports([{...input, sourceKey: 'manual-action'}]);
    const status = input?.status ?? 'À faire';
    if (!['À faire', 'En cours', 'En attente', 'Terminé'].includes(status)) throw new Error('invalid_action_status');
    const model = databaseModel(id ?? ensureDatabase());
    const source = sourceFor(model);
    const prepared = prepareAction(source, action, status);
    let rowId = '';
    ydoc.transact(() => {
      rowId = createAction(model.id, source, prepared, createdId => {
        if (action.sourceUrl) actionBindings.set(`manual-action:${createdId}`, {databaseId: model.id, rowId: createdId, sourceUrl: action.sourceUrl});
      });
    }, ydoc.clientID);
    return {databaseId: model.id, rowId};
  };
  const updateAction = (rowId:string,input:any,id?:string)=>{
    if(disposed)throw new Error('editor_unmounted');
    const model=databaseModel(id??ensureDatabase()),source=sourceFor(model);
    if(!source.rows$.value.includes(rowId))throw new Error('native_action_missing');
    const existingStatus=source.properties$.value.find(property=>source.propertyTypeGet(property)==='select'&&/^statut(?: \d+)?$/u.test(source.propertyNameGet(property).trim().toLocaleLowerCase('fr')));
    const allowedStatuses=mergeStatusOptions(existingStatus?source.propertyDataGet(existingStatus).options??[]:[]).map(option=>option.value);
    const patch=normalizeActionPatch(input,allowedStatuses);
    const dateValue=(name:string)=>{const property=source.properties$.value.find(id=>source.propertyNameGet(id)===name&&source.propertyTypeGet(id)===propertyPresets.datePropertyConfig.type);if(!property)return '';const value=source.cellValueGet(rowId,property);return value==null?'':source.propertyMetaGet(propertyPresets.datePropertyConfig.type)!.config.rawValue.toString({value,data:source.propertyDataGet(property),dataSource:source});};
    const start=Object.hasOwn(patch,'startDate')?patch.startDate:dateValue('Début'),end=Object.hasOwn(patch,'dueDate')?patch.dueDate:dateValue('Échéance');
    if(start&&end&&start>end)throw new Error('invalid_action_range');
    const values:{property:string;value:any}[]=[];
    for(const [key,name] of [['description','Description'],['owner','Responsable'],['priority','Priorité']]){
      if(Object.hasOwn(patch,key))values.push({property:propertyFor(source,databaseBlockProperties.richTextColumnConfig.type,name),value:patch[key]?new Text(patch[key]):null});
    }
    if(Object.hasOwn(patch,'status')){const status=statusProperty(source);values.push({property:status.id,value:status.options.find(option=>option.value===patch.status)!.id});}
    if(Object.hasOwn(patch,'progress'))values.push({property:propertyFor(source,databaseBlockProperties.richTextColumnConfig.type,'Avancement'),value:patch.progress===''?null:new Text(String(patch.progress))});
    for(const [key,name] of [['startDate','Début'],['dueDate','Échéance']])if(Object.hasOwn(patch,key)){
      const property=propertyFor(source,propertyPresets.datePropertyConfig.type,name);
      const converted=patch[key]?source.propertyMetaGet(propertyPresets.datePropertyConfig.type)!.config.rawValue.fromString({value:patch[key],data:source.propertyDataGet(property),dataSource:source}).value:null;
      values.push({property,value:converted});
    }
    ydoc.transact(()=>{if(Object.hasOwn(patch,'title'))store.updateBlock(store.getModelById(rowId)!,{text:new Text(patch.title)});for(const value of values)source.cellValueChange(rowId,value.property,value.value);},ydoc.clientID);
    scheduleMetadata();return {databaseId:model.id,rowId};
  };
  const importActions = (inputs: any[], id?: string) => {
    const actions = normalizeActionImports(inputs);
    const partition = partitionActionImports(actions, actionBindings, rowId => {
      const row = store.getModelById(rowId);
      return !!row && store.getParent(row)?.flavour === 'affine:database';
    });
    if (!partition.create.length) return freezeSnapshot({databaseId: id ?? store.getBlocksByFlavour('affine:database')[0]?.model.id ?? null, created: [], existing: partition.existing, deleted: partition.deleted, duplicates: partition.duplicates});
    const model = databaseModel(id ?? ensureDatabase());
    const source = sourceFor(model);
    const prepared = partition.create.map(action => ({action, prepared: prepareAction(source, action)}));
    const created: any[] = [];
    ydoc.transact(() => {
      for (const {action, prepared: item} of prepared) {
        createAction(model.id, source, item, rowId => {
          const binding = {databaseId: model.id, rowId, sourceUrl: action.sourceUrl ?? null};
          actionBindings.set(action.sourceKey, binding);
          created.push({sourceKey: action.sourceKey, ...binding});
        });
      }
    }, ydoc.clientID);
    return freezeSnapshot({databaseId: model.id, created, existing: partition.existing, deleted: partition.deleted, duplicates: partition.duplicates});
  };
  scheduleMetadata();
  return {
    getState, getText, getNotesText, getDatabases, getMetadata, save, addBlock, addParagraph, addDatabase, ensureDatabase, setDatabaseView, setPresentation, setStructureOpen, addAction, updateAction, importActions, capabilities,
    get presentation() { return presentation; },
    get structureOpen() { return structureOpen; },
    get dirty() { return dirty; },
    get revisionHash() { return revisionHash; },
    get store() { return store; },
    unmount() {
      disposed = true; ydoc.off('update', change); host.removeEventListener('keydown', structureKeydown); host.remove(); mobileDatabases.remove();
      viewObserver.disconnect(); for (const subscription of viewSubscriptions.values()) subscription.dispose(); viewSubscriptions.clear();
      store.dispose(); workspace.dispose(); container.classList.remove('travaux-native-editor', 'affine-page-viewport');
      if (previousPresentation === null) container.removeAttribute('data-native-presentation'); else container.setAttribute('data-native-presentation', previousPresentation);
      if (previousStructure === null) container.removeAttribute('data-native-structure-open'); else container.setAttribute('data-native-structure-open', previousStructure);
      if (previousTabindex === null) container.removeAttribute('tabindex'); else container.setAttribute('tabindex', previousTabindex);
    },
  };
}
