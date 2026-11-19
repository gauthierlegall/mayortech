export const MAX_UPLOAD_BYTES=5_000_000;
export function documentUploadAccess(session,bootstrap){return session?.public_demo!==true&&bootstrap?.permissions?.workspace?.write===true;}
export function validateUploadFile(file){
 if(!file||typeof file.name!=='string'||file.name.length>180||/[\\/:\p{Cc}\p{Cf}]/u.test(file.name)||!/^.+\.(pdf|docx|txt|md|csv)$/i.test(file.name))return 'Choisissez un fichier PDF, DOCX, TXT, MD ou CSV avec un nom simple.';
 if(!Number.isSafeInteger(file.size)||file.size<1||file.size>MAX_UPLOAD_BYTES)return 'Le fichier doit contenir entre 1 octet et 5 Mo.';
 return '';
}
export async function prepareDocumentUpload(file,clientId){
 const error=validateUploadFile(file);if(error)throw Error(error);
 if(typeof clientId!=='string'||!/^[-A-Za-z0-9_.:]{1,100}$/.test(clientId))throw Error('Cet import ne dispose pas d’un identifiant valide. Sélectionnez à nouveau le fichier.');
 const bytes=new Uint8Array(await file.arrayBuffer());
 if(bytes.byteLength!==file.size)throw Error('Le fichier a changé pendant sa lecture. Sélectionnez-le à nouveau.');
 // Bound each conversion to avoid spreading a 5 MB document onto the stack.
 let binary='';for(let start=0;start<bytes.length;start+=32768)binary+=String.fromCharCode(...bytes.subarray(start,start+32768));
 return {filename:file.name,content_base64:btoa(binary),client_id:clientId};
}
export function uploadReceipt(raw,projectId){
 if(raw?.project_id!==projectId||raw?.status!=='needs_review'||!raw.document_id||raw.document?.id!==raw.document_id||!raw.source_id||!raw.job_id||!Number.isSafeInteger(raw.candidate_count)||raw.candidate_count<0)throw Error('Le reçu ne correspond pas au document envoyé. Rechargez le dossier avant de réessayer.');
 let message='Original ajouté au dossier.';
 if(raw.job_status==='failed')message+=' L’analyse n’a pas abouti ; consultez l’original et vérifiez les informations manuellement.';
 else if(['queued','running'].includes(raw.job_status))message+=' L’analyse est en attente ou en cours ; les informations restent à vérifier.';
 else if(raw.job_status!=='done')message+=' L’état de l’analyse est indisponible ; consultez l’original avant de conclure.';
 else if(!['extracted','partial'].includes(raw.extraction_status))message+=' Aucun texte exploitable : consultez l’original.';
 else if(raw.candidate_count>0)message+=` ${raw.candidate_count} proposition${raw.candidate_count>1?'s':''} à relire dans l’onglet « Page ».`;
 else message+=' Aucune nouvelle information proposée par l’analyse.';
 return {...raw,message,warnings:Array.isArray(raw.warnings)?raw.warnings.filter(value=>typeof value==='string'):[]};
}
