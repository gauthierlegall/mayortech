import React from 'react';
import {
  Sparkle,
  Lock,
  Building,
  Anchor,
  HardHat,
  GraduationCap,
  Coins,
  Landmark,
  Mail,
  Sparkles,
  Send,
  ShieldCheck,
  Smartphone,
  Users,
  GitBranch,
  FileCheck2,
  Layers,
  Info,
  CheckCircle2
} from 'lucide-react';
import { useOrganizationModules } from './organization-modules-context';

const ICON_MAP: Record<string, React.ElementType> = {
  Users,
  GitBranch,
  FileCheck2,
  Building,
  Anchor,
  HardHat,
  GraduationCap,
  Coins,
  Landmark,
  Mail,
  Sparkles,
  Send,
  ShieldCheck,
  Smartphone,
};

export function OrganizationModulesSettings() {
  const { catalog, presets, modules, hasModule, toggleModule, applyPreset } = useOrganizationModules();

  const activePresetId = React.useMemo(() => {
    const sorted = [...modules].sort();
    for (const [id, pr] of Object.entries(presets)) {
      const sortedPr = [...pr.modules].sort();
      if (sorted.length === sortedPr.length && sorted.every((k, i) => k === sortedPr[i])) {
        return id;
      }
    }
    return '';
  }, [modules, presets]);

  return (
    <div className="space-y-6 text-slate-800">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Modules & Périmètre d’Activation</h2>
            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              À chaud · Zéro perte de données
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Activez ou masquez les fonctionnalités selon les besoins et la charte de votre collectivité.
            Toutes les données associées à un module désactivé restent archivées en toute sécurité.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold text-slate-800">{modules.length} modules actifs</span>
          </div>
        </div>
      </div>

      {/* 4 Presets Bar */}
      <div className="p-3 bg-white border border-slate-200 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-center gap-2">
          <Sparkle className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Profils types recommandés :
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap text-xs">
          {Object.values(presets).map((pr) => {
            const isSelected = activePresetId === pr.id;
            return (
              <button
                key={pr.id}
                type="button"
                onClick={() => applyPreset(pr.id)}
                className={`px-3 py-1.5 rounded-xl border font-semibold text-xs transition-all cursor-pointer shadow-2xs ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm font-bold'
                    : 'border-slate-200 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700'
                }`}
              >
                {pr.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 1. Socle Obligatoire */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            1. Socle Régalien Obligatoire
          </h3>
          <span className="text-[10px] text-slate-500 font-medium">Toujours actif</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {catalog
            .filter((m) => m.category === 'socle')
            .map((mod) => {
              const Icon = ICON_MAP[mod.icon] || Layers;
              return (
                <div
                  key={mod.key}
                  className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2.5"
                >
                  <div className="flex items-start justify-between">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                      <Lock className="w-2.5 h-2.5" />
                      <span>Inclus</span>
                    </span>
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">{mod.name}</h4>
                    <p className="text-[11px] text-slate-500 leading-snug mt-0.5">
                      {mod.description}
                    </p>
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* 2. Modules Métiers */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            2. Modules Métiers à la Carte
          </h3>
          <span className="text-[10px] text-slate-500">
            Cliquez pour activer ou masquer instantanément
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {catalog
            .filter((m) => m.category === 'metier')
            .map((mod) => {
              const isChecked = hasModule(mod.key);
              const Icon = ICON_MAP[mod.icon] || Layers;
              return (
                <div
                  key={mod.key}
                  onClick={() => toggleModule(mod.key)}
                  className={`rounded-xl p-4 border transition-all cursor-pointer relative shadow-2xs space-y-2.5 ${
                    isChecked
                      ? 'bg-white border-blue-500 ring-2 ring-blue-500/10'
                      : 'bg-slate-50/70 border-slate-200 opacity-60 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                        isChecked
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'bg-slate-100 text-slate-500 border-slate-200'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    {/* Live Switch */}
                    <div
                      className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                        isChecked ? 'bg-blue-600' : 'bg-slate-300'
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded-full bg-white shadow-xs transform transition-transform duration-200 ease-in-out ${
                          isChecked ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-slate-900">{mod.name}</h4>
                    <p className="text-[11px] text-slate-500 leading-snug mt-0.5 line-clamp-2">
                      {mod.description}
                    </p>
                  </div>

                  <div className="pt-1 flex items-center gap-1 flex-wrap">
                    {mod.circuits.map((c, i) => (
                      <span
                        key={i}
                        className="text-[9.5px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate max-w-full"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* 3. Options & Connecteurs */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            3. Options & Connecteurs Souverains
          </h3>
          <span className="text-[10px] text-slate-500">
            Désactivables pour charte sobre / zéro IA
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {catalog
            .filter((m) => m.category === 'options')
            .map((mod) => {
              const isChecked = hasModule(mod.key);
              const Icon = ICON_MAP[mod.icon] || Layers;
              return (
                <div
                  key={mod.key}
                  onClick={() => toggleModule(mod.key)}
                  className={`rounded-xl p-3.5 border transition-all cursor-pointer relative shadow-2xs space-y-2 ${
                    isChecked
                      ? 'bg-white border-blue-500 ring-2 ring-blue-500/10'
                      : 'bg-slate-50/70 border-slate-200 opacity-60 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center border ${
                        isChecked
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'bg-slate-100 text-slate-500 border-slate-200'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>

                    <div
                      className={`w-8 h-4 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                        isChecked ? 'bg-blue-600' : 'bg-slate-300'
                      }`}
                    >
                      <div
                        className={`w-3 h-3 rounded-full bg-white shadow-xs transform transition-transform duration-200 ease-in-out ${
                          isChecked ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[11.5px] font-bold text-slate-900">{mod.name}</h4>
                    <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                      {mod.description}
                    </p>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
