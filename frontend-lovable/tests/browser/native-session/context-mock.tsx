import {createContext,useContext} from 'react';
export const FixtureWorkspace=createContext<any>(null);
export function useWorkspace(){return useContext(FixtureWorkspace);}
