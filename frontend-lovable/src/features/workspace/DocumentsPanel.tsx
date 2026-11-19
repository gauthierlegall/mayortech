import {useEffect,useMemo,useRef,useState} from 'react';
import {FileText,Download,ExternalLink,Check,Mail,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from './context';
import {documentOf,projectOf,resultItems,type DocumentRecord,type ProjectRecord} from './ProjectPanels.types';
import {formatDate} from './model';
import {formatCatalogAmount,resolveDocumentCatalog,verifiedDocumentReview,type CatalogueDocument} from './document-catalog';
import {DocumentUpload} from './Documents';
import {DocumentSignatureCircuit} from './DocumentSignatureCircuit';

/** The original Lovable document surface, backed by verified originals and decisions. */
export function DocumentsPanel({project,documents,onSource,onMail}:{project:ProjectRecord;documents:DocumentRecord[];onSource:(id:string)=>void;onMail:(id:string)=>void}){
 const {api,refresh,session,bootstrap}=useWorkspace();
 const [currentProject,setCurrentProject]=useState(project),[files,setFiles]=useState(documents),[reviews,setReviews]=useState<unknown[]>([]),[reviewRevision,setReviewRevision]=useState<number|null>(null);
 const [selected,setSelected]=useState<string|null>(null),[loading,setLoading]=useState(false),[busy,setBusy]=useState<string|null>(null),[error,setError]=useState(''),[feedback,setFeedback]=useState(''),[retry,setRetry]=useState(0),[previewError,setPreviewError]=useState(false);
 const alive=useRef(true),epoch=useRef(0),opener=useRef<HTMLElement|null>(null);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;epoch.current++;};},[]);
 async function load(force=false){
  const token=++epoch.current;setLoading(true);setError('');
  try{
   if(typeof api.documentReviews!=='function')throw new Error('Les décisions documentaires ne sont pas disponibles. Les originaux restent consultables.');
   const decisions=await api.documentReviews(project.id);
   if(decisions?.project_id!==project.id||!Number.isSafeInteger(decisions.project_revision)||!Array.isArray(decisions.items))throw new Error('Les décisions reçues ne correspondent pas à ce dossier. Rechargez-le.');
   let detail=project,nextFiles=documents;
   if(force||decisions.project_revision!==project.revision){const values=await Promise.all([api.project(project.id),api.documents(project.id)]);detail=projectOf(values[0]);nextFiles=resultItems(values[1]).map(documentOf).filter(item=>item.kind!=='email'&&item.kind!=='eml');}
   if(!alive.current||token!==epoch.current)return;
   setCurrentProject(detail);setFiles(nextFiles);setReviews(decisions.items);setReviewRevision(decisions.project_revision);
  }catch(cause){if(alive.current&&token===epoch.current){setReviews([]);setReviewRevision(null);setError(cause instanceof Error?cause.message:'Les décisions n’ont pas pu être chargées. Réessayez.');}throw cause;}
  finally{if(alive.current&&token===epoch.current)setLoading(false);}
 }
 useEffect(()=>{setCurrentProject(project);setFiles(documents);setFeedback('');void load().catch(()=>{});},[project.id,project.revision,documents,api,retry]);
 const catalogue=useMemo(()=>resolveDocumentCatalog(currentProject,files),[currentProject,files]);
 const states=new Map(catalogue.items.map(item=>{const raw=reviews.find((row:any)=>row?.document_id===item.document.id);return [item.document.id,raw?verifiedDocumentReview(raw,currentProject,item.document):null] as const;}));
 const selectedDocument=catalogue.items.find(item=>(item.document.id||item.document.source_id)===selected)??null;
 const open=(item:CatalogueDocument,button:HTMLElement)=>{opener.current=button;setPreviewError(false);setSelected(item.document.id||item.document.source_id);};
 const status=(item:CatalogueDocument)=>states.get(item.document.id)?.statusLabel??(item.verified?item.statusLabel:'Non renseigné');
 const received=(item:CatalogueDocument)=>currentProject.sources.find(source=>source.id===item.mailSourceId)?.received_at||item.document.created_at;
 const sourceMail=(item:CatalogueDocument)=>item.mailSourceId?onMail(item.mailSourceId):onSource(item.document.preview_source_id||item.document.source_id);
 async function validate(item:CatalogueDocument){
  const state=states.get(item.document.id);
  if(!item.document.id||!state?.canReview||state.status!=='under_review'||reviewRevision===null||busy||typeof api.reviewDocument!=='function')return;
  if(!window.confirm('Valider ce devis ? Votre décision sera conservée avec cet original. Les versions précédentes resteront consultables.'))return;
  setBusy(item.document.id);setError('');setFeedback('');let recorded=false;
  try{
   await api.reviewDocument(item.document.id,{decision:'approve',expected_project_revision:reviewRevision,reason:'Validation explicite de ce document depuis la liste des pièces.'});recorded=true;
   await load(true);if(alive.current)setFeedback('Document validé. La décision et sa preuve sont conservées.');
   await refresh();
  }catch(cause){if(alive.current)setError(recorded?'La décision a été enregistrée, mais le dossier n’a pas pu être rechargé. Réessayez pour consulter son état actuel.':cause instanceof Error?cause.message:'La décision n’a pas pu être enregistrée. Rechargez le dossier avant de réessayer.');}
  finally{if(recorded)window.dispatchEvent(new CustomEvent('travaux:document-decision',{detail:{projectId:project.id}}));if(alive.current)setBusy(null);}
 }
 return <section>
  <div className="section-heading"><h2>Documents <span>{files.length}</span></h2><span className="muted-label">Originaux et versions conservés</span></div>
  <DocumentUpload key={project.id} projectId={project.id} onUploaded={async()=>{await load(true);await refresh();}}/>
  {error&&<div className="source-callout" role="alert"><p>{error}</p><Button variant="link" onClick={()=>setRetry(value=>value+1)} disabled={loading||Boolean(busy)}><RefreshCw/>Recharger les décisions</Button></div>}
  {catalogue.warnings.length>0&&<p className="settings-note" role="status">Certaines métadonnées n’ont pas pu être vérifiées. Aucun montant ni numéro de version n’est déduit du nom des fichiers.</p>}
  {feedback&&<p className="settings-feedback" role="status">{feedback}</p>}
  {catalogue.items.map((item,index)=>{const doc=item.document,state=states.get(doc.id),label=status(item);return <div key={doc.id||`${doc.source_id}:${index}`} className="document-row">
   <span className="pdf-icon"><FileText/></span>
   <div><Button variant="link" onClick={event=>open(item,event.currentTarget)}>{doc.filename}</Button><small>{item.verified?`Version ${item.version} · `:''}{formatDate(received(item))}{item.amount?` · ${formatCatalogAmount(item.amount)}`:''}</small></div>
   <span className={`status-pill ${label==='Validé'?'done':'waiting'}`}>{label}</span>
   <Button variant="ghost" size="icon" aria-label={item.mailSourceId?'Ouvrir le message d’origine':'Lire la source du document'} onClick={()=>sourceMail(item)}>{item.mailSourceId?<Mail/>:<FileText/>}</Button>
   {doc.available&&doc.id&&<Button variant="ghost" size="icon" title="Télécharger" asChild><a href={`/api/v1/documents/${encodeURIComponent(doc.id)}/download`} download><Download/></a></Button>}
   {state?.status==='under_review'&&state.canReview&&typeof api.reviewDocument==='function'&&<Button variant="outline" size="sm" disabled={Boolean(busy)||loading||reviewRevision===null} onClick={()=>void validate(item)}><Check/>{busy===doc.id?'Validation…':'Valider'}</Button>}
  </div>;})}
  {!files.length&&<p className="empty">Aucun document reçu pour ce chantier.</p>}
  <Dialog open={Boolean(selectedDocument)} onOpenChange={value=>{if(!value)setSelected(null);}}>
   <DialogContent className="document-modal" onCloseAutoFocus={event=>{event.preventDefault();if(opener.current?.isConnected)opener.current.focus({preventScroll:true});}}>
    <DialogTitle>{selectedDocument?.document.filename}{selectedDocument?.version?` · v${selectedDocument.version}`:''}</DialogTitle>
    <DialogDescription>{selectedDocument?status(selectedDocument):''} · {selectedDocument?.document.available?(session?.demo?'Original fictif conservé':'Original conservé'):'Original indisponible'}</DialogDescription>
    {selectedDocument&&<>
     {selectedDocument.document.available&&selectedDocument.document.id&&selectedDocument.document.media_type==='application/pdf'&&!previewError?<iframe title={`Aperçu du devis${selectedDocument.version?` version ${selectedDocument.version}`:''}`} src={`/api/v1/documents/${encodeURIComponent(selectedDocument.document.id)}/preview`} onError={()=>setPreviewError(true)}/>:<p className="source-callout">{previewError?'L’aperçu n’a pas pu être chargé. Téléchargez le PDF pour le consulter.':'L’aperçu intégré est disponible pour les originaux PDF conservés.'}</p>}
     <div className="flex gap-2">
      {selectedDocument.document.available&&selectedDocument.document.id&&<>
       {selectedDocument.document.media_type==='application/pdf'&&<Button asChild><a href={`/api/v1/documents/${encodeURIComponent(selectedDocument.document.id)}/preview`} target="_blank" rel="noreferrer"><ExternalLink/>Ouvrir le PDF</a></Button>}
       <Button variant="outline" asChild><a href={`/api/v1/documents/${encodeURIComponent(selectedDocument.document.id)}/download`} download><Download/>Télécharger</a></Button>
      </>}
      <Button variant="ghost" onClick={()=>{setSelected(null);sourceMail(selectedDocument);}}>{selectedDocument.mailSourceId?<Mail/>:<FileText/>}{selectedDocument.mailSourceId?'Message source':'Source du document'}</Button>
      {selectedDocument.document.text_available&&<Button variant="ghost" onClick={()=>{setSelected(null);onSource(selectedDocument.document.preview_source_id||selectedDocument.document.source_id);}}>Lire l’extrait</Button>}
     </div>
     {bootstrap?.access?.signature_workflow===true&&selectedDocument.document.available&&selectedDocument.document.media_type==='application/pdf'&&selectedDocument.document.id&&
      <DocumentSignatureCircuit key={selectedDocument.document.id} projectId={project.id} documentId={selectedDocument.document.id} sha256={selectedDocument.document.sha256}/>}
    </>}
   </DialogContent>
  </Dialog>
 </section>;
}
