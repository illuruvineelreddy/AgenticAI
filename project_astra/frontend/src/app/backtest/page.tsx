'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { BacktestResult } from '@/lib/types';
import { 
  BarChart2, Play, Calendar, DollarSign, Loader2, TrendingUp, CheckCircle, AlertTriangle 
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';

export default function Backtest() {
  const [strategy, setStrategy] = useState('trend_strategy');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [startDate, setStartDate] = useState('2026-05-01');
  const [endDate, setEndDate] = useState('2026-05-20');
  const [capital, setCapital] = useState(100000);
  const [isDelivery, setIsDelivery] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: config } = useQuery({
    queryKey: ['system-config'],
    queryFn: api.getConfig,
  });

  const watchlist = config?.watchlist || ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.runBacktest({
        strategy,
        symbol,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        initial_capital: Number(capital),
        is_delivery: isDelivery,
      });
      setResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'An error occurred during backtesting.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex bg-[#07070a] min-h-screen text-slate-100">
      <Sidebar />
      
      <main className="flex-1 p-8 space-y-6 overflow-y-auto max-h-screen">
        {/* Header */}
        <div className="flex justify-between items-center border-b border-slate-900 pb-4">
          <div>
            <h2 className="text-2xl font-black tracking-wider text-white">STRATEGY BACKTESTER</h2>
            <p className="text-xs text-slate-400 font-medium">Verify system intelligence against historical market data</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Config Panel */}
          <div className="glass-panel p-6 rounded-xl border border-slate-900 h-fit space-y-4">
            <h3 className="font-bold text-white text-sm uppercase tracking-wider border-b border-slate-900 pb-2">Configuration</h3>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Strategy Selector */}
              <div className="space-y-1.5">
                <label className="text-xs text-slate-400 font-semibold uppercase">Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="trend_strategy">Trend Crossover</option>
                  <option value="breakout_strategy">Price Breakout</option>
                  <option value="vwap_strategy">VWAP Reversion</option>
                  <option value="options_strategy">Volatility Options</option>
                  <option value="scalping_strategy">Fast Scalping</option>
                </select>
              </div>

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

              {/* Date pickers */}
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

              {/* Capital input */}
              <div className="space-y-1.5">
                <label className="text-xs text-slate-400 font-semibold uppercase">Capital (₹)</label>
                <input
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-900 text-sm text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              {/* Delivery check */}
              <div className="flex items-center gap-2 py-1">
                <input
                  type="checkbox"
                  id="delivery"
                  checked={isDelivery}
                  onChange={(e) => setIsDelivery(e.target.checked)}
                  className="w-4 h-4 accent-blue-600 rounded bg-slate-950 border-slate-900 focus:ring-0"
                />
                <label htmlFor="delivery" className="text-xs text-slate-300 font-medium">Delivery Mode</label>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white text-sm font-bold py-2 px-4 rounded-lg transition-colors cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Simulating...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Run Backtest
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-3 space-y-6">
            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-4 rounded-xl flex items-center gap-2 text-sm font-medium">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {!result && !loading && !error && (
              <div className="glass-panel p-12 rounded-xl border border-slate-900 text-center text-slate-500 font-medium space-y-2">
                <BarChart2 className="w-12 h-12 text-slate-700 mx-auto" />
                <p>Configure parameters and click &quot;Run Backtest&quot; to begin strategy simulation.</p>
              </div>
            )}

            {loading && (
              <div className="glass-panel p-20 rounded-xl border border-slate-900 flex flex-col items-center justify-center space-y-4">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <p className="text-sm text-slate-400 font-semibold tracking-wide">Synthesizing market variables and simulating fills...</p>
              </div>
            )}

            {result && (
              <div className="space-y-6">
                {/* Metrics Summary Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="glass-panel p-4 rounded-lg border border-slate-900">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Total Return</span>
                    <h4 className={`text-2xl font-black mt-1 ${result.metrics.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {result.metrics.total_return_pct.toFixed(2)}%
                    </h4>
                  </div>
                  <div className="glass-panel p-4 rounded-lg border border-slate-900">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Win Rate</span>
                    <h4 className="text-2xl font-black text-white mt-1">
                      {result.metrics.win_rate.toFixed(1)}%
                    </h4>
                  </div>
                  <div className="glass-panel p-4 rounded-lg border border-slate-900">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Max Drawdown</span>
                    <h4 className="text-2xl font-black text-rose-400 mt-1">
                      {result.metrics.max_drawdown_pct.toFixed(2)}%
                    </h4>
                  </div>
                  <div className="glass-panel p-4 rounded-lg border border-slate-900">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Sharpe Ratio</span>
                    <h4 className="text-2xl font-black text-blue-400 mt-1">
                      {result.metrics.sharpe_ratio.toFixed(2)}
                    </h4>
                  </div>
                </div>

                {/* Equity Curve Chart */}
                <div className="glass-panel p-6 rounded-xl border border-slate-900 space-y-4">
                  <h3 className="font-bold text-white text-sm uppercase tracking-wide">Equity Curve Growth</h3>
                  <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={result.equity_curve}>
                        <defs>
                          <linearGradient id="equityGlow" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#131321" />
                        <XAxis dataKey="time" hide />
                        <YAxis stroke="#475569" fontSize={10} domain={['auto', 'auto']} tickFormatter={(v) => `₹${v}`} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#07070a', borderColor: '#1e293b' }}
                          labelStyle={{ color: '#94a3b8' }}
                          itemStyle={{ color: '#3b82f6' }}
                          formatter={(value) => [`₹${Number(value).toFixed(2)}`, 'Equity']}
                        />
                        <Area type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#equityGlow)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Simulated Trades Table */}
                <div className="glass-panel p-6 rounded-xl border border-slate-900 space-y-4">
                  <h3 className="font-bold text-white text-sm uppercase tracking-wide">Execution Trade Log ({result.trades.length} trades)</h3>
                  <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="text-[10px] uppercase bg-slate-950/50 text-slate-500">
                        <tr>
                          <th className="px-4 py-2.5">Entry Time</th>
                          <th className="px-4 py-2.5">Exit Time</th>
                          <th className="px-4 py-2.5">Side</th>
                          <th className="px-4 py-2.5 text-right">Entry Price</th>
                          <th className="px-4 py-2.5 text-right">Exit Price</th>
                          <th className="px-4 py-2.5 text-right">Charges</th>
                          <th className="px-4 py-2.5 text-right">Net P&L</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-900/60">
                        {result.trades.map((t, i) => {
                          const isLong = t.direction === 'LONG';
                          const isWin = t.pnl >= 0;
                          return (
                            <tr key={i} className="hover:bg-slate-900/20 transition-colors">
                              <td className="px-4 py-2">{new Date(t.entry_time).toLocaleString()}</td>
                              <td className="px-4 py-2">{new Date(t.exit_time).toLocaleString()}</td>
                              <td className="px-4 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                  isLong ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                                }`}>
                                  {t.direction}
                                </span>
                              </td>
                              <td className="px-4 py-2 text-right">₹{t.entry_price.toFixed(2)}</td>
                              <td className="px-4 py-2 text-right">₹{t.exit_price.toFixed(2)}</td>
                              <td className="px-4 py-2 text-right text-rose-400/80">₹{t.charges.toFixed(2)}</td>
                              <td className={`px-4 py-2 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                                ₹{t.pnl.toFixed(2)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
