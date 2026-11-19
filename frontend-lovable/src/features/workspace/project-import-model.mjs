import {validDay} from './planning-model.mjs';

const labels={priority:'Priorité',status:'Statut',attachments:'Pièces jointes'};

function notionLink(value){
 if(typeof value!=='string'||value.length>2000||/[\s\\]/.test(value))return '';
 try{
  const url=new URL(value);
  const validHost=['notion.so','notion.com','notion.site'].some(host=>url.hostname===host||url.hostname.endsWith(`.${host}`));
  if(url.protocol==='https:'&&validHost&&!url.username&&!url.password&&!url.port&&!url.search&&!url.hash&&
     /(?:[a-f0-9]{32}|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})\/?$/i.test(url.pathname))return url.href;
 }catch{/* Keep the source readable if its old link is no longer valid. */}
 return '';
}

export function importedWorkbook(notes){
 for(const note of notes){
  if(note.origin!=='local_workbook_import'||typeof note.content!=='string')continue;
  let row;
  try{row=JSON.parse(note.content);}catch{continue;}
  if(row?.schema!=='mayortech.local-workbook-import/v1'||!Number.isSafeInteger(row.row_number)||row.row_number<2)continue;
  const originalTimes=(Array.isArray(row.source_cells)?row.source_cells:[]).flatMap(cell=>{
   const parts=cell?.type==='datetime'&&typeof cell.value==='string'?/^(\d{4}-\d\d-\d\d)T(\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)?)$/.exec(cell.value):null;
   return parts&&validDay(parts[1])&&!parts[2].startsWith('00:00:00')&&typeof cell.header==='string'?
    [{label:cell.header,day:parts[1],time:parts[2]}]:[];
  });
  const unmapped=(Array.isArray(row.unmapped_values)?row.unmapped_values:[]).flatMap(item=>{
   const label=item&&Object.hasOwn(labels,item.field)?labels[item.field]:'';
   const value=typeof item?.value==='string'?item.value.trim():'';
   return label&&value?[{label,value}]:[];
  });
  return {row:row.row_number,originalTimes,unmapped,notionUrl:notionLink(row.notion_reference?.url)};
 }
 return null;
}

export function mentionedDates(values){
 const dates=new Set();
 for(const key of ['notes','observation']){
  const value=values[key];
  if(typeof value!=='string')continue;
  for(const match of value.matchAll(/(?<![\d-])(?:(\d{4}-\d{2}-\d{2})|(\d{1,2})\/(\d{1,2})\/(\d{4}))(?![\d-])/g)){
   const day=match[1]||`${match[4]}-${match[3].padStart(2,'0')}-${match[2].padStart(2,'0')}`;
   if(validDay(day)&&day!==values.deadline&&day!==values.request_date)dates.add(day);
  }
 }
 return [...dates].sort();
}

export function workbookSituation(values){
 const asText=value=>typeof value==='string'?value.trim().replace(/\s+/g,' '):'';
 const excerpt=value=>{
  const text=asText(value);
  if(text.length<=360)return text;
  const limit=text.lastIndexOf(' ',359);
  return text.slice(0,limit>280?limit:359)+'…';
 };
 const observation=excerpt(values.observation),note=excerpt(values.notes);
 return {
  deadline:validDay(values.deadline)?values.deadline:'',
  priority:asText(values.priority),
  observation,
  note:note===observation?'':note,
 };
}
