/** Native SDK extension points only: the board, groups, rows and drag handlers
 * remain BlockSuite. Empty null groups are not seeded; real null rows recreate
 * them through the upstream GroupTrait.groupDataMap implementation. */
import {ExternalGroupByConfigProvider, groupByMatchers} from '@blocksuite/data-view';

const nativeSelect = groupByMatchers.find(config => config.name === 'select')!;
if (!nativeSelect) throw new Error('native_select_grouping_unavailable');
const selectGrouping = {
  ...nativeSelect,
  defaultKeys: (type: any) => nativeSelect.defaultKeys(type).filter(group => group.value != null),
  groupName: (type: any, value: any) => value == null ? 'Sans statut' : nativeSelect.groupName(type, value),
  view: (element: HTMLElement, props: any, expose: any) => {
    if (props.group.value != null) return nativeSelect.view(element, props, expose);
    const label = document.createElement('span'); label.textContent = 'Sans statut';
    element.append(label); expose({});
    return {update: () => {}, unmount: () => label.remove()};
  },
};
const key = ExternalGroupByConfigProvider('select');
export const compactGroupingExtension = {setup: (di: any) => di.addValue(key, selectGrouping)};
export function configureGrouping(source: any) {
  if (!source.serviceGet(key)) source.serviceSet(key, selectGrouping);
  return source;
}

export function compactKanban(source: any, view: any) {
  if (view.type !== 'kanban') return;
  const ids = source.properties$.value;
  const data = view.data$.value;
  const present = new Set(data.columns.map((column: any) => column.id));
  const missing = ids.filter((id: string) => !present.has(id));
  if (missing.length) view.dataUpdate((current: any) => ({columns: [...current.columns, ...missing.map((id: string) => ({id}))]}));
  for (const id of ids) {
    const name = source.propertyNameGet(id);
    const hideByDefault = id === data.groupBy?.columnId || ['Description', 'Montant indiqué', 'Échange'].includes(name);
    const column = view.data$.value.columns.find((column: any) => column.id === id);
    // An explicit human visibility choice (true/false) is retained.
    if (hideByDefault && column?.hide === undefined) view.propertyGetOrCreate(id).hideSet(true);
  }
  if (view.data$.value.header?.iconColumn === 'type') {
    const {iconColumn: _placeholder, ...header} = view.data$.value.header;
    view.dataUpdate(() => ({header}));
  }
}
