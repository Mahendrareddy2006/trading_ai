import React, { useState } from 'react';
import { ModelRecord } from '../types';
import { 
  BrainCircuit, 
  BarChart3, 
  ShieldCheck, 
  CheckCircle2, 
  Calendar,
  Layers
} from 'lucide-react';

interface ModelLabViewProps {
  models: ModelRecord[];
  onSelectModel?: (modelId: string) => void;
}

export const ModelLabView: React.FC<ModelLabViewProps> = ({ models }) => {
  const [selectedModelId, setSelectedModelId] = useState<string>(
    models.length > 0 ? models[0].model_id : ''
  );

  const selectedModel = models.find((m) => m.model_id === selectedModelId) || models[0];

  const classLabels = ['BUY (+1)', 'NEUTRAL (0)', 'SELL (-1)'];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-cyan-400" />
            <span>AI MODEL LABORATORY</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Registry of leak-free trained models with Platt-calibrated out-of-sample metrics & feature importances.
          </p>
        </div>

        {/* Model Selector Pill */}
        {models.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">Inspecting:</span>
            <select
              value={selectedModel?.model_id}
              onChange={(e) => setSelectedModelId(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
            >
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.symbol} {m.timeframe} ({m.model_type}) - {m.model_id.slice(-15)}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {models.length === 0 ? (
        <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-xl p-12 text-center text-slate-500">
          <BrainCircuit className="w-12 h-12 stroke-1 mx-auto text-slate-600 mb-3" />
          <h3 className="font-bold text-slate-300 text-sm">No Models in Registry Yet</h3>
          <p className="text-xs mt-1 max-w-md mx-auto text-slate-400">
            Head to the Training tab to train a leak-free model using historical Binance data with chronological walk-forward splits.
          </p>
        </div>
      ) : selectedModel ? (
        <div className="space-y-6">
          {/* Key Out-of-Sample Performance Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
              <span className="text-xs font-mono text-slate-400 uppercase">Test Accuracy</span>
              <p className="text-2xl font-black text-emerald-400 font-mono mt-1">
                {(selectedModel.metrics.accuracy * 100).toFixed(2)}%
              </p>
              <p className="text-[11px] text-slate-500 mt-1 font-mono">
                Pure out-of-sample holdout
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
              <span className="text-xs font-mono text-slate-400 uppercase">Balanced Accuracy</span>
              <p className="text-2xl font-black text-cyan-400 font-mono mt-1">
                {(selectedModel.metrics.balanced_accuracy * 100).toFixed(2)}%
              </p>
              <p className="text-[11px] text-slate-500 mt-1 font-mono">
                Class-weighted across regimes
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
              <span className="text-xs font-mono text-slate-400 uppercase">Macro F1 Score</span>
              <p className="text-2xl font-black text-indigo-400 font-mono mt-1">
                {(selectedModel.metrics.macro_f1 * 100).toFixed(2)}%
              </p>
              <p className="text-[11px] text-slate-500 mt-1 font-mono">
                Harmonic mean precision/recall
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
              <span className="text-xs font-mono text-slate-400 uppercase">Dataset Samples</span>
              <p className="text-2xl font-black text-slate-100 font-mono mt-1">
                {(selectedModel.sample_counts?.train || 0) + (selectedModel.sample_counts?.val || 0) + (selectedModel.sample_counts?.test || 0)}
              </p>
              <p className="text-[11px] text-slate-500 mt-1 font-mono">
                Train: {selectedModel.sample_counts?.train} | Test: {selectedModel.sample_counts?.test}
              </p>
            </div>
          </div>

          {/* Model Specs & Leakage Audit Strip */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-slate-500 block text-[10px]">MODEL ID</span>
                <span className="text-slate-200 font-bold">{selectedModel.model_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ALGORITHM</span>
                <span className="text-cyan-400 font-bold uppercase">{selectedModel.model_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">TARGET TIMEFRAME</span>
                <span className="text-slate-200 font-bold">{selectedModel.symbol} {selectedModel.timeframe}</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-400">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                <span>{selectedModel.created_at}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-emerald-950/40 border border-emerald-800/40 px-3 py-1.5 rounded-lg text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
              <span className="font-semibold text-[11px]">AUDITED: Zero Lookahead & Purged Split</span>
            </div>
          </div>

          {/* Dual Panel: Confusion Matrix & Feature Importances */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confusion Matrix */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-2 flex items-center justify-between">
                <span>OUT-OF-SAMPLE CONFUSION MATRIX</span>
                <span className="text-[10px] font-mono text-slate-400">Predicted vs Actual</span>
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Distribution of holdout sample classifications on unseen market candles.
              </p>

              {selectedModel.metrics.confusion_matrix && selectedModel.metrics.confusion_matrix.length === 3 ? (
                <div className="overflow-x-auto">
                  <div className="min-w-[320px]">
                    <div className="grid grid-cols-4 gap-2 text-center font-mono text-xs mb-2">
                      <div className="text-slate-500 text-[10px] self-end">Actual \ Pred</div>
                      <div className="font-bold text-emerald-400 bg-slate-950/60 p-2 rounded">BUY</div>
                      <div className="font-bold text-slate-300 bg-slate-950/60 p-2 rounded">NEUTRAL</div>
                      <div className="font-bold text-rose-400 bg-slate-950/60 p-2 rounded">SELL</div>
                    </div>

                    {selectedModel.metrics.confusion_matrix.map((row, rIdx) => (
                      <div key={rIdx} className="grid grid-cols-4 gap-2 text-center font-mono text-xs mb-2 items-center">
                        <div className="font-bold text-slate-400 text-left pl-2">
                          {classLabels[rIdx]}
                        </div>
                        {row.map((val, cIdx) => {
                          const isCorrect = rIdx === cIdx;
                          return (
                            <div 
                              key={cIdx} 
                              className={`p-3 rounded-lg border font-bold text-sm transition-all ${
                                isCorrect 
                                  ? 'bg-emerald-950/50 border-emerald-700/60 text-emerald-300' 
                                  : 'bg-slate-950/70 border-slate-800 text-slate-400'
                              }`}
                            >
                              {val}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500 font-mono">
                  Confusion matrix not recorded for this model artifact.
                </div>
              )}
            </div>

            {/* Feature Importance Bar Chart */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-2 flex items-center justify-between">
                <span>FEATURE IMPORTANCE RANKINGS</span>
                <span className="text-[10px] font-mono text-slate-400">Gini / Weight</span>
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Relative influence of scale-independent indicators on decision boundary.
              </p>

              {selectedModel.feature_importances && Object.keys(selectedModel.feature_importances).length > 0 ? (
                <div className="space-y-2.5 font-mono text-xs">
                  {Object.entries(selectedModel.feature_importances)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 8)
                    .map(([name, score], idx) => {
                      const maxScore = Math.max(...Object.values(selectedModel.feature_importances));
                      const pct = maxScore > 0 ? (score / maxScore) * 100 : 0;
                      return (
                        <div key={name}>
                          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
                            <span className="flex items-center gap-1.5">
                              <span className="text-slate-500">{idx + 1}.</span>
                              <span className="font-semibold">{name}</span>
                            </span>
                            <span className="text-cyan-400">{(score * 100).toFixed(2)}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800/80">
                            <div 
                              className="bg-gradient-to-r from-cyan-600 to-indigo-500 h-full rounded-full transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500 font-mono">
                  Linear weights or feature importances not exported.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
