export interface FieldReportActionSource{id:string;project_id:string;title:string;detail:string;author:string;kind:string}
export function fieldReportAction(report:FieldReportActionSource,dueDate:string):{sourceKey:string;title:string;description:string;owner:string;dueDate:string;priority:string;status:string};
export function fieldReportLink(sourceKey:string,result:unknown,metadata:unknown,pageId:string):{page_id:string;database_id:string;row_id:string};
