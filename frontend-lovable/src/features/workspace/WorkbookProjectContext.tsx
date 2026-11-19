import {formatDate} from './model';
import {mentionedDates,workbookSituation,type importedWorkbook} from './project-import-model.mjs';
import {textOf,type ProjectRecord} from './ProjectPanels.types';
import {statusLabel} from '../../../../web/model.js';
import './workbook-project-context.css';

const currency=new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'});
const amount=(value:unknown)=>typeof value==='string'&&/^-?\d+(?:\.\d+)?$/.test(value)&&Number.isFinite(Number(value))?currency.format(Number(value)):'';

export function WorkbookProjectContext({project,source}:{project:ProjectRecord;source:NonNullable<ReturnType<typeof importedWorkbook>>}){
 const values=project.properties?.values??{};
 const situation=workbookSituation(values),status=project.status&&project.status!=='unknown'?statusLabel(project.status):'';
 const deadline=formatDate(situation.deadline,'',true);
 const items=[
  ['Date de la demande',formatDate(textOf(values.request_date),'',true)],['Échéance du dossier',formatDate(textOf(values.deadline),'',true)],
  ['Demandeur',textOf(values.requester)],['Service / Responsable',textOf(values.service_owner)],
  ['Entreprise',textOf(values.contractor)],['Lieu',textOf(values.location)],['Catégorie',textOf(values.category)],['Priorité',textOf(values.priority)],
  ['Coût estimé',amount(values.estimated_cost)],['Coût réel',amount(values.actual_cost)],
 ].filter(([,value])=>value.trim());
 const dates=mentionedDates(values);
 return <section className="workbook-project-context" aria-label="Données importées du classeur">
  <div className="workbook-situation">
   <h3>Résumé du chantier</h3>
   <dl>
    <div><dt>Statut</dt><dd>{status||'Non renseigné'}</dd></div>
    {situation.priority&&<div><dt>Priorité</dt><dd>{situation.priority}</dd></div>}
    <div><dt>Échéance</dt><dd>{deadline||'Non renseignée'}</dd></div>
   </dl>
   {(situation.observation||situation.note)&&<div className="workbook-situation-excerpts">
    {situation.observation&&<p><strong>Observation</strong> {situation.observation}</p>}
    {situation.note&&<p><strong>Note de suivi</strong> {situation.note}</p>}
   </div>}
   {!situation.observation&&!situation.note&&<p>Aucune note de suivi ni observation dans le dossier importé.</p>}
  </div>
  {items.length>0&&<dl>{items.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
  {(situation.observation.endsWith('…')||situation.note.endsWith('…'))&&<details className="workbook-context-text">
   <summary>Lire les notes et observations complètes</summary>
   {textOf(values.observation)&&<div><h3>Observation</h3><p>{textOf(values.observation)}</p></div>}
   {textOf(values.notes)&&<div><h3>Notes du dossier</h3><p>{textOf(values.notes)}</p></div>}
  </details>}
  <details><summary>Source Excel · ligne {source.row}</summary>
    {dates.length>0&&<p><strong>Dates mentionnées dans les notes et observations</strong> {dates.map(day=>formatDate(day,'',true)).join(', ')}</p>}
    {source.originalTimes.length>0&&<ul>{source.originalTimes.map(item=><li key={item.label}>{item.label} dans Excel · {formatDate(item.day,'',true)} à {item.time}</li>)}</ul>}
    {source.unmapped.length>0&&<dl>{source.unmapped.map(item=><div key={item.label}><dt>{item.label} · valeur d’origine</dt><dd>{item.value}</dd></div>)}</dl>}
    {source.notionUrl&&<p><a href={source.notionUrl} target="_blank" rel="noopener noreferrer">Ouvrir la fiche Notion d’origine</a></p>}
  </details>
 </section>;
}
