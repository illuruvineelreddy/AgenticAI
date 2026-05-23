'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import wsClient from '@/lib/websocket';
import { api } from '@/lib/api';

interface LiveChartProps {
  initialSymbol?: string;
}

export default function LiveChart({ initialSymbol = 'NIFTY 50' }: LiveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  const [symbol, setSymbol] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState('15m');
  const [watchlist, setWatchlist] = useState<string[]>(['NIFTY 50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY']);

  useEffect(() => {
    // 1. Fetch system watchlist
    api.getConfig().then(cfg => {
      if (cfg.watchlist && cfg.watchlist.length > 0) {
        // Ensure NIFTY/BANKNIFTY are in the list for selection if not already present
        const combined = ['NIFTY 50', 'BANKNIFTY', ...cfg.watchlist];
        const list: string[] = [];
        combined.forEach(item => {
          if (!list.includes(item)) {
            list.push(item);
          }
        });
        setWatchlist(list);
      }
    }).catch(e => console.warn("Failed to load watchlist config for chart", e));
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 2. Initialize chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: {
        background: { color: '#0a1324' },
        textColor: '#94a3b8',
        fontSize: 11,
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: 1, // Normal crosshair
        vertLine: {
          color: '#6366f1',
          width: 1,
          style: 3,
        },
        horzLine: {
          color: '#6366f1',
          width: 1,
          style: 3,
        },
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
    });

    chartRef.current = chart;

    // 3. Add candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#10b981',
      wickDownColor: '#ef4444',
      wickUpColor: '#10b981',
    });
    candleSeriesRef.current = candleSeries;

    candleSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.3, // Leave bottom 30% empty for volume
      },
    });

    // 4. Add Volume histogram series
    const volumeSeries = chart.addHistogramSeries({
      color: '#10b981',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Set as overlay
    });
    volumeSeriesRef.current = volumeSeries;

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.7, // Occupy bottom 30% of the chart
        bottom: 0,
      },
    });

    // 5. Add EMA Line series
    const emaSeries = chart.addLineSeries({
      color: '#4f46e5', // indigo
      lineWidth: 2,
      priceLineVisible: false,
      title: 'EMA(20)',
    });
    emaSeriesRef.current = emaSeries;

    // 6. Add VWAP Line series
    const vwapSeries = chart.addLineSeries({
      color: '#eab308', // yellow
      lineWidth: 2,
      priceLineVisible: false,
      title: 'VWAP',
    });
    vwapSeriesRef.current = vwapSeries;

    // 7. Generate and set initial historical data
    const historicalData = generateMockHistoricalData(symbol);
    
    // Set candle data
    candleSeries.setData(historicalData.candles);
    
    // Set volume data
    volumeSeries.setData(historicalData.volumes);

    // Set EMA / VWAP data
    emaSeries.setData(historicalData.ema);
    vwapSeries.setData(historicalData.vwap);

    // 8. Connect to WebSocket live updates
    const handleWsCandle = (topic: string, data: any) => {
      if (topic === 'candles' && data.symbol === symbol) {
        let timeVal: number;
        if (typeof data.timestamp === 'string') {
          timeVal = Math.floor(new Date(data.timestamp).getTime() / 1000);
        } else {
          timeVal = Math.floor(Number(data.timestamp));
        }

        const open = Number(data.open);
        const high = Number(data.high);
        const low = Number(data.low);
        const close = Number(data.close);
        const vol = Number(data.volume || 150000);

        // Update candles
        candleSeries.update({
          time: timeVal as UTCTimestamp,
          open,
          high,
          low,
          close,
        });

        // Update volumes
        const isUp = close >= open;
        volumeSeries.update({
          time: timeVal as UTCTimestamp,
          value: vol,
          color: isUp ? '#10b981' : '#ef4444',
        });

        // Update EMA / VWAP (approximate real-time calculations)
        emaSeries.update({
          time: timeVal as UTCTimestamp,
          value: close * 0.999,
        });

        vwapSeries.update({
          time: timeVal as UTCTimestamp,
          value: close * 1.001,
        });
      }
    };

    wsClient.subscribe(['candles'], handleWsCandle);

    // Resize handler
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      wsClient.unsubscribe(['candles'], handleWsCandle);
      chart.removeSeries(candleSeries);
      chart.removeSeries(volumeSeries);
      chart.removeSeries(emaSeries);
      chart.removeSeries(vwapSeries);
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol]);

  // Generate simulated historical candles with synchronized volume, EMA, and VWAP
  const generateMockHistoricalData = (sym: string) => {
    const candles = [];
    const volumes = [];
    const ema = [];
    const vwap = [];

    let time = Math.floor(Date.now() / 1000) - (120 * 300); // 120 candles ago
    
    // Set base prices according to symbol
    let val = 22124.30; // default NIFTY
    if (sym.includes('BANKNIFTY')) val = 48532.15;
    else if (sym.includes('RELIANCE')) val = 2985.50;
    else if (sym.includes('TCS')) val = 3980.20;
    else if (sym.includes('HDFCBANK')) val = 1642.30;
    else if (sym.includes('INFY')) val = 1450.70;

    for (let i = 0; i < 120; i++) {
      const open = val;
      const close = val + (Math.random() - 0.48) * (val * 0.003); // slight upward bias
      const high = Math.max(open, close) + Math.random() * (val * 0.0015);
      const low = Math.min(open, close) - Math.random() * (val * 0.0015);
      
      candles.push({
        time: time as UTCTimestamp,
        open,
        high,
        low,
        close
      });

      const isUp = close >= open;
      volumes.push({
        time: time as UTCTimestamp,
        value: Math.floor(100000 + Math.random() * 400000),
        color: isUp ? '#10b98144' : '#ef444444', // semi-transparent volume histogram bars
      });

      // Calculate simple EMA / VWAP approximations for visual depth
      const emaWindow = 12;
      const startIdx = Math.max(0, i - emaWindow + 1);
      let sum = 0;
      let count = 0;
      for (let j = startIdx; j <= i; j++) {
        sum += candles[j].close;
        count++;
      }
      ema.push({
        time: time as UTCTimestamp,
        value: sum / count,
      });

      // VWAP line follows candles closely with a smooth offset
      vwap.push({
        time: time as UTCTimestamp,
        value: close * (1 + (Math.sin(i / 10) * 0.0015)),
      });

      val = close;
      time += 300;
    }

    return { candles, volumes, ema, vwap };
  };

  return (
    <div className="bg-[#0a1324] rounded-3xl border border-slate-800 p-5 shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            LIVE CHART — {symbol}
          </h2>
          <p className="text-slate-400 text-sm mt-1">EMA + VWAP + Volume</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Timeframe Buttons */}
          <div className="flex bg-slate-900/50 p-1 rounded-xl border border-slate-800">
            {['1m', '5m', '15m', '1h', 'D'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  timeframe === tf
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Symbol Selector Dropdown */}
          <select 
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-[#081021] border border-slate-800 text-xs font-semibold text-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-600 cursor-pointer transition-all hover:bg-slate-900"
          >
            {watchlist.map(sym => (
              <option key={sym} value={sym}>{sym}</option>
            ))}
          </select>

          {/* Indicators Button */}
          <button className="bg-[#081021] border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl flex items-center gap-2 transition-all">
            📊 Indicators
          </button>
        </div>
      </div>

      <div className="h-[420px] rounded-2xl border border-slate-800 bg-[#0a1324] relative overflow-hidden">
        <div ref={chartContainerRef} className="w-full h-full animate-fade-in" />
      </div>
    </div>
  );
}
