export function importedWorkbook(notes:readonly {origin?:string;content?:string}[]):{
 row:number;notionUrl:string;originalTimes:{label:string;day:string;time:string}[];unmapped:{label:string;value:string}[];
}|null;
export function mentionedDates(values:Record<string,unknown>):string[];
export function workbookSituation(values:Record<string,unknown>):{deadline:string;priority:string;observation:string;note:string};
