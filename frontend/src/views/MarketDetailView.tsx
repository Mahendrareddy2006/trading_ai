import React, { useState, useEffect, useCallback } from 'react';
import { Candle, Position, Prediction, TickerData } from '../types';
import { api } from '../services/api';
import { CandlestickChart } from '../components/CandlestickChart';
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Layers, 
  Compass, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle,
  RefreshCw,
  Sliders,
  DollarSign,
  Activity
} from 'lucide-react';

interface MarketDetailViewProps {
  symbol: string;
  onSymbolChange: (symbol: string) => void;
  symbols: string[];
  ticker?: TickerData;
  activePosition?: Position;
  prediction?: Prediction | null;
  onClosePosition: (symbol: string) => void;
  onRefreshData?: () => void;
}

export const MarketDetailView: React.FC<MarketDetailViewProps> = ({
  symbol,
  onSymbolChange,
  symbols,
  ticker,
  activePosition,
  prediction,
  onClosePosition,
  onRefreshData
}) => {
  const [timeframe, setTimeframe] = useState('1h');
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];

  // Fetch candles on symbol or timeframe change
  const fetchCandles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const c = await api.getCandles(symbol, timeframe, 80);
      setCandles(c);
    } catch (e: any) {
      console.error('Error fetching candles:', e);
      setError('Unable to fetch live candlestick history from Binance.');
    } finally {
      setIsLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchCandles();
  }, [fetchCandles]);

  const candlePrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const currentPrice = ticker?.price || candlePrice;
  const changePct = ticker?.change_24h ?? 0;
  const changeAbs = ticker?.change_24h_abs ?? 0;
  const isUp = changePct >= 0;

  return (
    <div className="space-y-6">
      {/* Symbol & Timeframe Navigation Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-xl shadow-xl flex flex-wrap items-center justify-between gap-4">
        {/* Symbol Quick Select */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Symbol:</label>
            <select
              value={symbol}
              onChange={(e) => onSymbolChange(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm font-mono font-bold text-cyan-400 focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              {symbols.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Timeframe Selector */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all ${
                  timeframe === tf
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          <button
            onClick={fetchCandles}
            disabled={isLoading}
            className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-lg transition-colors"
            title="Refresh candles"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Real-time Metrics Pill */}
        <div className="flex flex-wrap items-center gap-6 font-mono text-xs">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Last Price</span>
            <span className="text-base font-black text-slate-100">
              ${currentPrice > 10 ? currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : currentPrice.toFixed(4)}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block text-[10px] uppercase">24h Change</span>
            <div className={`flex items-center gap-1 font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
              <span>{isUp ? '+' : ''}{changePct.toFixed(2)}% (${isUp ? '+' : ''}{changeAbs.toFixed(2)})</span>
            </div>
          </div>

          <div className="hidden sm:block">
            <span className="text-slate-500 block text-[10px] uppercase">Mark Price</span>
            <span className="text-slate-200">
              ${(ticker?.mark_price || currentPrice).toLocaleString()}
            </span>
          </div>

          <div className="hidden md:block">
            <span className="text-slate-500 block text-[10px] uppercase">Funding Rate (8h)</span>
            <span className={(ticker?.funding_rate ?? 0) >= 0 ? 'text-cyan-400' : 'text-amber-400'}>
              {ticker?.funding_rate !== undefined ? `${ticker.funding_rate >= 0 ? '+' : ''}${ticker.funding_rate.toFixed(4)}%` : '0.0000%'}
            </span>
          </div>

          <div className="hidden lg:block">
            <span className="text-slate-500 block text-[10px] uppercase">24h Volume</span>
            <span className="text-slate-200">
              ${((ticker?.quote_volume_24h || 0) / 1_000_000).toFixed(1)}M USDT
            </span>
          </div>
        </div>
      </div>

      {/* Candlestick Chart Area */}
      <div className="relative">
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-amber-950/40 border border-amber-800/40 text-xs text-amber-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>{error}</span>
          </div>
        )}

        <CandlestickChart
          candles={candles}
          symbol={symbol}
          timeframe={timeframe}
          stopLoss={activePosition?.stop_loss}
          takeProfit={activePosition?.take_profit}
        />
      </div>

      {/* Grid: AI Quantitative Signal & Simulated Paper Execution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quantitative Model Signal */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <h3 className="font-bold text-slate-100 text-sm">Quantitative ML Inference</h3>
              </div>
              <span className="text-[10px] font-mono text-slate-500 uppercase">
                Model: {prediction?.model_version || 'ensemble_rf'}
              </span>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Direction Forecast</span>
                <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-black ${
                  prediction?.direction === 'LONG'
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                    : prediction?.direction === 'SHORT'
                    ? 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {prediction?.direction || 'NEUTRAL / CASH'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Model Confidence</span>
                <span className="font-mono text-slate-200 font-bold">
                  {prediction ? `${(prediction.confidence * 100).toFixed(1)}%` : '33.3%'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Estimated Edge (α)</span>
                <span className="font-mono text-cyan-400 font-bold">
                  {prediction ? `+${(prediction.edge * 100).toFixed(2)}%` : '+0.00%'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Market Regime</span>
                <span className="font-mono text-slate-300">
                  {prediction?.regime || 'CHOP / CONSOLIDATION'}
                </span>
              </div>

              {/* Class Probability Distribution */}
              {prediction?.probabilities && (
                <div className="pt-2">
                  <span className="text-[11px] text-slate-500 block mb-1">Probability Distribution:</span>
                  <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                    <div className="bg-emerald-950/40 border border-emerald-800/40 p-2 rounded text-center">
                      <span className="text-emerald-400 block text-[9px]">BUY</span>
                      <span className="font-bold text-slate-100">{(prediction.probabilities.BUY * 100).toFixed(1)}%</span>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-2 rounded text-center">
                      <span className="text-slate-500 block text-[9px]">NEUTRAL</span>
                      <span className="font-bold text-slate-100">{(prediction.probabilities.NEUTRAL * 100).toFixed(1)}%</span>
                    </div>
                    <div className="bg-rose-950/40 border border-rose-800/40 p-2 rounded text-center">
                      <span className="text-rose-400 block text-[9px]">SELL</span>
                      <span className="font-bold text-slate-100">{(prediction.probabilities.SELL * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono">
            <span>Notice: Research forecast only. No simulated paper trades are placed without positive risk validation.</span>
          </div>
        </div>

        {/* Active Paper Position for this symbol */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <h3 className="font-bold text-slate-100 text-sm">Active Simulated Paper Position</h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                PAPER ONLY
              </span>
            </div>

            {activePosition ? (
              <div className="space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Position Side</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    activePosition.side === 'LONG' ? 'text-emerald-400 bg-emerald-950/60' : 'text-rose-400 bg-rose-950/60'
                  }`}>
                    {activePosition.side} ({activePosition.leverage}x)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Entry Price</span>
                  <span className="text-slate-200">${activePosition.entry_price.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Current Price</span>
                  <span className="text-slate-200">${activePosition.current_price.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Simulated Quantity</span>
                  <span className="text-slate-200">{activePosition.quantity.toFixed(4)} {symbol.replace('USDT', '')}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Unrealized PnL</span>
                  <span className={`font-black text-sm ${activePosition.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {activePosition.unrealized_pnl >= 0 ? '+' : ''}${activePosition.unrealized_pnl.toFixed(2)} ({activePosition.return_pct.toFixed(2)}%)
                  </span>
                </div>

                <div className="pt-3">
                  <button
                    onClick={() => onClosePosition(symbol)}
                    className="w-full py-2 bg-rose-950/60 hover:bg-rose-900 border border-rose-800/60 text-rose-300 font-semibold text-xs rounded-lg transition-colors"
                  >
                    Close Simulated Paper Position
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 font-mono text-xs">
                <ShieldAlert className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                <p className="text-slate-400 font-medium">No open simulated position for {symbol}.</p>
                <p className="text-[11px] text-slate-600 mt-1">The paper-trading engine will open a simulated trade when edge exceeds threshold.</p>
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono">
            <span>Safety Gate: Real exchange orders are blocked at the server level. Zero live risk.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
