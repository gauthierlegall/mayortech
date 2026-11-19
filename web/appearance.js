export const palettes=Object.freeze([
  {id:'forest',name:'Vert',accent:'#0F766E',hover:'#0D635D',soft:'#F0FDFA'},
  {id:'blue',name:'Encre Marine',accent:'#102A4C',hover:'#193D6B',soft:'#F0F4F8'},
  {id:'violet',name:'Violet',accent:'#655095',hover:'#503f79',soft:'#f1eef7'},
  {id:'slate',name:'Gris',accent:'#4b5966',hover:'#3c4854',soft:'#eef1f4'},
  {id:'teal',name:'Bleu-vert',accent:'#246871',hover:'#1c525a',soft:'#eaf3f4'},
  {id:'earth',name:'Brun',accent:'#785940',hover:'#5e4532',soft:'#f4f0eb'},
]);
const key='travaux:appearance';
export function normalizeAppearance(value){
  return {color:palettes.some(p=>p.id===value?.color)?value.color:'blue',density:value?.density==='comfortable'?'comfortable':'compact'};
}
export function getAppearance(){
  try{return normalizeAppearance(JSON.parse(globalThis.localStorage?.getItem(key)||'{}'));}catch{return normalizeAppearance({});}
}
export function applyAppearance(value=getAppearance()){
  const preferences=normalizeAppearance(value),palette=palettes.find(p=>p.id===preferences.color);
  if(typeof document!=='undefined'){
    const root=document.documentElement;
    root.dataset.palette=palette.id;root.dataset.density=preferences.density;
    for(const [token,color] of Object.entries({'--accent':palette.accent,'--accent-hover':palette.hover,'--accent-soft':palette.soft,'--green':palette.accent,'--green-deep':palette.hover,'--green-light':palette.soft}))root.style.setProperty(token,color);
  }
  return preferences;
}
export function setAppearance(change){
  const value=applyAppearance({...getAppearance(),...change});
  try{globalThis.localStorage?.setItem(key,JSON.stringify(value));}catch{}
  globalThis.window?.dispatchEvent(new Event('travaux:appearance'));
  return value;
}
