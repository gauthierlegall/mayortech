export const workspaceIdentityEvent='travaux:workspace-identity';
export const workspaceAccessEvent='travaux:workspace-access';
export function workspaceIdentity(session){return JSON.stringify([session?.authenticated===true,session?.actor?.tenant_id,session?.actor?.actor_id,session?.actor?.role,session?.account?.id]);}
export function workspaceProjectSet(ids){return JSON.stringify([...new Set(ids)].sort());}
/** Announce a verified server session before any fallible business-data request. */
export function observeWorkspaceIdentity(session){const key=workspaceIdentity(session);if(typeof window!=='undefined')window.dispatchEvent(new CustomEvent(workspaceIdentityEvent,{detail:{key}}));return key;}
export function observeWorkspaceAccess(key,ids){if(typeof window!=='undefined')window.dispatchEvent(new CustomEvent(workspaceAccessEvent,{detail:{key,projects:workspaceProjectSet(ids)}}));}
