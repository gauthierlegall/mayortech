import {createFileRoute} from '@tanstack/react-router';
import {workspaceOptions} from '@/features/workspace/data';
import {WorkspaceProvider} from '@/features/workspace/context';
import {Shell} from '@/features/workspace/Shell';
import {Actions} from '@/features/workspace/Actions';
import {pageMeta} from '@/features/workspace/route-meta';
export const Route=createFileRoute('/actions')({head:()=>pageMeta('Actions','Suivre les actions municipales en tableau et Kanban dans MayorTech.'),loader:({context})=>context.queryClient.ensureQueryData(workspaceOptions),component:ActionsPage});
function ActionsPage(){return <WorkspaceProvider><Shell><Actions/></Shell></WorkspaceProvider>;}
