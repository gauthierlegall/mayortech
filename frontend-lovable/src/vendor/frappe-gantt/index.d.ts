/** Travaux boundary types for Frappe Gantt 1.2.2 and the local disposal method. */
export default class Gantt {
 constructor(host:HTMLElement,tasks:{id:string;name:string;start:string;end:string;progress?:number;dependencies?:string[]|string;custom_class?:string}[],options:Record<string,unknown>);
 config:{column_width:number};
 destroy():void;
}
