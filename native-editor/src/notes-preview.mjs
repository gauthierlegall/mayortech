// Read projection over detached SDK snapshots. The original snapshot and Yjs
// document are never modified; only an explicit managed database ID may vanish.
export function notesSnapshot(snapshot,managedActionDatabaseId){
  const copy=structuredClone(snapshot);
  if(typeof managedActionDatabaseId!=='string'||!managedActionDatabaseId)return copy;
  const visit=node=>{
    if(!node||typeof node!=='object')return;
    if(Array.isArray(node.children)){
      node.children=node.children.filter(child=>!(child?.id===managedActionDatabaseId&&child.flavour==='affine:database'));
      node.children.forEach(visit);
    }
  };
  visit(copy.blocks);
  return copy;
}
