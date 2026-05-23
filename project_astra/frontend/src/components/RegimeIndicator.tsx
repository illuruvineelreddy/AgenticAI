'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ShieldCheck, ShieldAlert, Sparkles } from 'lucide-react';

export default function RegimeIndicator() {
  const { data } = useQuery({
    queryKey: ['market-status'],
    queryFn: api.getMarketStatus,
    refetchInterval: 10000,
  });

  const regimeData = data?.regime;
  const regimeName = regimeData?.regime || 'SIDEWAYS';
  const confidence = regimeData?.confidence || 0.5;
  const vix = regimeData?.vix_level || 15.0;
  const riskMultiplier = regimeData?.risk_multiplier || 1.0;
  const allowed = regimeData?.allowed_strategies || ['trend', 'vwap', 'breakout', 'scalping'];

  const getRegimeColor = (name: string) => {
    switch (name) {
      case 'BULL':
        return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
      case 'BEAR':
        return 'text-rose-400 border-rose-500/20 bg-rose-500/5';
      case 'HIGH_VOL':
        return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
      case 'EVENT_MODE':
        return 'text-red-500 border-red-500/20 bg-red-500/5 animate-pulse';
      default:
        return 'text-blue-400 border-blue-500/20 bg-blue-500/5';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
      <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
        <Sparkles className="w-5 h-5 text-blue-400" />
        <div>
          <h3 className="font-bold text-white tracking-wide">Market Regime Context</h3>
          <p className="text-xs text-slate-400">Dynamic system constraint calibrator</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Regime and Confidence */}
        <div className={`p-4 rounded-lg border flex flex-col justify-between ${getRegimeColor(regimeName)}`}>
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider opacity-60">Active State</span>
            <h4 className="text-2xl font-black mt-1 tracking-wider">{regimeName}</h4>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-[10px] font-bold mb-1 opacity-70">
              <span>State Confidence</span>
              <span>{(confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-950/60 rounded-full h-1.5 overflow-hidden">
              <div 
                className="h-1.5 rounded-full bg-current" 
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Volatility & Risk factor */}
        <div className="bg-slate-950/40 border border-slate-900 p-4 rounded-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">India VIX</span>
              <h4 className="text-2xl font-black text-white mt-1">{vix.toFixed(2)}</h4>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block text-right">Risk Scale</span>
              <h4 className="text-2xl font-black text-blue-400 mt-1 text-right">{riskMultiplier.toFixed(1)}x</h4>
            </div>
          </div>
          
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-4 bg-slate-900/30 p-2 rounded border border-slate-900/40">
            {riskMultiplier > 0.5 ? (
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
            )}
            <span className="font-semibold">
              {riskMultiplier > 0.5 
                ? 'Trading environment nominal. Standard position size.' 
                : 'Caution: high vol regime. Scaled down position risk.'}
            </span>
          </div>
        </div>
      </div>

      {/* Allowed Strategies list */}
      <div className="space-y-2">
        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Permitted Strategies</span>
        <div className="flex flex-wrap gap-1.5">
          {allowed.map((strat: string) => (
            <span 
              key={strat} 
              className="px-2 py-1 rounded bg-slate-900 border border-slate-900 text-[10px] font-semibold text-slate-300 uppercase tracking-wide"
            >
              {strat.replace('_', ' ')}
            </span>
          ))}
          {allowed.length === 0 && (
            <span className="text-rose-400 text-xs font-bold bg-rose-500/10 px-2 py-1 border border-rose-500/20 rounded">
              ALL STRATEGIES DISABLED
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
