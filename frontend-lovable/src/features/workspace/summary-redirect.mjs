const identifier=value=>typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$/.test(value);
/** Old bookmarks resolve through the authorized API; no global summary surface remains. */
export async function resolveSummaryDestination(api,id,projectIds){
 if(!identifier(id))return '#/';
 try{
  const summary=await api.summary(id),projectId=summary?.project_id;
  if(summary?.id!==id||!identifier(projectId)||!Array.isArray(projectIds)||!projectIds.includes(projectId))return '#/';
  return `#/chantiers/${encodeURIComponent(projectId)}?view=page`;
 }catch{return '#/';}
}
