export interface WorkCommission {id:string;name:string;code?:string;role?:string;can_read:boolean;can_edit?:boolean;capabilities?:{can_read?:boolean;can_edit?:boolean};active?:boolean}
export interface WorkProfile {status:'inactive'|'ready'|'choose'|'unavailable';commissionId:string|null;changed:boolean}
export interface WorkProfileSnapshot {identity:string;session:unknown;bootstrap:unknown;hasProjects:boolean}
export function authorizedCommissions(bootstrap:unknown):WorkCommission[];
export function workProfilePreferenceKey(session:unknown):string|null;
export function resolveWorkProfile(session:unknown,bootstrap:unknown,saved:unknown,hasProjects?:boolean):WorkProfile;
export function commissionRequestFilter(bootstrap:unknown,commissionId:string):{commission_id?:string};
export function changeWorkProfile(options:{commissionId:string;snapshot:()=>WorkProfileSnapshot;preserve:()=>Promise<unknown>;commit:(id:string)=>void}):Promise<void>;
