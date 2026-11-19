export function canLogoutWorkspace(session:unknown):boolean;
export function logoutWorkspace(options:{session:unknown;api:{logout:()=>Promise<unknown>};preserve:()=>Promise<unknown>;assertCurrent:()=>void;onRevoked:()=>void;redirect:()=>void}):Promise<void>;
