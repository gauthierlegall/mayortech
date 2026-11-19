"""Operator-only fictional planning, preserving existing dates and human edits.

Run after the existing Lovable storyline/native seeding, never at app startup.
Both the base URL and its actual manifest must be supplied explicitly.
"""
from pathlib import Path
import argparse
import json
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if (parsed.hostname not in {"127.0.0.1", "localhost", "travaux.kerforge.com"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}))):
        parser.error("Expected the explicit local or public fictional demonstration URL.")
    fixture = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if fixture.get("storyline_id") != "lovable-travaux-v1":
        parser.error("Expected the exact operator Lovable storyline manifest.")
    starts = {
        "Valider le devis initial": "2026-11-04",
        "Préparer la sécurisation de l’entrée": "2026-11-16",
        "Confirmer l’accès vendredi": "2026-11-20",
        "Confirmer le plan de circulation": "2026-11-16",
        "Recevoir les résultats des essais": "2026-11-18",
        "Organiser la visite technique": "2026-11-20",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page.goto(args.base_url.rstrip("/") + "/#/parametres", wait_until="networkidle")
        result = page.evaluate("""async({fixture,starts})=>{
          const request=async(path,body)=>{const response=await fetch('/api/v1/'+path,{...(body?{method:'POST',body:JSON.stringify(body)}:{}),headers:{'X-Requested-With':'Travaux','Content-Type':'application/json'}});if(!response.ok)throw new Error('Operator request refused');return response.json();};
          const settings=await request('settings');if(!['demo','public_demo'].includes(settings.mode))throw new Error('Fictional demo mode required');
          const native=await import('/native/editor.js');const proofs=[];
          for(const [id,seed] of Object.entries(fixture.native_seed)){
            const project=await request('projects/'+id);if(!project.sources.some(source=>source.metadata?.fictitious===true&&source.metadata?.storyline_id===fixture.storyline_id))throw new Error('Storyline source required');
            const beforeFacts=JSON.stringify(project.facts.map(({id,field,value,status})=>({id,field,value,status})));
            const page=await request('projects/'+id+'/page',{});const host=document.createElement('div');host.style.cssText='position:fixed;left:-20000px;width:1000px;height:700px;visibility:hidden';host.inert=true;document.body.append(host);
            const editor=await native.mount(host,{pageId:page.id,title:project.name});const changed=[],preserved=[];
            try{
              const marker=editor.store.workspace.doc.getMap('travaux:workspace');const key='operatorCoordinationPlanning';
              if(marker.get(key)!=='v0.6'){
                const metadata=editor.getMetadata();
                for(const action of seed.actions){
                  const database=metadata.databases.find(item=>item.rows.some(row=>row.sourceKey===action.candidate_id));const row=database?.rows.find(row=>row.sourceKey===action.candidate_id);const start=starts[action.title];if(!row||!start)continue;
                  const field=name=>row.fields.find(item=>item.name===name)?.text||'';
                  if(field('Début')||field('Intitulé')!==action.title||field('Échéance')!==action.due||field('Responsable')!==action.owner||field('Statut')!==action.status||field('Priorité')!==action.priority){preserved.push(row.id);continue;}
                  editor.updateAction(row.id,{startDate:start},database.id);changed.push({row_id:row.id,title:action.title,start,due:action.due});
                }
                if(changed.length)editor.addBlock('text','Planification de démonstration renseignée par l’opérateur : les débuts des actions de cet exemple sont des choix de planning fictifs. Ils ne confirment aucune nouvelle annonce de l’entreprise.');
                marker.set(key,'v0.6');while(editor.dirty)await editor.save();
              }
              const after=await request('projects/'+id);if(JSON.stringify(after.facts.map(({id,field,value,status})=>({id,field,value,status})))!==beforeFacts)throw new Error('Planning must not change confirmed facts');
              proofs.push({project_id:id,changed,preserved,metadata:editor.getMetadata(),confirmed_facts_unchanged:true});
            }finally{editor.unmount();host.remove();}
          }return proofs;
        }""", {"fixture": fixture, "starts": starts})
        browser.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"fictitious": True, "operator_action": True, "projects": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"projects": len(result), "planned": sum(len(item["changed"]) for item in result), "preserved": sum(len(item["preserved"]) for item in result)}))


if __name__ == "__main__":
    main()
