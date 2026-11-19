/** Explicit test double: React lifecycle is real; no BlockSuite or backend I/O. */
export async function mountNativePage(host:HTMLElement,options:any){
 const box=document.createElement('textarea');box.setAttribute('aria-label','Note fictive du contrôleur natif simulé');box.placeholder='Saisir une note fictive';host.replaceChildren(box);
 const all=((window as any).__nativeControllers??=[]);let release:(()=>void)|null=null;
 const controller:any={id:all.length+1,dirty:false,destroyed:false,flushes:0,updates:0,writes:0,blocked:0,
  get text(){return box.value;},getMetadata(){return {databases:[]};},
  async flush(){if(!controller.dirty)return;options.beforeSave?.();controller.flushes++;controller.dirty=false;options.onDirty?.(false);options.onSaved?.();},
  updateActions(actions:any[]){controller.updates++;controller.actions=actions;},
  beginDeferredSave(){return new Promise<void>(resolve=>{release=resolve;}).then(()=>{try{options.beforeSave?.();controller.writes++;}catch(error){controller.blocked++;throw error;}});},
  release(){release?.();},destroy(){controller.destroyed=true;box.remove();}
 };
 box.addEventListener('input',()=>{controller.dirty=true;options.onDirty?.(true);});
 all.push(controller);return controller;
}
