export interface NativeReadPage {id:string;project_id:string;kind?:string;state_base64?:string|null;text?:string;revision_hash?:string|null;editor_version?:string}
export interface NativeReadEntry {projectId:string;page?:NativeReadPage}
export function nativePageMayHaveActions(page:unknown):boolean;
export function nativeReadPlan(projectIds:string[],rawPages:unknown,confirmedProjectIds?:string[],canWrite?:boolean):{load:NativeReadEntry[];empty:NativeReadEntry[]};
