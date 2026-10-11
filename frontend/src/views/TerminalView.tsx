import React, { useState } from 'react';
import { 
  Candle, 
  Prediction, 
  Position,
  TickerData
} from '../types';
import { CandlestickChart } from '../components/CandlestickChart';
import { 
  Compass, 
  Layers, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle
} from 'lucide-react';

interface TerminalViewProps {
  candles: Candle[];
  symbol: string;
  timeframe: string;
  onSymbolChange: (sym: string) => void;
  onTimeframeChange: (tf: string) => void;
  prediction: Prediction | null;
  activePosition: Position | undefined;
  ticker?: TickerData;
  onClosePosition: (symbol: string) => void;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  candles,
  symbol,
  timeframe,
  onSymbolChange,
  onTimeframeChange,
  prediction,
  activePosition,
  ticker,
  onClosePosition
}) => {
  const [symbols] = useState(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']);
  const [timeframes] = useState(['5m', '1h', '4h']);

  const candlePrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const markPrice = ticker?.price || candlePrice;
  const changePct = ticker?.change_24h ?? 0;
  const isUp = changePct >= 0;

  return (
    <div className="space-y-6">
      {/* Symbol & Timeframe Toolbar with Real Exchange Prices */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          {/* Symbol Select Buttons */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
            {symbols.map((sym) => (
              <button
                key={sym}
                onClick={() => onSymbolChange(sym)}
                className={`px-3 py-1.5 rounded-md text-xs font-mono font-bold transition-all ${
                  symbol === sym
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {sym}
              </button>
            ))}
          </div>

          {/* Timeframe Select Buttons */}
          <div className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => onTimeframeChange(tf)}
                className={`px-2.5 py-1.5 rounded-md text-xs font-mono font-semibold transition-all ${
                  timeframe === tf
                    ? 'bg-slate-700 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Real-time Ticker Stats from Binance */}
        <div className="flex items-center gap-6 font-mono text-xs">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Real Mark Price</span>
            <span className="text-base font-black text-slate-100">
              ${markPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">24h Change</span>
            <span className={`font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? '+' : ''}{changePct.toFixed(2)}%
            </span>
          </div>
          {ticker?.high_24h && (
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">24h High / Low</span>
              <span className="text-slate-300">
                ${ticker.high_24h.toFixed(1)} / ${ticker.low_24h.toFixed(1)}
              </span>
            </div>
          )}
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Live Candles</span>
            <span className="text-slate-300 font-semibold">{candles.length}</span>
          </div>
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left 3 Columns: Interactive Candlestick Chart */}
        <div className="lg:col-span-3">
          <CandlestickChart
            candles={candles}
            symbol={symbol}
            timeframe={timeframe}
            stopLoss={activePosition?.stop_loss}
            takeProfit={activePosition?.take_profit}
          />
        </div>

        {/* Right 1 Column: Decision & Multi-Timeframe Alignment */}
        <div className="space-y-4">
          {/* Multi-Timeframe Alignment Matrix */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span>Multi-TF Decision Flow</span>
            </h4>

            <div className="space-y-2.5 font-mono text-xs">
              {/* 4H Macro Regime */}
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                <div className="flex justify-between items-center text-[11px] text-slate-400 mb-1">
                  <span>1. 4H Macro Regime</span>
                  <span className="text-[10px] px-1 rounded bg-slate-800">EMA Trend</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200 uppercase">{prediction?.regime || 'CHOP / NEUTRAL'}</span>
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                </div>
              </div>

              {/* 1H Directional ML Model */}
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                <div className="flex justify-between items-center text-[11px] text-slate-400 mb-1">
                  <span>2. 1H Directional Edge</span>
                  <span className="text-[10px] px-1 rounded bg-slate-800">Calibrated ML</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={`font-bold ${
                    prediction?.direction === 'LONG' ? 'text-emerald-400' : prediction?.direction === 'SHORT' ? 'text-rose-400' : 'text-slate-400'
                  }`}>
                    {prediction?.direction || 'NEUTRAL'}
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    Edge: {prediction ? `${(prediction.edge * 100).toFixed(1)}%` : '--'}
                  </span>
                </div>
              </div>

              {/* 5M Entry Timing Engine */}
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                <div className="flex justify-between items-center text-[11px] text-slate-400 mb-1">
                  <span>3. 5M Timing Engine</span>
                  <span className="text-[10px] px-1 rounded bg-slate-800">Microstructure</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-300">
                    {activePosition ? 'POSITION ACTIVE' : 'SCANNING TRIGGER'}
                  </span>
                  <CheckCircle2 className={`w-3.5 h-3.5 ${activePosition ? 'text-emerald-400' : 'text-slate-500'}`} />
                </div>
              </div>
            </div>
          </div>

          {/* Model Probabilities Detail */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5 text-indigo-400" />
                <span>Class Probabilities</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">P(y | x)</span>
            </h4>

            {prediction ? (
              <div className="space-y-2 text-xs font-mono">
                <div>
                  <div className="flex justify-between text-emerald-400 text-[11px] mb-0.5">
                    <span>BUY / LONG:</span>
                    <span>{(prediction.probabilities.BUY * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full" style={{ width: `${prediction.probabilities.BUY * 100}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-slate-400 text-[11px] mb-0.5">
                    <span>NEUTRAL:</span>
                    <span>{(prediction.probabilities.NEUTRAL * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-slate-500 h-full" style={{ width: `${prediction.probabilities.NEUTRAL * 100}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-rose-400 text-[11px] mb-0.5">
                    <span>SELL / SHORT:</span>
                    <span>{(prediction.probabilities.SELL * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-rose-500 h-full" style={{ width: `${prediction.probabilities.SELL * 100}%` }} />
                  </div>
                </div>

                {prediction.abstention_reason && (
                  <div className="mt-3 p-2 rounded bg-slate-800/80 border border-slate-700 text-[11px] text-slate-300 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                    <span>Filter: {prediction.abstention_reason}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-4 text-center text-xs text-slate-500 font-mono">
                No prediction received yet
              </div>
            )}
          </div>

          {/* Active Position Info for Symbol */}
          {activePosition ? (
            <div className="bg-slate-900/70 border border-emerald-900/50 rounded-xl p-4 backdrop-blur-md">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-emerald-400">ACTIVE POSITION</span>
                <span className="text-xs font-mono font-bold text-slate-200">{activePosition.side}</span>
              </div>
              <div className="space-y-1 font-mono text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Entry Price:</span>
                  <span>${activePosition.entry_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Quantity:</span>
                  <span>{activePosition.quantity.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Unrealized P&L:</span>
                  <span className={activePosition.unrealized_pnl >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                    ${activePosition.unrealized_pnl.toFixed(2)}
                  </span>
                </div>
              </div>
              <button
                onClick={() => onClosePosition(symbol)}
                className="mt-3 w-full py-1.5 bg-rose-600/80 hover:bg-rose-600 text-white rounded-lg text-xs font-bold transition-colors"
              >
                Close Position Now
              </button>
            </div>
          ) : (
            <div className="p-3 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500 font-mono">
              <HelpCircle className="w-4 h-4 mx-auto mb-1 text-slate-600" />
              Flat on {symbol}. Waiting for aligned 3-timeframe setup.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
