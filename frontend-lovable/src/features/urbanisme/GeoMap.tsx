import React, {useState, useEffect, useMemo} from 'react';
import {
  MapPin,
  Anchor,
  FileText,
  HardHat,
  Compass,
  List,
  Layers,
  ArrowRight,
  X,
  ExternalLink,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from '../workspace/context';
import './geomap.css';

export interface GeoFeature {
  id: string;
  type: string;
  geometry: {
    type: string;
    coordinates: [number, number]; // [lon, lat]
  };
  properties: {
    id: string;
    project_id: string;
    feature_type: 'port_ouvrage' | 'parcelle' | 'chantier_travaux' | string;
    name: string;
    condition_rating?: string;
    advice_status?: string;
    parcel_ref?: string;
    port_name?: string;
    created_at?: string;
    [key: string]: any;
  };
}

import {projectLonLat, unprojectXY} from './geo-projection.mjs';
export {projectLonLat, unprojectXY};

const FALLBACK_FEATURES: GeoFeature[] = [
  {
    id: 'geo-tinduff',
    type: 'Feature',
    geometry: {type: 'Point', coordinates: [-4.3820, 48.3370]},
    properties: {
      id: 'geo-tinduff',
      project_id: 'TRV-2026-042',
      feature_type: 'port_ouvrage',
      name: 'Port du Tinduff — Ponton et Cale',
      port_name: 'Port du Tinduff',
      condition_rating: 'moyen',
      ouvrage_type: 'Ponton plaisance'
    }
  },
  {
    id: 'geo-passage',
    type: 'Feature',
    geometry: {type: 'Point', coordinates: [-4.4210, 48.3615]},
    properties: {
      id: 'geo-passage',
      project_id: 'TRV-2026-038',
      feature_type: 'port_ouvrage',
      name: 'Port du Passage — Cale historique',
      port_name: 'Port du Passage',
      condition_rating: 'bon',
      ouvrage_type: 'Cale de mise à l\'eau'
    }
  },
  {
    id: 'geo-auberlach',
    type: 'Feature',
    geometry: {type: 'Point', coordinates: [-4.3975, 48.3512]},
    properties: {
      id: 'geo-auberlach',
      project_id: 'TRV-2026-045',
      feature_type: 'port_ouvrage',
      name: 'Port de l\'Auberlac\'h — Zone de mouillage',
      port_name: 'Port de l\'Auberlac\'h',
      condition_rating: 'degrade',
      ouvrage_type: 'Chaîne d\'amarrage'
    }
  },
  {
    id: 'geo-parcelle-a12',
    type: 'Feature',
    geometry: {type: 'Point', coordinates: [-4.3680, 48.3750]},
    properties: {
      id: 'geo-parcelle-a12',
      project_id: 'TRV-2026-031',
      feature_type: 'parcelle',
      name: 'Parcelle Exemple A-12 — Centre Bourg',
      parcel_ref: 'A-12',
      advice_status: 'favorable',
      regulation_source: 'PLU Zone Ub'
    }
  }
];

export function GeoMap({
  selectedProjectId,
  onSelectFeature
}: {
  selectedProjectId?: string;
  onSelectFeature?: (feature: GeoFeature) => void;
}) {
  const {api} = useWorkspace();
  const [features, setFeatures] = useState<GeoFeature[]>(FALLBACK_FEATURES);
  const [filterType, setFilterType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [selectedFeature, setSelectedFeature] = useState<GeoFeature | null>(null);
  const [hoverCoords, setHoverCoords] = useState<[number, number]>([-4.3750, 48.3650]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    async function loadFeatures() {
      if (!api || typeof api.geoFeatures !== 'function') return;
      try {
        setLoading(true);
        const res = await api.geoFeatures();
        if (alive && res && Array.isArray(res.features) && res.features.length > 0) {
          setFeatures(res.features);
        }
      } catch (err) {
        console.warn('GeoFeatures api fallback used', err);
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadFeatures();
    return () => {
      alive = false;
    };
  }, [api]);

  const filteredFeatures = useMemo(() => {
    if (filterType === 'all') return features;
    return features.filter(f => f.properties.feature_type === filterType);
  }, [features, filterType]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * 900;
    const svgY = ((e.clientY - rect.top) / rect.height) * 580;
    const [lon, lat] = unprojectXY(svgX, svgY);
    setHoverCoords([lon, lat]);
  };

  const handleFeatureClick = (f: GeoFeature) => {
    setSelectedFeature(f);
    if (onSelectFeature) {
      onSelectFeature(f);
    }
  };

  return (
    <div className="geomap-container">
      <div className="geomap-header">
        <div className="geomap-title-group">
          <h3>
            <Compass size={20} className="text-sky-500" />
            Cartographie du Territoire — Plougastel-Daoulas
          </h3>
          <p>Visualisation spatiale des ouvrages portuaires, parcelles d'urbanisme et chantiers.</p>
        </div>

        <div className="geomap-controls">
          <div className="geomap-filters" role="toolbar" aria-label="Filtres cartographiques">
            <button
              className={`geomap-filter-btn ${filterType === 'all' ? 'active' : ''}`}
              onClick={() => setFilterType('all')}
            >
              Tous ({features.length})
            </button>
            <button
              className={`geomap-filter-btn ${filterType === 'port_ouvrage' ? 'active' : ''}`}
              onClick={() => setFilterType('port_ouvrage')}
            >
              Ports ({features.filter(f => f.properties.feature_type === 'port_ouvrage').length})
            </button>
            <button
              className={`geomap-filter-btn ${filterType === 'parcelle' ? 'active' : ''}`}
              onClick={() => setFilterType('parcelle')}
            >
              Urbanisme ({features.filter(f => f.properties.feature_type === 'parcelle').length})
            </button>
            <button
              className={`geomap-filter-btn ${filterType === 'chantier_travaux' ? 'active' : ''}`}
              onClick={() => setFilterType('chantier_travaux')}
            >
              Chantiers ({features.filter(f => f.properties.feature_type === 'chantier_travaux').length})
            </button>
          </div>

          <div className="flex gap-1">
            <Button
              variant={viewMode === 'map' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('map')}
              title="Vue Carte Vectorielle"
            >
              <Layers size={14} className="mr-1" /> Carte
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              title="Vue Liste Accessible"
            >
              <List size={14} className="mr-1" /> Liste
            </Button>
          </div>
        </div>
      </div>

      {viewMode === 'map' ? (
        <div className="geomap-viewport-wrapper">
          {/* HUD Overlay with Live Coordinates */}
          <div className="geomap-hud">
            <span>WGS84:</span>
            <strong>{hoverCoords[0].toFixed(4)}° E, {hoverCoords[1].toFixed(4)}° N</strong>
            <span className="text-slate-400">| Presqu'île de Plougastel</span>
          </div>

          {/* SVG Vector Map of Plougastel Peninsula */}
          <svg
            className="geomap-svg"
            viewBox="0 0 900 580"
            onMouseMove={handleMouseMove}
            aria-label="Carte vectorielle interactive de Plougastel-Daoulas"
          >
            <defs>
              <linearGradient id="seaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#081426" />
                <stop offset="50%" stopColor="#0b1b33" />
                <stop offset="100%" stopColor="#06101e" />
              </linearGradient>

              <linearGradient id="landGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#1e293b" />
                <stop offset="100%" stopColor="#172234" />
              </linearGradient>

              <radialGradient id="coastGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(56, 189, 248, 0.25)" />
                <stop offset="100%" stopColor="rgba(56, 189, 248, 0)" />
              </radialGradient>

              <filter id="pinShadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.6" />
              </filter>
            </defs>

            {/* Sea Background */}
            <rect width="900" height="580" fill="url(#seaGrad)" />

            {/* Subtle Nautical Coordinate Grid */}
            <g stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" strokeDasharray="4 6">
              <line x1="150" y1="0" x2="150" y2="580" />
              <line x1="300" y1="0" x2="300" y2="580" />
              <line x1="450" y1="0" x2="450" y2="580" />
              <line x1="600" y1="0" x2="600" y2="580" />
              <line x1="750" y1="0" x2="750" y2="580" />
              <line x1="0" y1="120" x2="900" y2="120" />
              <line x1="0" y1="240" x2="900" y2="240" />
              <line x1="0" y1="360" x2="900" y2="360" />
              <line x1="0" y1="480" x2="900" y2="480" />
            </g>

            {/* Bathymetric coastal contours */}
            <path
              d="M 280 80 Q 200 280 90 380 Q 150 480 360 520 Q 550 500 850 380 L 850 80 Z"
              fill="none"
              stroke="rgba(56, 189, 248, 0.08)"
              strokeWidth="12"
              pointerEvents="none"
            />

            {/* Plougastel Peninsula Landmass Polygon */}
            {/* Realistically contours the Elorn estuary, Pont de l'Iroise, Le Passage, Armorique, Auberlac'h, Tinduff, Corbeaux */}
            <path
              d="M 315 100
                 C 290 140, 260 220, 220 290
                 C 200 320, 160 350, 110 395
                 C 90 415, 120 445, 170 435
                 C 210 425, 250 405, 280 380
                 C 305 360, 330 345, 345 355
                 C 365 370, 370 400, 395 440
                 C 410 465, 415 480, 385 490
                 C 365 498, 400 520, 450 505
                 C 510 485, 590 460, 680 430
                 C 740 410, 800 380, 850 360
                 L 850 200
                 C 780 180, 680 160, 560 145
                 C 460 130, 370 115, 315 100 Z"
              fill="url(#landGrad)"
              stroke="#38bdf8"
              strokeWidth="2.5"
              strokeOpacity="0.8"
              pointerEvents="none"
            />

            {/* Pont de l'Iroise / RN165 road axis */}
            <path
              d="M 315 20 L 315 100 C 320 180, 370 250, 460 270 C 560 290, 700 310, 850 330"
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="3.5"
              strokeDasharray="8 3"
              strokeOpacity="0.5"
              pointerEvents="none"
            />
            {/* D29 Route vers Tinduff */}
            <path
              d="M 460 270 C 440 320, 420 370, 415 440"
              fill="none"
              stroke="#cbd5e1"
              strokeWidth="2"
              strokeOpacity="0.4"
              pointerEvents="none"
            />

            {/* Waterway & Geographic Labels */}
            <text x="180" y="80" fill="#7dd3fc" fontSize="13" fontWeight="600" letterSpacing="1" opacity="0.75">
              L'ÉLORN
            </text>
            <text x="60" y="300" fill="#7dd3fc" fontSize="13" fontWeight="600" letterSpacing="1" opacity="0.75">
              RADE DE BREST
            </text>
            <text x="210" y="520" fill="#7dd3fc" fontSize="12" fontWeight="500" letterSpacing="0.8" opacity="0.65">
              Anse de l'Auberlac'h
            </text>
            <text x="330" y="65" fill="#94a3b8" fontSize="11" opacity="0.8">
              Pont de l'Iroise (RN165)
            </text>
            <text x="500" y="240" fill="#cbd5e1" fontSize="13" fontWeight="600" opacity="0.7">
              Plougastel-Daoulas
            </text>

            {/* Render Geo Feature Markers */}
            {filteredFeatures.map(f => {
              const [x, y] = projectLonLat(f.geometry.coordinates[0], f.geometry.coordinates[1]);
              const isSelected = selectedFeature?.id === f.id;
              const type = f.properties.feature_type;

              let fillColor = '#0284c7'; // Port (Sky/Blue)
              let strokeColor = '#38bdf8';
              if (type === 'parcelle') {
                fillColor = '#059669'; // Parcelle (Emerald)
                strokeColor = '#34d399';
              } else if (type === 'chantier_travaux') {
                fillColor = '#d97706'; // Travaux (Amber)
                strokeColor = '#fbbf24';
              }

              return (
                <g
                  key={f.id}
                  className="geo-pin-group"
                  transform={`translate(${x}, ${y})`}
                  onClick={() => handleFeatureClick(f)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleFeatureClick(f);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`${f.properties.name} (${f.properties.feature_type})`}
                >
                  {/* Glowing halo pulse when selected */}
                  {isSelected && (
                    <circle r="18" fill="none" stroke={strokeColor} strokeWidth="2.5" className="geo-pin-pulse" />
                  )}

                  {/* Marker Pin Base */}
                  <circle
                    r={isSelected ? '12' : '9'}
                    fill={fillColor}
                    stroke="#ffffff"
                    strokeWidth="2"
                    filter="url(#pinShadow)"
                  />

                  {/* Inner Symbol Dot */}
                  <circle r="3.5" fill="#ffffff" />

                  {/* Label on hover or selection */}
                  <text
                    x="14"
                    y="4"
                    fill="#ffffff"
                    fontSize={isSelected ? '12' : '11'}
                    fontWeight={isSelected ? '700' : '500'}
                    filter="url(#pinShadow)"
                    pointerEvents="none"
                  >
                    {f.properties.name}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Map Legend */}
          <div className="geomap-legend" aria-hidden="true">
            <div className="geomap-legend-item">
              <span className="geomap-legend-dot port" />
              <span>Ports & Mouillages</span>
            </div>
            <div className="geomap-legend-item">
              <span className="geomap-legend-dot parcelle" />
              <span>Parcelles & PLU</span>
            </div>
            <div className="geomap-legend-item">
              <span className="geomap-legend-dot chantier" />
              <span>Chantiers & Ouvrages</span>
            </div>
          </div>

          {/* Selected Feature Detail Drawer Card */}
          {selectedFeature && (
            <div className="geomap-drawer" role="region" aria-label="Détail du point sélectionné">
              <div className="geomap-drawer-header">
                <div>
                  <h4 className="geomap-drawer-title">{selectedFeature.properties.name}</h4>
                  <span
                    className={`geomap-drawer-badge ${
                      selectedFeature.properties.feature_type === 'port_ouvrage'
                        ? 'port'
                        : selectedFeature.properties.feature_type === 'parcelle'
                        ? 'parcelle'
                        : 'chantier'
                    }`}
                  >
                    {selectedFeature.properties.feature_type === 'port_ouvrage' && <Anchor size={11} />}
                    {selectedFeature.properties.feature_type === 'parcelle' && <FileText size={11} />}
                    {selectedFeature.properties.feature_type === 'chantier_travaux' && <HardHat size={11} />}
                    {selectedFeature.properties.feature_type === 'port_ouvrage'
                      ? 'Ouvrage portuaire'
                      : selectedFeature.properties.feature_type === 'parcelle'
                      ? 'Parcelle Urbanisme'
                      : 'Chantier Travaux'}
                  </span>
                </div>
                <button
                  className="geomap-drawer-close"
                  onClick={() => setSelectedFeature(null)}
                  aria-label="Fermer la fiche"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="geomap-drawer-coords">
                Coordonnées : {selectedFeature.geometry.coordinates[0].toFixed(4)}° E,{' '}
                {selectedFeature.geometry.coordinates[1].toFixed(4)}° N
              </div>

              {selectedFeature.properties.port_name && (
                <div className="text-xs text-slate-300">
                  <strong>Port de rattachement :</strong> {selectedFeature.properties.port_name}
                </div>
              )}

              {selectedFeature.properties.condition_rating && (
                <div className="text-xs text-slate-300">
                  <strong>État constaté :</strong>{' '}
                  <span
                    className={`font-semibold ${
                      selectedFeature.properties.condition_rating === 'bon'
                        ? 'text-emerald-400'
                        : selectedFeature.properties.condition_rating === 'moyen'
                        ? 'text-yellow-400'
                        : selectedFeature.properties.condition_rating === 'degrade'
                        ? 'text-orange-400'
                        : 'text-red-400'
                    }`}
                  >
                    {selectedFeature.properties.condition_rating.toUpperCase()}
                  </span>
                </div>
              )}

              {selectedFeature.properties.parcel_ref && (
                <div className="text-xs text-slate-300">
                  <strong>Référence cadastrale :</strong> {selectedFeature.properties.parcel_ref}
                  {selectedFeature.properties.regulation_source && (
                    <span> ({selectedFeature.properties.regulation_source})</span>
                  )}
                </div>
              )}

              <div className="geomap-drawer-actions">
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    if (selectedFeature.properties.project_id) {
                      window.location.hash = `#/chantiers/${encodeURIComponent(
                        selectedFeature.properties.project_id
                      )}?view=urbanisme`;
                    }
                  }}
                >
                  Ouvrir le dossier lié <ArrowRight size={13} className="ml-1" />
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Accessible List View Fallback */
        <div className="geomap-list-view" role="list" aria-label="Liste des points du territoire">
          {filteredFeatures.map(f => (
            <div key={f.id} className="geomap-list-item" role="listitem">
              <div className="geomap-list-info">
                <span
                  className={`geomap-list-dot ${
                    f.properties.feature_type === 'port_ouvrage'
                      ? 'bg-sky-500'
                      : f.properties.feature_type === 'parcelle'
                      ? 'bg-emerald-500'
                      : 'bg-amber-500'
                  }`}
                />
                <div>
                  <div className="geomap-list-title">{f.properties.name}</div>
                  <div className="geomap-list-meta">
                    {f.geometry.coordinates[0].toFixed(4)}° E, {f.geometry.coordinates[1].toFixed(4)}° N ·{' '}
                    {f.properties.port_name || f.properties.parcel_ref || 'Territoire de Plougastel'}
                  </div>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  window.location.hash = `#/chantiers/${encodeURIComponent(
                    f.properties.project_id
                  )}?view=urbanisme`;
                }}
              >
                Dossier <ExternalLink size={12} className="ml-1" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
