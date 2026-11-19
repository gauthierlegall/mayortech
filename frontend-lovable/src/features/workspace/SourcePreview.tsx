import {useEffect,useRef,useState} from 'react';
import {Download,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogDescription,DialogTitle} from '@/components/ui/dialog';

export function SourcePreview({api,sourceId,onClose,returnFocus=null}:{api:any;sourceId:string|null;onClose:()=>void;returnFocus?:HTMLElement|null}){
 const lastFocus=useRef<HTMLElement|null>(null);
 if(sourceId&&returnFocus)lastFocus.current=returnFocus;
 const [source,setSource]=useState<any>(null),[documents,setDocuments]=useState<any[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(false),[retry,setRetry]=useState(0),[documentError,setDocumentError]=useState(''),[documentLoading,setDocumentLoading]=useState(false);
 useEffect(()=>{
  let active=true;setSource(null);setDocuments([]);setError('');setDocumentError('');setDocumentLoading(false);
  if(!sourceId)return()=>{active=false;};
  setLoading(true);setDocumentLoading(true);
  void api.source(sourceId).then(async(payload:any)=>{
   if(!active)return;const item=payload.source??payload;setSource(item);setLoading(false);
   const projectIds:string[]=Array.isArray(item.project_ids)?item.project_ids:item.project_id?[item.project_id]:[];
   const results=await Promise.allSettled(projectIds.map(id=>api.documents(id)));
   if(!active)return;
   const originals=results.flatMap(result=>result.status==='fulfilled'?(Array.isArray(result.value)?result.value:result.value.items??[]):[]).filter((document:any)=>document.source_id===sourceId);
   setDocuments([...new Map(originals.map((item:any)=>[item.id??item.source_id,item])).values()]);setDocumentLoading(false);
   if(results.some(result=>result.status==='rejected'))setDocumentError('La liste des originaux n’a pas pu être entièrement chargée. Réessayez.');
  }).catch((cause:unknown)=>{if(active){setError(cause instanceof Error?cause.message:'Cette source ne peut pas être chargée.');setLoading(false);setDocumentLoading(false);}});
  return()=>{active=false;};
 },[api,sourceId,retry]);
 return <Dialog open={Boolean(sourceId)} onOpenChange={open=>{if(!open)onClose();}}>
  <DialogContent className="document-modal source-preview" onCloseAutoFocus={event=>{event.preventDefault();if(lastFocus.current?.isConnected)lastFocus.current.focus({preventScroll:true});}}>
   <DialogTitle>{String(source?.metadata?.filename??source?.subject??'Source du chantier')}</DialogTitle>
   <DialogDescription>Texte conservé avec sa source. Les images et liens distants ne sont pas chargés.</DialogDescription>
   {loading&&<p role="status">Chargement de la source…</p>}
   {error&&<div role="alert"><p>{error}</p><Button variant="outline" onClick={()=>setRetry(value=>value+1)}><RefreshCw/>Réessayer</Button></div>}
   {source&&<>
    <div className="source-envelope">
     {typeof source.sender==='string'&&<p>De : {source.sender}</p>}
     {source.received_at&&<p>Reçu le {new Date(source.received_at).toLocaleString('fr-FR')}</p>}
    </div>
    <pre className="source-plain-text">{typeof source.body==='string'&&source.body?source.body:'Aucun texte n’a été extrait de cette pièce.'}</pre>
    {documentLoading&&<p role="status">Recherche du fichier original…</p>}
    <div className="source-originals">{documents.map(document=>document.available&&document.id?
     <Button key={document.id} variant="outline" asChild><a href={`/api/v1/documents/${encodeURIComponent(document.id)}/download`} download><Download/>Télécharger {document.filename??'l’original'}</a></Button>:
     <p key={document.id??document.source_id}>L’original de cette source n’est pas conservé.</p>)}</div>
    {!documentLoading&&!documents.length&&!documentError&&<p className="settings-note">Le téléchargement de l’original n’est pas disponible depuis cette source.</p>}
    {documentError&&<p role="status">{documentError} <Button variant="link" onClick={()=>setRetry(value=>value+1)}>Réessayer</Button></p>}
   </>}
   <Button variant="outline" onClick={onClose}>Fermer l’aperçu</Button>
  </DialogContent>
 </Dialog>;
}
