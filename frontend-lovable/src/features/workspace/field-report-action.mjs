/** Input for the existing native import, never a second action store. */
export function fieldReportAction(report,dueDate){
 if(!report||typeof report.id!=='string'||!/^[a-f0-9-]{36}$/i.test(report.id)||typeof report.title!=='string'||!report.title.trim()||report.title.length>160||typeof report.detail!=='string'||typeof report.author!=='string'||report.author.length>200)throw Error('Le constat reçu est incomplet. Actualisez les constats.');
 const day=typeof dueDate==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(dueDate)?new Date(dueDate+'T12:00:00Z'):null;
 if(!day||!Number.isFinite(day.getTime())||day.toISOString().slice(0,10)!==dueDate)throw Error('Choisissez une échéance valide pour l’action.');
 return {sourceKey:'field-report:'+report.id,title:report.title,description:report.detail.slice(0,3600)+`\n\nConstat terrain : ${report.id}. Rapport complet dans Suivi terrain.`,owner:report.author,dueDate,priority:report.kind==='Visite'?'Normale':'Haute',status:'À faire'};
}

export function fieldReportLink(sourceKey,result,metadata,pageId){
 if(result?.deleted?.some(item=>item.sourceKey===sourceKey))throw Error('L’action de ce constat a été supprimée du suivi. Elle ne sera pas recréée automatiquement.');
 for(const database of metadata?.databases||[]){
  const row=database.rows?.find(item=>item.sourceKey===sourceKey);
  if(row&&typeof row.id==='string'&&typeof database.id==='string'&&typeof pageId==='string')return {page_id:pageId,database_id:database.id,row_id:row.id};
 }
 throw Error('L’action native ne peut pas être retrouvée. Actualisez le suivi avant de réessayer.');
}
