const BLOCKS = Object.freeze({
  text: {flavour: 'affine:paragraph', type: 'text'},
  h1: {flavour: 'affine:paragraph', type: 'h1'},
  h2: {flavour: 'affine:paragraph', type: 'h2'},
  bulleted: {flavour: 'affine:list', type: 'bulleted'},
  todo: {flavour: 'affine:list', type: 'todo'},
  quote: {flavour: 'affine:paragraph', type: 'quote'},
  divider: {flavour: 'affine:divider'},
});
const ALIASES = Object.freeze({texte: 'text', titre1: 'h1', titre2: 'h2', liste: 'bulleted', checkbox: 'todo', citation: 'quote'});
export function blockSpec(kind) {
  const canonical = ALIASES[kind] ?? kind;
  if (!Object.hasOwn(BLOCKS, canonical)) throw new Error('invalid_block_kind');
  return {...BLOCKS[canonical]};
}

export const DEFAULT_STATUSES = Object.freeze([
  Object.freeze({id: 'travaux-todo', value: 'À faire', color: '#e2e8f0'}),
  Object.freeze({id: 'travaux-in-progress', value: 'En cours', color: '#dbeafe'}),
  Object.freeze({id: 'travaux-waiting', value: 'En attente', color: '#fef3c7'}),
  Object.freeze({id: 'travaux-done', value: 'Terminé', color: '#dcfce7'}),
]);
export function mergeStatusOptions(existing = []) {
  if (!Array.isArray(existing) || existing.length > 1000) throw new Error('invalid_status_options');
  const result = existing.map(option => ({...option}));
  for (const status of DEFAULT_STATUSES) {
    if (result.some(option => option.value === status.value)) continue;
    let id = status.id;
    for (let suffix = 2; result.some(option => option.id === id); suffix += 1) id = `${status.id}-${suffix}`;
    result.push({...status, id});
  }
  return result;
}

export function normalizeActionImports(actions) {
  if (!Array.isArray(actions) || actions.length > 100) throw new Error('action_import_limit');
  return actions.map(action => {
    if (!action || typeof action !== 'object' || typeof action.sourceKey !== 'string'
        || !/^[A-Za-z0-9_.:-]{1,200}$/.test(action.sourceKey)
        || typeof action.title !== 'string' || !action.title.trim() || action.title.length > 500) throw new Error('invalid_action_import');
    const value = {sourceKey: action.sourceKey, title: action.title.trim()};
    for (const [key, maximum] of [['description', 4000], ['owner', 200], ['priority',80]]) {
      if (action[key] == null) continue;
      if (typeof action[key] !== 'string' || action[key].length > maximum) throw new Error('invalid_action_import');
      if (action[key].trim()) value[key] = action[key].trim();
    }
    if (action.sourceUrl != null && action.sourceUrl !== '') {
      if (typeof action.sourceUrl !== 'string' || !/^#\/mail\/[A-Za-z0-9_-]{1,160}$/.test(action.sourceUrl)) throw new Error('invalid_action_import');
      value.sourceUrl = action.sourceUrl;
    }
    for (const key of ['startDate','dueDate']) if (action[key] != null && action[key] !== '') {
      const date = action[key];
      if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)
          || !Number.isFinite(Date.parse(date + 'T00:00:00Z')) || new Date(date + 'T00:00:00Z').toISOString().slice(0, 10) !== date) throw new Error('invalid_action_import');
      value[key] = date;
    }
    if(value.startDate&&value.dueDate&&value.startDate>value.dueDate)throw new Error('invalid_action_range');
    if(action.progress!=null&&action.progress!==''){if(!Number.isInteger(action.progress)||action.progress<0||action.progress>100)throw new Error('invalid_action_progress');value.progress=action.progress;}
    return value;
  });
}

export function normalizeActionPatch(input,allowedStatuses=DEFAULT_STATUSES.map(status=>status.value)){
  if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(key=>!['title','description','owner','startDate','dueDate','priority','status','progress'].includes(key)))throw new Error('invalid_action_patch');
  const output={};
  for(const [key,maximum] of [['title',500],['description',4000],['owner',200],['priority',80]]){
    if(!Object.hasOwn(input,key))continue;
    if(typeof input[key]!=='string'||input[key].length>maximum||(key==='title'&&!input[key].trim()))throw new Error('invalid_action_patch');
    output[key]=input[key].trim();
  }
  if(Object.hasOwn(input,'status')){if(typeof input.status!=='string'||!Array.isArray(allowedStatuses)||!allowedStatuses.includes(input.status))throw new Error('invalid_action_status');output.status=input.status;}
  if(Object.hasOwn(input,'progress')){if(input.progress!==''&&(!Number.isInteger(input.progress)||input.progress<0||input.progress>100))throw new Error('invalid_action_progress');output.progress=input.progress;}
  for(const key of ['startDate','dueDate'])if(Object.hasOwn(input,key)){const date=input[key];if(typeof date!=='string'||(date!==''&&(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date+'T00:00:00Z'))||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date)))throw new Error('invalid_action_date');output[key]=date;}
  if(output.startDate&&output.dueDate&&output.startDate>output.dueDate)throw new Error('invalid_action_range');
  return output;
}

export function partitionActionImports(actions, bindings, hasRow) {
  const result = {create: [], existing: [], deleted: [], duplicates: []};
  const seen = new Set();
  for (const action of actions) {
    if (seen.has(action.sourceKey)) { result.duplicates.push(action.sourceKey); continue; }
    seen.add(action.sourceKey);
    const binding = bindings.get(action.sourceKey);
    if (binding) {
      if (typeof binding.databaseId !== 'string' || typeof binding.rowId !== 'string') throw new Error('invalid_action_binding');
      result[hasRow(binding.rowId) ? 'existing' : 'deleted'].push({sourceKey: action.sourceKey, databaseId: binding.databaseId, rowId: binding.rowId});
    } else result.create.push(action);
  }
  return result;
}

export function freezeSnapshot(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) freezeSnapshot(child);
    Object.freeze(value);
  }
  return value;
}
