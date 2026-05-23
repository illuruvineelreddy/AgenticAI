'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { SystemConfig } from '@/lib/types';
import { 
  Settings as SettingsIcon, ShieldCheck, Wallet, MessageSquare, AlertCircle, Save, CheckCircle2 
} from 'lucide-react';

export default function SettingsPage() {
  const { data: config } = useQuery({
    queryKey: ['system-config'],
    queryFn: api.getConfig,
  });

  const [paperMode, setPaperMode] = useState(true);
  const [maxRisk, setMaxRisk] = useState(1.0);
  const [maxDrawdown, setMaxDrawdown] = useState(3.0);
  const [maxPositions, setMaxPositions] = useState(5);
  const [capital, setCapital] = useState(1000000);
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (config) {
      setPaperMode(config.paper_trading_mode);
      setMaxRisk(config.max_risk_per_trade * 100);
      setMaxDrawdown(config.max_daily_drawdown * 100);
      setMaxPositions(config.max_open_positions);
      setCapital(config.default_capital);
    }
  }, [config]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
    // In a full implementation, we would send a PUT/POST to /api/v1/settings/update
  };

  return (
    <div className="flex bg-[#07070a] min-h-screen text-slate-100">
      <Sidebar />
      
      <main className="flex-1 p-8 space-y-6 overflow-y-auto max-h-screen">
        {/* Header */}
        <div className="flex justify-between items-center border-b border-slate-900 pb-4">
          <div>
            <h2 className="text-2xl font-black tracking-wider text-white">SYSTEM SETTINGS</h2>
            <p className="text-xs text-slate-400 font-medium">Configure risk parameters, execution boundaries, and alerting services</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="max-w-3xl space-y-6">
          {saveSuccess && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-4 rounded-xl flex items-center gap-2 text-sm font-semibold tracking-wide shadow-lg">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              Settings successfully saved (simulated update).
            </div>
          )}

          {/* Core Configuration */}
          <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
              <div>
                <h3 className="font-bold text-white tracking-wide">Execution Mode</h3>
                <p className="text-xs text-slate-400">Toggle live trading status or simulated sandbox mode</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-900 rounded-lg">
              <div>
                <span className="text-xs font-semibold text-white uppercase tracking-wider block">Paper Trading Sandbox</span>
                <span className="text-[10px] text-slate-500 mt-0.5 block leading-relaxed max-w-md">
                  All trade orders are simulated in memory with slippage, latency, and full transaction cost computations. No capital risk.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setPaperMode(!paperMode)}
                className={`w-14 h-8 flex items-center rounded-full p-1 transition-all duration-300 ${
                  paperMode ? 'bg-blue-600 justify-end' : 'bg-slate-800 justify-start'
                }`}
              >
                <span className="w-6 h-6 rounded-full bg-white shadow-md transition-transform" />
              </button>
            </div>
          </div>

          {/* Risk Management limits */}
          <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
              <Wallet className="w-5 h-5 text-blue-400" />
              <div>
                <h3 className="font-bold text-white tracking-wide">Risk Controls</h3>
                <p className="text-xs text-slate-400">Strict portfolio bounds assessed by the Risk Agent</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Max Risk Per Trade (%)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={maxRisk}
                  onChange={(e) => setMaxRisk(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              
              <div className="space-y-1.5">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Max Daily Drawdown (%)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={maxDrawdown}
                  onChange={(e) => setMaxDrawdown(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Max Open Positions</label>
                <input 
                  type="number" 
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Initial Capital (₹)</label>
                <input 
                  type="number" 
                  value={capital}
                  onChange={(e) => setCapital(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>
          </div>

          {/* Telegram alerts */}
          <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
              <MessageSquare className="w-5 h-5 text-blue-400" />
              <div>
                <h3 className="font-bold text-white tracking-wide">Telegram Notifications</h3>
                <p className="text-xs text-slate-400">Stream critical errors or trades straight to your chats</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-900 rounded-lg">
              <div>
                <span className="text-xs font-semibold text-white uppercase tracking-wider block">Enable Bot Messaging</span>
              </div>
              <button
                type="button"
                onClick={() => setTelegramEnabled(!telegramEnabled)}
                className={`w-14 h-8 flex items-center rounded-full p-1 transition-all duration-300 ${
                  telegramEnabled ? 'bg-blue-600 justify-end' : 'bg-slate-800 justify-start'
                }`}
              >
                <span className="w-6 h-6 rounded-full bg-white shadow-md transition-transform" />
              </button>
            </div>

            {telegramEnabled && (
              <div className="grid grid-cols-2 gap-4 animate-fade-in">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Bot Token</label>
                  <input 
                    type="password" 
                    value={telegramToken}
                    onChange={(e) => setTelegramToken(e.target.value)}
                    placeholder="Enter Telegram Bot token"
                    className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Chat ID</label>
                  <input 
                    type="text" 
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    placeholder="Enter Telegram Chat ID"
                    className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 px-6 rounded-lg transition-colors cursor-pointer"
          >
            <Save className="w-4 h-4" />
            Save Configuration
          </button>
        </form>
      </main>
    </div>
  );
}
