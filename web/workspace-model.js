const views = new Set(['page','table','kanban','documents','exchanges','memory','notes','sources']);
export const workspaceView = value => views.has(value) ? value : 'page';

export function actionInputs(actions=[]) {
  const seen=new Set(), output=[];
  for(const action of actions) {
    if(!action || typeof action.id!=='string' || !action.id || seen.has(action.id))continue;
    const value=action.value;
    const title=typeof value==='string'?value:value?.title||value?.action||value?.text||value?.description||action.title||'';
    if(!String(title).trim())continue;
    const source=action.source_id||action.citations?.[0]?.source_id||action.evidence?.[0]?.source_id;
    const originalTitle=String(title).trim();
    const deadline=typeof value==='object'?String(value?.due_date||value?.deadline||''):'';
    const parsedDate=/^\d{4}-\d{2}-\d{2}$/.test(deadline)?new Date(deadline+'T00:00:00Z'):null;
    const dueDate=parsedDate&&Number.isFinite(parsedDate.getTime())&&parsedDate.toISOString().slice(0,10)===deadline?deadline:'';
    const description=[originalTitle.length>500?originalTitle:'',typeof value==='object'&&value?.description!==title?String(value?.description||''):'',deadline&&!dueDate?`Échéance annoncée : ${deadline}`:''].filter(Boolean).join('\n');
    output.push({sourceKey:action.id,title:originalTitle.length>500?originalTitle.slice(0,499)+'…':originalTitle,
      description:description.length>4000?description.slice(0,3950)+'… Voir le courriel complet.':description,
      owner:(typeof value==='object'?String(value?.assignee||value?.owner||value?.responsible||''):'').slice(0,200),
      dueDate,
      sourceUrl:source?`#/mail/${encodeURIComponent(source)}`:''});
    seen.add(action.id);
  }
  return output;
}

export function fileSize(bytes) {
  if(!Number.isFinite(bytes)||bytes<0)return 'Taille inconnue';
  return bytes<1024?`${bytes} o`:bytes<1024**2?`${Math.ceil(bytes/1024)} Ko`:`${(bytes/1024**2).toFixed(1)} Mo`;
}
