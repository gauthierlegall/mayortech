import type {NativeAction} from './native-actions';
export interface PlanningAction extends NativeAction {start?:string;progress?:number}
export interface CalendarEvent {id:string;title:string;start:string;end:string;all_day:boolean;calendar_name:string;project_id:string;status:string;source_url:string}
export interface GanttTask {id:string;name:string;start:string;end:string;progress:number;dependencies:string[];custom_class:string}
export function validDay(value:unknown):value is string;
export function dayFromGanttDate(value:unknown):string;
export function scheduleOf(action:{start?:string;due?:string}):{start:string;end:string}|null;
export function schedulePatch(start:string,end:string,progress:string):{startDate:string;dueDate:string;progress:string|number};
export function scheduleFormPatch(action:{owner:string;status:string},start:string,end:string,progress:string,owner:string,status:string):{startDate:string;dueDate:string;progress:string|number;owner?:string;status?:string};
export function planningActionGroups(items:NativeAction[],projects:{id:string;title:string}[]):{id:string;label:string;items:NativeAction[]}[];
export function planningOwnerChoices(_members:string[],items:NativeAction[],current:string,projectId:string):string[];
export function planningConsistencyWarning(status:string,progress:string):string;
export function planningFormDirty(action:NativeAction|null,start:string,end:string,progress:string,owner:string,status:string):boolean;
export function monthWindow(month:string):{start:string;days:string[]};
export function shiftMonth(month:string,offset:number):string;
export function timelinePlacement(start:string,end:string,windowStart:string,days:number):{column:number;span:number}|null;
export function ganttTasks(rows:PlanningAction[]):{tasks:GanttTask[];actions:Map<string,PlanningAction>};
export function calendarEventsOf(value:unknown,projectId:string):CalendarEvent[];
export function safeCalendarUrl(value:string):string|null;
export interface PlanningMilestone {id:string;label:string;date:string;sourceId?:string;confirmed:boolean}
export function timelineAction(action:{start?:string;due?:string}):{kind:'range'|'deadline';start:string;end:string}|null;
export function planningMilestones(project:{facts?:{id:string;label:string;status:string;kind:string;field:string;value:unknown;source_id?:string}[];properties?:{values?:Record<string,unknown>}},deadline?:string):PlanningMilestone[];
export function timelineOverview(groups:{project:Parameters<typeof planningMilestones>[0];actions:NativeAction[];deadline?:string}[],month:string):{hasDates:boolean;visibleCount:number;nearestMonth:string|null};
export function loadPlanningProjects<T>(ids:string[],read:(id:string)=>Promise<T>):Promise<{projects:T[];failed:number}>;
