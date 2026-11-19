export function projectNotesPreview(notes,sources,projection){
  let status='ready';
  const result=[];
  for(const note of notes){
    if(['human_property','human_field_report','local_workbook_import'].includes(note.origin)||!note.content.trim())continue;
    if(note.origin!=='manual_affine'){result.push(note);continue;}
    if(!projection||projection.status==='loading'){status=status==='unavailable'?status:'loading';continue;}
    const source=sources.find(source=>source.id===note.source_id);
    const matches=projection.status==='ready'&&typeof projection.pageId==='string'
      &&source?.metadata?.remote_id===`affine:${projection.pageId}`
      &&typeof projection.fullText==='string'&&projection.fullText.trim()===note.content.trim()
      &&typeof projection.text==='string';
    if(matches)result.push({...note,content:projection.text,actionsOnly:!projection.text.trim()});
    else{status='unavailable';result.push(note);}
  }
  return {notes:result,status};
}
