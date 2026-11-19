import {createFileRoute} from '@tanstack/react-router';
import {workspaceOptions} from '@/features/workspace/data';
import {WorkspaceProvider} from '@/features/workspace/context';
import {Shell} from '@/features/workspace/Shell';
import {ProjectDetail} from '@/features/workspace/ProjectDetail';
import {pageMeta} from '@/features/workspace/route-meta';
export const Route=createFileRoute('/chantiers/$id')({loader:async({context,params})=>{const d=await context.queryClient.ensureQueryData(workspaceOptions);return {title:d.state.projects.find(p=>p.id===params.id)?.title};},head:()=>pageMeta('Dossier de chantier','Situation, documents, actions et historique du chantier dans MayorTech.'),component:Detail});
function Detail(){const {id}=Route.useParams();return <WorkspaceProvider><Shell><ProjectDetail id={id}/></Shell></WorkspaceProvider>;}
