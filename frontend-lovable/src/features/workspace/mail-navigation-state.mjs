// Event scope travels with the producer; the receiving actor must not assign it.
export function workspaceMailIdentity(session){
 return JSON.stringify([session?.actor?.tenant_id||'',session?.actor?.actor_id||'',session?.auth_required===true]);
}

export function mailFolderUnread(detail,identity){
 if(typeof identity!=='string'||!detail||typeof detail!=='object'||Array.isArray(detail)
  ||detail.identity!==identity||!Array.isArray(detail.items))return null;
 const inbox=detail.items.find(item=>item?.id==='inbox');
 return Number.isSafeInteger(inbox?.unread)&&inbox.unread>=0?inbox.unread:null;
}
