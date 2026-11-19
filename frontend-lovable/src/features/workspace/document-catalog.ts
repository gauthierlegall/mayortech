import type {DocumentRecord,ProjectRecord} from './ProjectPanels.types';
export interface CatalogueMoney {amount:string;currency:string;basis:string}
export interface CatalogueDocument {document:DocumentRecord;verified:boolean;version:number|null;family:string;status:string;statusLabel:string;amount:CatalogueMoney|null;mailSourceId:string;catalogueSourceId:string}
const object=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
const string=(value:unknown)=>typeof value==='string'?value:'';
const sha=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{64}$/i.test(value)?value.toLowerCase():'';
const canonical=(value:unknown):string=>JSON.stringify(value&&typeof value==='object'?(Array.isArray(value)?value.map(item=>JSON.parse(canonical(item))):Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,JSON.parse(canonical(item))]))):value);
const statusLabels:Record<string,string>={validated:'Validé',under_review:'En examen',replaced:'Remplacé'};

function moneySupported(value:unknown,quote:string):CatalogueMoney|null{
 const raw=object(value),amount=string(raw.amount),currency=string(raw.currency),basis=string(raw.basis);
 if(!/^\d{1,12}\.\d{2}$/.test(amount)||!/^[A-Z]{3}$/.test(currency)||!['HT','TTC'].includes(basis))return null;
 if(!(quote.includes(currency)||(currency==='EUR'&&quote.includes('€')))||!new RegExp(`\\b${basis}\\b`,'i').test(quote))return null;
 const decimal=(text:string)=>text.replace(/[\s\u00a0\u202f]/g,'').replace(',','.').replace(/^0+(?=\d)/,'');
 if(![...quote.matchAll(/\d[\d\s\u00a0\u202f]*[.,]\d{2}/g)].some(match=>decimal(match[0])===decimal(amount)))return null;
 return {amount,currency,basis};
}

/** Every decorated value is backed by the exact original, ledger text and quotes.
 * A document's name is never used to guess its version, status, family or amount.
 */
export function resolveDocumentCatalog(project:ProjectRecord,documents:DocumentRecord[]):{items:CatalogueDocument[];warnings:string[]}{
 const rows:{value:Record<string,unknown>;catalogueSourceId:string}[]=[],warnings:string[]=[];
 const sources=new Map(project.sources.filter(source=>source.project_ids.includes(project.id)).map(source=>[source.id,source]));
 for(const catalogue of project.sources){
  if(!sources.has(catalogue.id)||!Array.isArray(catalogue.metadata.document_catalog))continue;
  // This note is a server/operator document, never an arbitrary imported mail.
  if(!catalogue.metadata.note_id||catalogue.metadata.source_kind!=='demo_document_catalog')continue;
  const declared=catalogue.metadata.document_catalog;
  let recorded:unknown;
  try{recorded=JSON.parse(catalogue.body.slice(catalogue.body.indexOf('[')));}catch{warnings.push('Un catalogue documentaire n’a pas pu être vérifié.');continue;}
  if(canonical(declared)!==canonical(recorded)){warnings.push('Un catalogue documentaire ne correspond pas à sa source conservée.');continue;}
  for(const value of declared)rows.push({value:object(value),catalogueSourceId:catalogue.id});
 }
 const items=documents.map(document=>{
  const fallback:CatalogueDocument={document,verified:false,version:null,family:'',status:'unknown',statusLabel:'Non renseigné',amount:null,mailSourceId:document.parent_source_id,catalogueSourceId:''};
  const matches=rows.filter(row=>row.value.document_id===document.id);
  if(!matches.length)return fallback;
  if(matches.length!==1){warnings.push('Plusieurs déclarations documentaires se contredisent.');return fallback;}
  const {value:row,catalogueSourceId}=matches[0]!;
  const original=sources.get(document.source_id),mail=sources.get(string(row.mail_source_id));
  const validAssociation=Boolean(document.id&&document.source_id&&sha(document.sha256)&&row.source_id===document.source_id&&sha(row.sha256)===sha(document.sha256)&&original&&mail&&document.parent_source_id===mail.id&&original.metadata.parent_source_id===mail.id&&(!original.metadata.raw_sha256||sha(original.metadata.raw_sha256)===sha(document.sha256)));
  if(!validAssociation){warnings.push('Une association entre un document, son original et son courriel n’a pas pu être vérifiée.');return fallback;}
  const evidence=object(row.evidence);
  const proof=(key:string,originalOnly=false)=>{
   const declaration=object(evidence[key]),source=sources.get(string(declaration.source_id)),quote=string(declaration.quote);
   if(!source||!quote||quote.length>10000||!source.body.includes(quote)||(originalOnly&&source.id!==document.source_id))return null;
   return quote;
  };
  const versionProof=proof('version',true),statusProof=proof('status'),amountProof=proof('amount',true);
  const version=typeof row.version==='number'&&Number.isSafeInteger(row.version)&&row.version>0&&row.version<10000?row.version:null;
  const family=string(row.family),status=string(row.status),statusLabel=statusLabels[status];
  const quotedVersion=versionProof?/\bversion\s*[:#-]?\s*(\d+)\b/i.exec(versionProof):null;
  const amount=amountProof?moneySupported(row.amount,amountProof):null;
  if(!version||!family||!versionProof?.includes(family)||Number(quotedVersion?.[1])!==version||!statusProof||!statusLabel||row.status_label!==statusLabel||!amount){warnings.push('Une version, un montant ou un état documentaire n’est pas étayé par ses preuves exactes.');return fallback;}
  return {document,verified:true,version,family,status,statusLabel,amount,mailSourceId:mail!.id,catalogueSourceId};
 });
 return {items:items.sort((a,b)=>a.verified&&b.verified&&a.family===b.family?(a.version??0)-(b.version??0):0),warnings:[...new Set(warnings)]};
}

export function formatCatalogAmount(value:CatalogueMoney|null){
 if(!value)return '';
 return `${new Intl.NumberFormat('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value.amount))} ${value.currency==='EUR'?'€':value.currency} ${value.basis}`;
}

export interface VerifiedDocumentReview {documentId:string;status:'approved'|'under_review'|'unknown';statusLabel:string;canReview:boolean;sourceId:string;reviewer:string;origin:string}
export function verifiedDocumentReview(value:unknown,project:ProjectRecord,document:DocumentRecord):VerifiedDocumentReview|null{
 const row=object(value),status=string(row.status),labels:Record<string,string>={approved:'Validé',under_review:'En examen',unknown:'Non renseigné'};
 if(!document.id||row.document_id!==document.id||row.document_source_id!==document.source_id||!sha(document.sha256)||sha(row.sha256)!==sha(document.sha256)||!labels[status]||row.status_label!==labels[status])return null;
 if(status!=='unknown'){
  const proof=object(object(row.evidence).status),source=project.sources.find(item=>item.id===proof.source_id&&item.project_ids.includes(project.id));
  const quote=string(proof.quote),start=proof.start,end=proof.end;
  if(!source||source.id!==row.source_id||!quote||!sha(source.body_hash)||sha(proof.source_hash)!==sha(source.body_hash)||!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||(start as number)<0||(end as number)<=(start as number))return null;
  // Backend evidence ranges count Unicode code points, not UTF-16 code units.
  if(Array.from(source.body).slice(start as number,end as number).join('')!==quote)return null;
  if(row.origin==='human_decision'&&!source.metadata.note_id)return null;
  if(!['human_decision','fixture_catalogue'].includes(string(row.origin)))return null;
 }
 return {documentId:document.id,status:status as VerifiedDocumentReview['status'],statusLabel:labels[status]!,canReview:row.can_review===true,sourceId:string(row.source_id),reviewer:string(row.reviewer),origin:string(row.origin)};
}
