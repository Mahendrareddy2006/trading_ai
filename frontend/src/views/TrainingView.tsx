import React, { useState } from 'react';
import { 
  FlaskConical, 
  Play, 
  Loader2, 
  CheckCircle2, 
  ShieldCheck, 
  Sliders, 
  Info,
  Clock
} from 'lucide-react';
import { api } from '../services/api';

interface TrainingViewProps {
  onTrainingComplete: () => void;
}

export const TrainingView: React.FC<TrainingViewProps> = ({ onTrainingComplete }) => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [modelType, setModelType] = useState('random_forest');
  const [nEstimators, setNEstimators] = useState(25);
  const [maxDepth, setMaxDepth] = useState(5);

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStartTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.startTraining({
        symbol,
        timeframe,
        model_type: modelType,
        n_estimators: Number(nEstimators),
        max_depth: Number(maxDepth)
      });
      setResult(res);
      onTrainingComplete();
    } catch (err: any) {
      setError(err.message || 'Training failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-indigo-400" />
          <span>TRAINING & EXPERIMENT MANAGEMENT</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Train reproducible machine learning models on validated historical Binance klines with strictly chronological train/validation/test splits.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Training Config Form */}
        <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl p-6 backdrop-blur-md shadow-xl">
          <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-4 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>MODEL HYPERPARAMETERS & CONFIGURATION</span>
          </h3>

          <form onSubmit={handleStartTraining} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Asset Symbol */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  TARGET ASSET (SYMBOL)
                </label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="BTCUSDT">BTCUSDT (Bitcoin)</option>
                  <option value="ETHUSDT">ETHUSDT (Ethereum)</option>
                  <option value="BNBUSDT">BNBUSDT (Binance Coin)</option>
                  <option value="SOLUSDT">SOLUSDT (Solana)</option>
                </select>
              </div>

              {/* Timeframe */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  FEATURE TIMEFRAME
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="1h">1-Hour (Primary Directional Engine)</option>
                  <option value="5m">5-Minute (Microstructure Timing)</option>
                  <option value="4h">4-Hour (Regime Filter)</option>
                </select>
              </div>

              {/* Model Architecture */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  MODEL ARCHITECTURE
                </label>
                <select
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="random_forest">Random Forest Ensemble (Non-linear)</option>
                  <option value="decision_tree">Decision Tree (Fast baseline)</option>
                  <option value="logistic_regression">Logistic Regression (Linear baseline)</option>
                </select>
              </div>

              {/* Trees / Estimators */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  NUMBER OF ESTIMATORS: <span className="text-cyan-400 font-bold">{nEstimators}</span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="100"
                  step="5"
                  value={nEstimators}
                  onChange={(e) => setNEstimators(Number(e.target.value))}
                  className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-cyan-500 mt-2"
                />
              </div>

              {/* Max Depth */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  MAX TREE DEPTH: <span className="text-cyan-400 font-bold">{maxDepth}</span>
                </label>
                <input
                  type="range"
                  min="2"
                  max="12"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                  className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-cyan-500 mt-2"
                />
              </div>
            </div>

            {/* Launch Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/40 transition-all disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>TRAINING MODEL & EVALUATING HOLDOUT...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>LAUNCH TRAINING PIPELINE</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Results Display */}
          {result && (
            <div className="mt-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 font-mono text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-bold mb-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Training Successful & Model Registered!</span>
              </div>
              <p className="text-slate-300">Model ID: <span className="text-cyan-300">{result.model_id}</span></p>
              <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-emerald-900/60 text-center">
                <div>
                  <span className="text-slate-500 block text-[10px]">HOLDOUT ACCURACY</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {(result.metrics.accuracy * 100).toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">BALANCED ACCURACY</span>
                  <span className="text-cyan-400 font-bold text-sm">
                    {(result.metrics.balanced_accuracy * 100).toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">MACRO F1</span>
                  <span className="text-indigo-400 font-bold text-sm">
                    {(result.metrics.macro_f1 * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs font-mono text-rose-300">
              Training Error: {error}
            </div>
          )}
        </div>

        {/* Right 1 Column: Methodology & Safeguards */}
        <div className="space-y-4">
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Anti-Leakage Protocol</span>
            </h4>

            <ul className="space-y-3 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200">Chronological Split:</strong> 70% Train, 15% Validation, 15% Holdout. Zero random shuffling.
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200">Scale-Independent Features:</strong> Stationary indicators (EMA spreads, ATR ratio, normalized RSI) prevents cross-asset leakage.
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200">Platt Calibration:</strong> Sigmoid calibration on validation fold produces true calibrated probabilities.
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200">Purged Embargo:</strong> Target label horizons are purged at fold transitions to avoid window overlap.
                </div>
              </li>
            </ul>
          </div>

          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md font-mono text-xs">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span>Training Pipeline</span>
            </h4>
            <ol className="list-decimal list-inside space-y-1.5 text-slate-400 text-[11px]">
              <li>Load historical UTC candles</li>
              <li>Compute 17 stationary features</li>
              <li>Construct ATR-barrier targets</li>
              <li>Purge boundary lookaheads</li>
              <li>Fit model on train fold</li>
              <li>Calibrate on validation fold</li>
              <li>Evaluate untouched holdout</li>
              <li>Persist artifact to disk</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};
