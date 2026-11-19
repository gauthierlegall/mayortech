/** Layout follows the visible viewport, including an on-screen keyboard. */
export function widgetViewport({layoutHeight,visibleHeight=layoutHeight,offsetTop=0,mobile=false}){
 const visibleBottom=Math.min(layoutHeight,offsetTop+visibleHeight);
 const inset=Math.max(0,layoutHeight-visibleBottom);
 const keyboard=mobile&&inset>160;
 const launcherBottom=mobile?80:24;
 const bottom=keyboard?inset+8:launcherBottom+68;
 const height=Math.max(120,Math.min(640,layoutHeight-bottom-Math.max(16,offsetTop+16)));
 return {bottom,height,keyboard,launcherBottom};
}

/** A remembered id can never select a thread absent from the authorized list. */
export function initialThread(threads,projectId,rememberedId){
 if(projectId)return threads.find(thread=>thread.project_id===projectId)||null;
 return threads.find(thread=>thread.id===rememberedId)||threads[0]||null;
}

export function assistantSessionIdentity(session){
 return JSON.stringify([session?.authenticated===true,session?.actor?.tenant_id||'',session?.actor?.actor_id||'']);
}
