import React, { useState } from 'react';
import { X, Plus, Trash2, Save, FormInput, FileText, CheckSquare, Calendar, Euro } from 'lucide-react';
import { toast } from 'sonner';

interface FormField {
  name: string;
  title: string;
  type: 'string' | 'textarea' | 'number' | 'boolean' | 'date' | 'select';
  required: boolean;
  options?: string[];
}

interface MayorFlowFormBuilderModalProps {
  definitionId: string;
  nodeId: string;
  nodeName: string;
  onClose: () => void;
}

export function MayorFlowFormBuilderModal({ definitionId, nodeId, nodeName, onClose }: MayorFlowFormBuilderModalProps) {
  const [fields, setFields] = useState<FormField[]>([
    { name: 'decision', title: 'Décision d\'instruction', type: 'select', required: true, options: ['Favorable', 'Défavorable', 'Compléments requis'] },
    { name: 'observations', title: 'Motivations techniques', type: 'textarea', required: true },
    { name: 'montant_estime', title: 'Montant prévisionnel (€)', type: 'number', required: false },
    { name: 'date_visa', title: 'Date d\'examen', type: 'date', required: false },
  ]);

  const [saving, setSaving] = useState(false);

  const addField = () => {
    const newField: FormField = {
      name: `champ_${fields.length + 1}`,
      title: `Nouveau champ ${fields.length + 1}`,
      type: 'string',
      required: false,
    };
    setFields([...fields, newField]);
  };

  const removeField = (index: number) => {
    setFields(fields.filter((_, i) => i !== index));
  };

  const updateField = (index: number, key: keyof FormField, val: any) => {
    const updated = [...fields];
    updated[index] = { ...updated[index], [key]: val };
    setFields(updated);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const properties: Record<string, any> = {};
      const requiredList: string[] = [];
      const uiSchema: Record<string, any> = {};

      fields.forEach((f) => {
        if (f.type === 'textarea') {
          properties[f.name] = { type: 'string', title: f.title };
          uiSchema[f.name] = { 'ui:widget': 'textarea' };
        } else if (f.type === 'select') {
          properties[f.name] = { type: 'string', title: f.title, enum: f.options || [] };
        } else if (f.type === 'number') {
          properties[f.name] = { type: 'number', title: f.title };
        } else if (f.type === 'boolean') {
          properties[f.name] = { type: 'boolean', title: f.title };
        } else if (f.type === 'date') {
          properties[f.name] = { type: 'string', format: 'date', title: f.title };
        } else {
          properties[f.name] = { type: 'string', title: f.title };
        }

        if (f.required) {
          requiredList.push(f.name);
        }
      });

      const schema = {
        type: 'object',
        title: `Formulaire : ${nodeName}`,
        properties,
        required: requiredList,
      };

      const res = await fetch(`/api/v1/workflows/definitions/${definitionId}/form/${nodeId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
        body: JSON.stringify({ schema, uischema: uiSchema }),
      });
      if (!res.ok) throw new Error('Erreur lors de la sauvegarde du formulaire.');

      toast.success('Champs du formulaire enregistrés avec succès !');
      onClose();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in font-sans">
      <div className="relative w-full max-w-3xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-600">
              <FormInput size={20} />
            </div>
            <div>
              <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest block">
                Champs du formulaire
              </span>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight">Formulaire de l'étape « {nodeName} »</h3>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition" aria-label="Fermer">
            <X size={18} />
          </button>
        </div>

        {/* Fields list */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="font-semibold text-slate-700">Champs configurés pour cette étape</span>
            <button
              onClick={addField}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 transition font-semibold"
            >
              <Plus size={14} />
              <span>Ajouter un champ</span>
            </button>
          </div>

          <div className="space-y-3">
            {fields.map((f, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <div className="flex-1 space-y-1">
                  <label htmlFor={`champ-label-${i}`} className="text-[10px] text-slate-500 uppercase tracking-wider block">Libellé du champ</label>
                  <input
                    id={`champ-label-${i}`}
                    type="text"
                    value={f.title}
                    onChange={(e) => updateField(i, 'title', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="w-36 space-y-1">
                  <label htmlFor={`champ-type-${i}`} className="text-[10px] text-slate-500 uppercase tracking-wider block">Type</label>
                  <select
                    id={`champ-type-${i}`}
                    value={f.type}
                    onChange={(e) => updateField(i, 'type', e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="string">Texte court</option>
                    <option value="textarea">Texte long</option>
                    <option value="number">Montant / Nombre</option>
                    <option value="date">Date</option>
                    <option value="boolean">Case à cocher</option>
                    <option value="select">Menu déroulant</option>
                  </select>
                </div>

                <div className="pt-4 flex items-center gap-2">
                  <label className="flex items-center gap-1 text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={f.required}
                      onChange={(e) => updateField(i, 'required', e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-[11px]">Requis</span>
                  </label>
                  <button
                    onClick={() => removeField(i)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded transition"
                    title="Supprimer"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/70 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 transition text-xs font-medium">
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition active:scale-95 text-xs shadow-sm"
          >
            <Save size={15} />
            <span>{saving ? 'Enregistrement…' : 'Enregistrer le Formulaire'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
