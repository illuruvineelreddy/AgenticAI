'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Sidebar from '@/components/Sidebar';
import LiveChart from '@/components/LiveChart';
import { api } from '@/lib/api';
import { ReplayStatus } from '@/lib/types';
import { 
  Play, Pause, Square, FastForward, Sliders, Calendar, PlayCircle, Loader2, AlertCircle 
} from 'lucide-react';

export default function Replay() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [startDate, setStartDate] = useState('2026-05-01');
  const [endDate, setEndDate] = useState('2026-05-15');
  const [speed, setSpeed] = useState(1.0);
  const [status, setStatus] = useState<ReplayStatus>({
    running: false,
    paused: false,
    speed: 1.0,
    symbol: '',
  });

  const { data: config } = useQuery({
    queryKey: ['system-config'],
    queryFn: api.getConfig,
  });

  const watchlist = config?.watchlist || ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'];

  // Query replay status every 3 seconds while running
  useEffect(() => {
    let timer: NodeJS.Timeout;
    const fetchStatus = async () => {
      try {
        const data = await api.getReplayStatus();
        setStatus(data);
        if (data.running) {
          timer = setTimeout(fetchStatus, 3000);
        }
      } catch (e) {
        console.error("Failed to query replay status", e);
      }
    };

    fetchStatus();
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [status.running]);

  const handleStart = async () => {
    try {
      const res = await api.startReplay({
        symbol,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        speed,
      });
      if (res.status === 'success') {
        setStatus({
          running: true,
          paused: false,
          speed,
          symbol,
          start_date: startDate,
          end_date: endDate,
        });
      }
    } catch (e) {
      alert("Failed to start replay. Make sure database contains historical candles.");
    }
  };

  const handlePause = async () => {
    try {
      if (status.paused) {
        await api.resumeReplay();
        setStatus(prev => ({ ...prev, paused: false }));
      } else {
        await api.pauseReplay();
        setStatus(prev => ({ ...prev, paused: true }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStop = async () => {
    try {
      await api.stopReplay();
      setStatus({
        running: false,
        paused: false,
        speed: 1.0,
        symbol: '',
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleSpeedChange = async (newSpeed: number) => {
    setSpeed(newSpeed);
    if (status.running) {
      try {
        await api.setReplaySpeed(newSpeed);
        setStatus(prev => ({ ...prev, speed: newSpeed }));
      } catch (e) {
        console.error(e);
      }
    }
  };

  return (
    <div className="flex bg-[#07070a] min-h-screen text-slate-100">
      <Sidebar />
      
      <main className="flex-1 p-8 space-y-6 overflow-y-auto max-h-screen">
        {/* Header */}
        <div className="flex justify-between items-center border-b border-slate-900 pb-4">
          <div>
            <h2 className="text-2xl font-black tracking-wider text-white">HISTORICAL REPLAY CONSOLE</h2>
            <p className="text-xs text-slate-400 font-medium">Replay market history at adjustable speed to validate real-time execution</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Controls Panel */}
          <div className="glass-panel p-6 rounded-xl border border-slate-900 h-fit space-y-4">
            <h3 className="font-bold text-white text-sm uppercase tracking-wider border-b border-slate-900 pb-2">Control Console</h3>
            
            {status.running ? (
              // Active Replay Dashboard State
              <div className="space-y-4">
                <div className="bg-slate-950 p-4 border border-slate-900 rounded-lg space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Replay Status</span>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold ${
                      status.paused ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400 animate-pulse'
                    }`}>
                      {status.paused ? 'PAUSED' : 'STREAMING'}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Symbol</span>
                    <span className="text-white font-bold">{status.symbol}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Speed</span>
                    <span className="text-blue-400 font-bold">{status.speed}x</span>
                  </div>
                </div>

                {/* Control Buttons */}
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handlePause}
                    className="flex items-center justify-center gap-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer"
                  >
                    {status.paused ? (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        Resume
                      </>
                    ) : (
                      <>
                        <Pause className="w-3.5 h-3.5" />
                        Pause
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleStop}
                    className="flex items-center justify-center gap-1.5 bg-rose-950/20 hover:bg-rose-950/40 border border-rose-950/30 text-rose-400 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5" />
                    Stop
                  </button>
                </div>
              </div>
            ) : (
              // Setup Replay State
              <div className="space-y-4">
                {/* Symbol Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs text-slate-400 font-semibold uppercase">Symbol</label>
                  <select
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    {watchlist.map(sym => (
                      <option key={sym} value={sym}>{sym}</option>
                    ))}
                  </select>
                </div>

                {/* Date range pickers */}
                <div className="space-y-1.5">
                  <label className="text-xs text-slate-400 font-semibold uppercase">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-slate-400 font-semibold uppercase">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>

                {/* Trigger Start */}
                <button
                  onClick={handleStart}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold py-2 px-4 rounded-lg transition-colors cursor-pointer"
                >
                  <Play className="w-4 h-4" />
                  Start Replay
                </button>
              </div>
            )}

            {/* Replay speed control */}
            <div className="space-y-2 border-t border-slate-900 pt-4">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400 font-semibold uppercase">Replay Speed</span>
                <span className="text-blue-400 font-bold">{speed}x</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                step="1"
                value={speed}
                onChange={(e) => handleSpeedChange(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-semibold">
                <span>1x (Real)</span>
                <span>50x</span>
                <span>100x (Max)</span>
              </div>
            </div>
          </div>

          {/* Visualization Chart */}
          <div className="lg:col-span-3 space-y-6">
            {status.running ? (
              <LiveChart initialSymbol={status.symbol} />
            ) : (
              <div className="glass-panel p-20 rounded-xl border border-slate-900 text-center text-slate-500 font-medium space-y-3">
                <PlayCircle className="w-12 h-12 text-slate-700 mx-auto" />
                <p>Launch the Replay streaming to display candles in the chart overlay.</p>
                <span className="text-xs text-slate-600 max-w-sm block mx-auto leading-relaxed">
                  Note: the Replay engine streams records directly into the live pipeline. Strategy agents will execute trades in paper mode as candles stream.
                </span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
