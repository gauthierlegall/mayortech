/** A layout preference only: no messages, drafts or account data are stored here. */
const GUTTER=10;
let sequence=0;
export function mailPaneBounds(available){
  if(!Number.isFinite(available)||available<560)return null;
  return {min:240,max:Math.floor(Math.min(720,available-320))};
}
export function fitMailWidth(value,bounds){return Math.max(bounds.min,Math.min(bounds.max,Number.isFinite(value)?Math.round(value):bounds.min));}
export function readMailWidth(value){return typeof value==='string'&&/^\d{3}$/.test(value)&&Number(value)>=240&&Number(value)<=720?Number(value):null;}

export function mountMailSplitter(layout,{list,reader,preferenceKey,breakpoint=950}){
  const media=window.matchMedia(`(min-width:${breakpoint+1}px)`),lifetime=new AbortController();
  let preferred=null,bounds=null,drag=null,disposed=false,current=0;
  try{preferred=readMailWidth(localStorage.getItem(preferenceKey));}catch{/* Optional browser preference. */}
  const separator=document.createElement('div');separator.className='mail-splitter';separator.hidden=true;
  separator.setAttribute('role','separator');separator.setAttribute('aria-orientation','vertical');
  separator.setAttribute('aria-label','Redimensionner la liste des messages');separator.tabIndex=-1;
  separator.title='Glissez pour redimensionner. Flèches gauche et droite au clavier. Double-cliquez pour rétablir la largeur.';
  const originalIds=[list.id,reader.id],uid=++sequence;
  if(!list.id)list.id=`mail-split-list-${uid}`;if(!reader.id)reader.id=`mail-split-reader-${uid}`;
  separator.setAttribute('aria-controls',`${list.id} ${reader.id}`);
  reader.before(separator);layout.dataset.mailSplit='';
  const originalWidth=layout.style.getPropertyValue('--mail-list-width');
  function initialWidth(){const value=parseFloat(getComputedStyle(layout).getPropertyValue('--mail-list-default'));return Number.isFinite(value)?value:310;}
  function apply(value){
    if(!bounds)return;
    current=fitMailWidth(value,bounds);
    const width=`${current}px`;if(layout.style.getPropertyValue('--mail-list-width')!==width)layout.style.setProperty('--mail-list-width',width);
    separator.setAttribute('aria-valuemin',String(bounds.min));separator.setAttribute('aria-valuemax',String(bounds.max));separator.setAttribute('aria-valuenow',String(current));
    separator.setAttribute('aria-valuetext',`Liste des messages : ${current} pixels`);
  }
  function persist(){try{if(preferred===null)localStorage.removeItem(preferenceKey);else localStorage.setItem(preferenceKey,String(preferred));}catch{/* Resizing still works when storage is unavailable. */}}
  function finish(save){
    if(!drag)return;const previous=drag;drag=null;
    delete layout.dataset.mailResizing;document.documentElement.classList.remove('mail-layout-resizing');
    if(separator.hasPointerCapture?.(previous.id))separator.releasePointerCapture(previous.id);
    if(save){preferred=current;persist();}else{preferred=previous.preferred;apply(preferred??initialWidth());}
  }
  function measure(){
    if(disposed)return;
    const start=list.getBoundingClientRect(),end=reader.getBoundingClientRect();
    bounds=media.matches&&start.width>0&&end.width>0?mailPaneBounds(end.right-start.left-GUTTER):null;
    const enabled=Boolean(bounds);
    separator.hidden=!enabled;separator.tabIndex=enabled?0:-1;
    if(enabled){layout.dataset.mailSplitActive='true';apply(drag?current:preferred??initialWidth());}
    else{finish(false);delete layout.dataset.mailSplitActive;}
  }
  const options={signal:lifetime.signal};
  separator.addEventListener('pointerdown',event=>{
    if(!bounds||event.button!==0||drag)return;
    event.preventDefault();separator.focus({preventScroll:true});
    drag={id:event.pointerId,x:event.clientX,width:current,preferred};
    separator.setPointerCapture(event.pointerId);layout.dataset.mailResizing='true';document.documentElement.classList.add('mail-layout-resizing');
  },options);
  separator.addEventListener('pointermove',event=>{if(drag&&event.pointerId===drag.id)apply(drag.width+event.clientX-drag.x);},options);
  separator.addEventListener('pointerup',event=>{if(drag&&event.pointerId===drag.id)finish(true);},options);
  separator.addEventListener('pointercancel',()=>finish(false),options);
  separator.addEventListener('lostpointercapture',()=>finish(false),options);
  separator.addEventListener('keydown',event=>{
    if(drag&&event.key==='Escape'){event.preventDefault();event.stopPropagation();finish(false);return;}
    if(drag)return;
    if(!bounds||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();const step=event.shiftKey?50:10;
    apply(event.key==='Home'?bounds.min:event.key==='End'?bounds.max:current+(event.key==='ArrowLeft'?-step:step));preferred=current;persist();
  },options);
  separator.addEventListener('dblclick',()=>{if(bounds){preferred=null;persist();apply(initialWidth());}},options);
  window.addEventListener('resize',measure,options);media.addEventListener('change',measure,options);
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(measure):null;
  for(const element of [layout,list,reader])observer?.observe(element);
  measure();
  return {destroy(){if(disposed)return;finish(false);disposed=true;observer?.disconnect();lifetime.abort();separator.remove();delete layout.dataset.mailSplit;delete layout.dataset.mailSplitActive;if(originalWidth)layout.style.setProperty('--mail-list-width',originalWidth);else layout.style.removeProperty('--mail-list-width');if(!originalIds[0])list.removeAttribute('id');if(!originalIds[1])reader.removeAttribute('id');}};
}
