export const assistantOpenEvent='travaux:open-assistant';
export interface OpenAssistantDetail {projectId?:string}
export function openAssistant(projectId?:string){
 if(typeof window!=='undefined')window.dispatchEvent(new CustomEvent<OpenAssistantDetail>(assistantOpenEvent,{detail:{projectId}}));
}
