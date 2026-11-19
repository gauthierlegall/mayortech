/** Single-page host for the real public BlockSuite interfaces.
 * No TestWorkspace/TestDoc classes, cloud backend, or paid AFFiNE code is used.
 * Navigation/auth/metadata remain owned by the authenticated Travaux backend.
 */
import {AwarenessStore, StoreContainer, nanoid} from '@blocksuite/affine/store';
import {BlobEngine} from '@blocksuite/affine/sync';
import {NoopLogger} from '@blocksuite/affine/global/utils';
import {Subject} from 'rxjs';
import {Awareness} from 'y-protocols/awareness';
import * as Y from 'yjs';

class PageMeta {
  docMetaAdded = new Subject<string>();
  docMetaRemoved = new Subject<string>();
  docMetaUpdated = new Subject<void>();
  constructor(private readonly document: Y.Doc) {}
  private get values() { return this.document.getMap('travaux:metadata'); }
  get docMetas() { return [...this.values.values()]; }
  get docs() { return this.docMetas; }
  get properties() { return this.document.getMap('travaux:properties').toJSON(); }
  initialize() { this.values; }
  addDocMeta(value: any) { this.values.set(value.id, value); this.docMetaAdded.next(value.id); }
  getDocMeta(id: string) { return this.values.get(id); }
  setDocMeta(id: string, changes: any) {
    const previous = this.values.get(id);
    if (!previous) throw new Error('page_metadata_missing');
    this.values.set(id, {...previous, ...changes}); this.docMetaUpdated.next();
  }
  removeDocMeta() { throw new Error('delete_page_via_authenticated_backend'); }
  setProperties(values: any) {
    this.document.transact(() => {
      const properties = this.document.getMap('travaux:properties');
      for (const [key, value] of Object.entries(values)) properties.set(key, value);
    });
  }
  dispose() { this.docMetaAdded.complete(); this.docMetaRemoved.complete(); this.docMetaUpdated.complete(); }
}

class NativeDocument {
  ready = false;
  loaded = true;
  private readonly stores = new StoreContainer(this as any);
  constructor(readonly id: string, readonly workspace: NativeWorkspace) {}
  get rootDoc() { return this.workspace.doc; }
  get spaceDoc() { return this.workspace.doc; }
  get yBlocks() { return this.spaceDoc.getMap('blocks'); }
  get awarenessStore() { return this.workspace.awarenessStore; }
  get meta() { return this.workspace.meta.getDocMeta(this.id); }
  load(initialise?: () => void) { if (!this.ready) { initialise?.(); this.ready = true; } }
  getStore(options: any = {}) {
    return this.stores.getStore({...options, id: options.id ?? this.id,
      extensions: [...this.workspace.storeExtensions, ...(options.extensions ?? [])]});
  }
  removeStore = (options: any) => this.stores.removeStore(options);
  clear() { this.yBlocks.clear(); }
  remove() { throw new Error('delete_page_via_authenticated_backend'); }
  dispose() { this.ready = false; }
}

export class NativeWorkspace {
  readonly docs = new Map<string, NativeDocument>();
  readonly meta: PageMeta;
  readonly awarenessStore: AwarenessStore;
  readonly blobSync: BlobEngine;
  readonly idGenerator = nanoid;
  readonly slots = {docListUpdated: new Subject<void>()};
  readonly id: string;
  constructor(readonly doc: Y.Doc, readonly pageId: string, title: string,
              readonly storeExtensions: any[]) {
    this.id = `travaux-page-${pageId}`;
    this.meta = new PageMeta(doc);
    if (!this.meta.getDocMeta(pageId)) this.meta.addDocMeta({id: pageId, title, tags: [], createDate: Date.now()});
    this.awarenessStore = new AwarenessStore(new Awareness(doc));
    // Blob persistence is not implemented: reject writes instead of losing files
    // in a fake in-memory store or uploading them to a vendor service.
    this.blobSync = new BlobEngine({
      name: 'travaux-blobs-unavailable', readonly: true,
      get: async () => null,
      set: async () => { throw new Error('Les fichiers et images ne sont pas encore pris en charge dans ces pages.'); },
      delete: async () => { throw new Error('blob_storage_unavailable'); },
      list: async () => [],
    }, [], new NoopLogger());
    this.blobSync.start();
    this.docs.set(pageId, new NativeDocument(pageId, this));
  }
  getDoc(id: string) { return this.docs.get(id) ?? null; }
  createDoc(id = this.pageId) {
    if (id !== this.pageId) throw new Error('create_page_via_authenticated_backend');
    return this.docs.get(id)!;
  }
  removeDoc() { throw new Error('delete_page_via_authenticated_backend'); }
  dispose() {
    this.blobSync.stop(); this.awarenessStore.destroy(); this.meta.dispose();
    this.slots.docListUpdated.complete(); this.doc.destroy();
  }
}
