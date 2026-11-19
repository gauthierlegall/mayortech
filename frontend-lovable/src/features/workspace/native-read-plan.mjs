/** Only existing saved native state or explicit confirmed actions need an editor. */
export function nativePageMayHaveActions(page){
 if(typeof page?.state_base64!=='string'||!page.state_base64)return false;
 if(page.editor_version!=='blocksuite-0.22.4')return true;
 try{
  const state=atob(page.state_base64);
  // V1 writes the block flavour strings literally. Unknown structure stays readable.
  if(!state.includes('affine:page')||!state.includes('affine:note'))return true;
  return state.includes('affine:database')||state.includes('actionDatabaseId');
 }catch{return true;}
}
export function nativeReadPlan(projectIds,rawPages,confirmedProjectIds=[],canWrite=false){
 const pages=Array.isArray(rawPages)?rawPages:Array.isArray(rawPages?.items)?rawPages.items:null;
 if(!pages||pages.some(page=>!page||typeof page.id!=='string'||!page.id||typeof page.project_id!=='string'||!page.project_id))throw Error('La liste des pages n’a pas pu être chargée. Actualisez les actions.');
 const allowed=new Set(projectIds),confirmed=new Set(confirmedProjectIds),byProject=new Map();
 for(const page of pages)if(allowed.has(page.project_id)&&(page.kind==='main'||page.kind===undefined)&&!byProject.has(page.project_id))byProject.set(page.project_id,page);
 const load=[],empty=[];
 for(const projectId of [...allowed]){
  const page=byProject.get(projectId),entry={projectId,page};
  if(nativePageMayHaveActions(page)||canWrite&&confirmed.has(projectId))load.push(entry);
  else empty.push(entry);
 }
 return {load,empty};
}
