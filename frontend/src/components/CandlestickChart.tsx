import React, { useState } from 'react';
import { Candle } from '../types';

interface ChartProps {
  candles: Candle[];
  symbol: string;
  timeframe: string;
  stopLoss?: number | null;
  takeProfit?: number | null;
}

export const CandlestickChart: React.FC<ChartProps> = ({
  candles,
  symbol,
  timeframe,
  stopLoss,
  takeProfit
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (!candles || candles.length === 0) {
    return (
      <div className="h-96 flex flex-col items-center justify-center bg-slate-900/60 rounded-xl border border-slate-800 text-slate-500">
        <p className="font-medium">No candlestick data available</p>
        <p className="text-xs mt-1">Select an active symbol and timeframe</p>
      </div>
    );
  }

  // Slice to most recent 60 candles for crisp rendering
  const displayCandles = candles.slice(-60);
  const n = displayCandles.length;

  const width = 850;
  const height = 380;
  const padding = { top: 25, right: 65, bottom: 40, left: 15 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const minPrice = Math.min(...displayCandles.map((c) => c.low));
  const maxPrice = Math.max(...displayCandles.map((c) => c.high));
  const priceRange = maxPrice - minPrice || 1.0;

  const maxVol = Math.max(...displayCandles.map((c) => c.volume)) || 1.0;

  const getY = (val: number) => {
    return padding.top + chartHeight - ((val - minPrice) / priceRange) * chartHeight;
  };

  const candleWidth = Math.max(3, chartWidth / n - 4);

  const hoveredCandle = hoverIndex !== null && displayCandles[hoverIndex] ? displayCandles[hoverIndex] : displayCandles[displayCandles.length - 1];

  return (
    <div className="bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 p-4 shadow-xl">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-2">
        <div className="flex items-center gap-3">
          <span className="font-bold text-lg text-slate-100">{symbol}</span>
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-cyan-950/70 border border-cyan-800/50 text-cyan-400 font-mono">
            {timeframe}
          </span>
          <span className="text-xs text-slate-400 font-mono">
            {hoveredCandle.timestamp}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div><span className="text-slate-500">O:</span> <span className="text-slate-200">${hoveredCandle.open.toFixed(2)}</span></div>
          <div><span className="text-slate-500">H:</span> <span className="text-emerald-400">${hoveredCandle.high.toFixed(2)}</span></div>
          <div><span className="text-slate-500">L:</span> <span className="text-rose-400">${hoveredCandle.low.toFixed(2)}</span></div>
          <div><span className="text-slate-500">C:</span> <span className="font-bold text-slate-100">${hoveredCandle.close.toFixed(2)}</span></div>
          <div><span className="text-slate-500">Vol:</span> <span className="text-slate-400">{hoveredCandle.volume.toFixed(1)}</span></div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
          {/* Horizontal Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
            const p = minPrice + priceRange * ratio;
            const y = getY(p);
            return (
              <g key={idx}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                <text x={width - padding.right + 8} y={y + 4} fill="#64748b" fontSize="10" fontFamily="JetBrains Mono">
                  ${p.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Protective Order Levels */}
          {stopLoss && stopLoss >= minPrice && stopLoss <= maxPrice && (
            <g>
              <line x1={padding.left} y1={getY(stopLoss)} x2={width - padding.right} y2={getY(stopLoss)} stroke="#f43f5e" strokeWidth="1.5" strokeDasharray="4 2" />
              <text x={width - padding.right + 6} y={getY(stopLoss) + 3} fill="#f43f5e" fontSize="9" fontWeight="bold" fontFamily="JetBrains Mono">
                SL ${stopLoss.toFixed(2)}
              </text>
            </g>
          )}

          {takeProfit && takeProfit >= minPrice && takeProfit <= maxPrice && (
            <g>
              <line x1={padding.left} y1={getY(takeProfit)} x2={width - padding.right} y2={getY(takeProfit)} stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 2" />
              <text x={width - padding.right + 6} y={getY(takeProfit) + 3} fill="#10b981" fontSize="9" fontWeight="bold" fontFamily="JetBrains Mono">
                TP ${takeProfit.toFixed(2)}
              </text>
            </g>
          )}

          {/* Candlesticks & Volume Bars */}
          {displayCandles.map((candle, idx) => {
            const x = padding.left + idx * (chartWidth / n) + (chartWidth / n - candleWidth) / 2;
            const isBullish = candle.close >= candle.open;
            const color = isBullish ? '#10b981' : '#f43f5e';

            const yHigh = getY(candle.high);
            const yLow = getY(candle.low);
            const yOpen = getY(candle.open);
            const yClose = getY(candle.close);

            const candleTop = Math.min(yOpen, yClose);
            const candleHeight = Math.max(2, Math.abs(yClose - yOpen));

            // Volume bar in bottom 20% of chart
            const volHeight = (candle.volume / maxVol) * 45;
            const volY = height - padding.bottom - volHeight;

            return (
              <g
                key={idx}
                onMouseEnter={() => setHoverIndex(idx)}
                className="cursor-crosshair"
              >
                {/* Volume Bar */}
                <rect
                  x={x}
                  y={volY}
                  width={candleWidth}
                  height={volHeight}
                  fill={isBullish ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}
                />

                {/* Wick */}
                <line
                  x1={x + candleWidth / 2}
                  y1={yHigh}
                  x2={x + candleWidth / 2}
                  y2={yLow}
                  stroke={color}
                  strokeWidth="1.2"
                />

                {/* Candle Body */}
                <rect
                  x={x}
                  y={candleTop}
                  width={candleWidth}
                  height={candleHeight}
                  fill={color}
                  rx="1"
                />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
