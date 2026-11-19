type Preserver = {save: () => Promise<unknown> | unknown; dirty: () => boolean};
const preservers = new Map<symbol, Preserver>();
let pending: Promise<void> | null = null;

/** Register a real controller, not a copy of its state. Failures stop navigation. */
export function registerPreserver(save: Preserver['save'], dirty: Preserver['dirty'] = () => false) {
  const key = Symbol('workspace-panel');
  preservers.set(key, {save, dirty});
  return () => {preservers.delete(key);};
}
export function hasDirtyPanels() {return [...preservers.values()].some(panel => panel.dirty());}
export function preservePanels(): Promise<void> {
  if (!pending) pending = (async () => {for (const panel of [...preservers.values()]) await panel.save();})().finally(() => {pending = null;});
  return pending;
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (hasDirtyPanels()) {event.preventDefault();event.returnValue = '';}
});
