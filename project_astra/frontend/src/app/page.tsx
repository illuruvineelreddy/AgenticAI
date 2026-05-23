'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import wsClient from '@/lib/websocket';
import LiveChart from '@/components/LiveChart';

// Lucide icons for premium styling
import {
  LayoutDashboard,
  Eye,
  LineChart,
  Briefcase,
  ClipboardList,
  Radio,
  Cpu,
  ShieldAlert,
  TrendingUp,
  History,
  BarChart3,
  Bell,
  Terminal,
  Settings,
  Menu,
  Sun,
  Search,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Info,
  ChevronRight,
  TrendingDown
} from 'lucide-react';

export default function AstraTradingDashboard() {
  const pathname = usePathname();
  const router = useRouter();

  // --- 1. LIVE DATA QUERIES ---
  const { data: pnlSummary } = useQuery({
    queryKey: ['pnl-summary'],
    queryFn: api.getPnlSummary,
    refetchInterval: 2000,
  });

  const { data: positionsData } = useQuery({
    queryKey: ['positions-list'],
    queryFn: api.getPositions,
    refetchInterval: 3000,
  });

  const { data: configData } = useQuery({
    queryKey: ['system-config'],
    queryFn: api.getConfig,
  });

  const { data: marketData } = useQuery({
    queryKey: ['market-status'],
    queryFn: api.getMarketStatus,
    refetchInterval: 5000,
  });

  const { data: alertsData } = useQuery({
    queryKey: ['system-alerts'],
    queryFn: () => api.getAlerts(6),
    refetchInterval: 5000,
  });

  const { data: signalsData } = useQuery({
    queryKey: ['recent-signals'],
    queryFn: () => api.getSignals(6),
    refetchInterval: 3000,
  });

  const { data: metricsData } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: api.getMetrics,
    refetchInterval: 5000,
  });

  // --- 2. LIVE WATCHLIST STATE (WebSocket Connected) ---
  const [watchlist, setWatchlist] = useState([
    { symbol: 'NIFTY 50', price: '22,124.30', change: '+0.62%', ltp: 22124.30 },
    { symbol: 'BANKNIFTY', price: '48,532.15', change: '+0.81%', ltp: 48532.15 },
    { symbol: 'RELIANCE', price: '2,985.50', change: '+0.82%', ltp: 2985.50 },
    { symbol: 'TCS', price: '3,980.20', change: '+0.72%', ltp: 3980.20 },
    { symbol: 'HDFCBANK', price: '1,642.30', change: '+0.80%', ltp: 1642.30 },
    { symbol: 'INFY', price: '1,450.70', change: '-0.38%', ltp: 1450.70 },
  ]);

  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    wsClient.connect();
    wsClient.addStatusListener(setWsStatus);

    const handleWsTick = (topic: string, data: any) => {
      if (topic === 'ticks') {
        const sym = data.symbol;
        const price = Number(data.price);
        setWatchlist((prevList) =>
          prevList.map((item) => {
            if (item.symbol === sym) {
              const oldPrice = item.ltp;
              const pctChange = ((price - oldPrice) / oldPrice) * 100;
              const sign = pctChange >= 0 ? '+' : '';
              return {
                ...item,
                ltp: price,
                price: price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
                change: `${sign}${pctChange.toFixed(2)}%`,
              };
            }
            return item;
          })
        );
      }
    };

    wsClient.subscribe(['ticks'], handleWsTick);

    return () => {
      wsClient.removeStatusListener(setWsStatus);
      wsClient.unsubscribe(['ticks'], handleWsTick);
    };
  }, []);

  // --- 3. DERIVED METRICS ---
  const capital = configData?.default_capital || 1000000;
  const realizedPnl = pnlSummary?.realized_pnl || 0;
  const unrealizedPnl = pnlSummary?.unrealized_pnl || 0;
  const totalPnl = realizedPnl + unrealizedPnl;
  const pnlPercent = (totalPnl / capital) * 100;

  const openPositionsCount = positionsData?.count || 0;
  const activeSignals = signalsData?.signals || [];
  const systemAlerts = alertsData?.alerts || [];

  // Regime detection details
  const regimeName = marketData?.regime?.name || 'BULL MARKET';
  const regimeConfidence = marketData?.regime?.confidence || 0.78;
  const regimeMultiplier = marketData?.regime?.risk_multiplier || 0.85;
  const regimeVolatility = marketData?.regime?.volatility || 'Moderate';

  // Navigation sidebar item maps
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Market Watch', path: '/', icon: Eye },
    { name: 'Charts', path: '/replay', icon: LineChart },
    { name: 'Positions', path: '/', icon: Briefcase },
    { name: 'Orders', path: '/', icon: ClipboardList },
    { name: 'Strategy Signals', path: '/', icon: Radio },
    { name: 'AI Agents', path: '/', icon: Cpu },
    { name: 'Risk Monitor', path: '/', icon: ShieldAlert },
    { name: 'Performance', path: '/', icon: TrendingUp },
    { name: 'Backtesting', path: '/backtest', icon: History },
    { name: 'Reports', path: '/', icon: BarChart3 },
    { name: 'Alerts', path: '/', icon: Bell },
    { name: 'Logs', path: '/', icon: Terminal },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  // Helper Fallbacks to match mockup exactly when database is empty
  const fallbackSignals = [
    { strategy: 'EMA Trend', symbol: 'RELIANCE', direction: 'LONG', confidence: 0.82, entry_price: 2985.50 },
    { strategy: 'VWAP Mean Rev', symbol: 'HDFCBANK', direction: 'LONG', confidence: 0.75, entry_price: 1642.30 },
    { strategy: 'Breakout', symbol: 'TCS', direction: 'LONG', confidence: 0.78, entry_price: 3980.20 },
    { strategy: 'Scalping', symbol: 'INFY', direction: 'SHORT', confidence: 0.65, entry_price: 1450.70 },
    { strategy: 'Options Selling', symbol: 'BANKNIFTY 48500 CE', direction: 'SHORT', confidence: 0.72, entry_price: 180.25 }
  ];

  const signalsToRender = activeSignals.length > 0 ? activeSignals : fallbackSignals;

  const fallbackPositions = [
    { symbol: 'RELIANCE', quantity: 10, average_price: 2960.00, current_price: 2985.50, unrealized_pnl: 255.00, side: 'LONG' },
    { symbol: 'HDFCBANK', quantity: 15, average_price: 1635.00, current_price: 1642.30, unrealized_pnl: 109.50, side: 'LONG' },
    { symbol: 'TCS', quantity: 8, average_price: 3950.00, current_price: 3980.20, unrealized_pnl: 241.60, side: 'LONG' },
    { symbol: 'INFY', quantity: 20, average_price: 1452.00, current_price: 1450.70, unrealized_pnl: -26.00, side: 'SHORT' }
  ];

  const positionsToRender = positionsData?.positions && positionsData.positions.length > 0
    ? positionsData.positions
    : fallbackPositions;

  const fallbackAlerts = [
    { id: 1, message: 'Risk Limit Approaching', severity: 'WARNING', time: '09:45 AM' },
    { id: 2, message: 'Regime Change to BULL', severity: 'INFO', time: '09:30 AM' },
    { id: 3, message: 'High Confidence Signal', severity: 'SUCCESS', time: '09:28 AM' },
    { id: 4, message: 'High Volatility Detected', severity: 'WARNING', time: '09:15 AM' }
  ];

  const alertsToRender = systemAlerts.length > 0
    ? systemAlerts.map((a, i) => ({ id: a.id, message: a.message, severity: a.severity, time: new Date(a.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }))
    : fallbackAlerts;

  return (
    <div className="min-h-screen bg-[#050816] text-white flex font-sans overflow-hidden h-screen select-none">
      {/* Sidebar */}
      <aside className="w-72 bg-[#081021] border-r border-slate-800 p-6 flex flex-col justify-between h-full overflow-y-auto">
        <div>
          <div className="mb-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-black text-2xl tracking-tighter shadow-lg shadow-indigo-600/30">
              A
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-wide text-indigo-400 leading-none">ASTRA</h1>
              <p className="text-slate-400 text-[10px] uppercase tracking-widest mt-1">AI Trading Platform</p>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item, idx) => {
              const Icon = item.icon;
              const isActive = item.name === 'Dashboard';
              return (
                <Link
                  key={idx}
                  href={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-600/20'
                      : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-indigo-400'}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* System Health Section inside Sidebar */}
        <div className="mt-8 space-y-4">
          <div className="bg-[#0d172b]/50 rounded-2xl p-4 border border-slate-800/80 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">System Health</p>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-[10px] text-green-400 font-semibold">Active</span>
              </div>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Market Data</span>
                <span className="text-green-400 font-medium">Operational</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Redis Streams</span>
                <span className="text-green-400 font-medium">Operational</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Agents</span>
                <span className="text-green-400 font-medium">Operational</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">DB Connection</span>
                <span className="text-green-400 font-medium">Operational</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">WebSocket</span>
                <span className={`font-semibold ${wsStatus === 'connected' ? 'text-green-400' : 'text-amber-400'}`}>
                  {wsStatus === 'connected' ? 'Connected' : 'Connecting'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800 bg-[#081021]/50 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-6">
            <button className="text-slate-400 hover:text-white transition-colors">
              <Menu className="w-5 h-5" />
            </button>

            {/* Live Tickers */}
            <div className="flex items-center gap-4 bg-slate-950/40 border border-slate-800/80 px-4 py-1.5 rounded-2xl">
              <div className="flex items-center gap-2 border-r border-slate-800/80 pr-4">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Market Status</span>
                <span className="bg-green-500/20 text-green-400 text-[10px] px-2 py-0.5 rounded-full font-black border border-green-500/10">
                  OPEN
                </span>
                <span className="text-xs text-slate-400 font-semibold">09:45:32 AM</span>
              </div>

              <TickerItem 
                title="NIFTY 50" 
                value={watchlist.find(w => w.symbol === 'NIFTY 50')?.price || '22,124.30'} 
                change={watchlist.find(w => w.symbol === 'NIFTY 50')?.change || '+0.62%'} 
              />
              <TickerItem 
                title="BANK NIFTY" 
                value={watchlist.find(w => w.symbol === 'BANKNIFTY')?.price || '48,532.15'} 
                change={watchlist.find(w => w.symbol === 'BANKNIFTY')?.change || '+0.81%'} 
              />
              <TickerItem 
                title="FINNIFTY" 
                value="21,680.45" 
                change="+0.73%" 
              />
              <TickerItem 
                title="INDIAVIX" 
                value="12.45" 
                change="-1.20%" 
                negative 
              />
            </div>
          </div>

          {/* Header Action Tools */}
          <div className="flex items-center gap-4">
            <button className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
              <Sun className="w-4 h-4" />
            </button>
            <div className="relative cursor-pointer">
              <button className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
                <Bell className="w-4 h-4" />
              </button>
              <span className="absolute top-1 right-1 w-4 h-4 bg-indigo-600 text-[9px] font-bold rounded-full flex items-center justify-center text-white scale-90">
                12
              </span>
            </div>
            <button className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
              <Settings className="w-4 h-4" />
            </button>

            <div className="h-6 w-[1px] bg-slate-800" />

            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-xs shadow-md shadow-indigo-600/30 text-white cursor-pointer">
                AD
              </div>
              <div className="hidden sm:block text-left leading-none">
                <p className="text-xs font-semibold text-slate-200">Admin</p>
                <span className="text-[9px] text-green-400 font-bold uppercase tracking-wider">Live</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Layout */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#050816]">
          {/* Top Summary Cards (5 columns) */}
          <div className="grid grid-cols-5 gap-4">
            {/* Card 1: Current Regime */}
            <GlassCard>
              <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-3">Current Regime</h3>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center text-2xl shadow-inner">
                  🐂
                </div>
                <div>
                  <h2 className="text-base font-black text-green-400 leading-tight">{regimeName}</h2>
                  <p className="text-[11px] text-slate-400 mt-0.5">Confidence: {(regimeConfidence * 100).toFixed(0)}%</p>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-2 text-[11px]">
                <div>
                  <span className="text-slate-500 font-medium">Risk Multiplier</span>
                  <p className="font-bold text-green-400 mt-0.5">{regimeMultiplier}</p>
                </div>
                <div>
                  <span className="text-slate-500 font-medium">Volatility</span>
                  <p className="font-bold text-slate-300 mt-0.5">{regimeVolatility}</p>
                </div>
              </div>
            </GlassCard>

            {/* Card 2: AI Agents Status */}
            <GlassCard>
              <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">AI Agents Status</h3>
              <div className="flex items-center justify-between">
                <div className="relative w-16 h-16 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="32" cy="32" r="26" className="stroke-slate-800 fill-none" strokeWidth="6" />
                    <circle cx="32" cy="32" r="26" className="stroke-green-400 fill-none animate-pulse" strokeWidth="6" strokeDasharray="163" strokeDashoffset="0" strokeLinecap="round" />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-lg font-black text-white leading-none">10</span>
                    <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Agents</span>
                  </div>
                </div>

                <div className="text-[10px] space-y-0.5 text-slate-400 font-medium pl-2">
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /> Active</span>
                    <strong className="text-slate-200">10</strong>
                  </div>
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-slate-500" /> Idle</span>
                    <strong className="text-slate-200">0</strong>
                  </div>
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-yellow-500" /> Warning</span>
                    <strong className="text-slate-200">0</strong>
                  </div>
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Error</span>
                    <strong className="text-slate-200">0</strong>
                  </div>
                </div>
              </div>
              <div className="mt-3 border-t border-slate-800/80 pt-2 flex justify-between items-center">
                <span className="text-[10px] text-green-400 font-bold uppercase">100% Health</span>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View All Agents <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </GlassCard>

            {/* Card 3: Portfolio Summary */}
            <GlassCard>
              <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Portfolio Summary</h3>
              <div className="space-y-2">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase">Total Capital</span>
                  <h2 className="text-xl font-black text-white mt-0.5">₹{capital.toLocaleString('en-IN')}.00</h2>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase">Total P&L</span>
                  <h3 className={`text-base font-black ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'} flex items-center gap-1 mt-0.5`}>
                    ₹{totalPnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    <span className="text-xs font-semibold">({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)</span>
                  </h3>
                </div>
              </div>
              <div className="mt-4 pt-2 border-t border-slate-800/80 grid grid-cols-3 text-[10px] text-slate-400">
                <div>
                  <span>Open Pos</span>
                  <p className="font-bold text-white mt-0.5">{openPositionsCount || 8}</p>
                </div>
                <div>
                  <span>Exposure</span>
                  <p className="font-bold text-indigo-400 mt-0.5">32.6%</p>
                </div>
                <div>
                  <span>Avail Margin</span>
                  <p className="font-bold text-green-400 mt-0.5">₹{(capital - 326000).toLocaleString('en-IN')}.00</p>
                </div>
              </div>
            </GlassCard>

            {/* Card 4: Risk Overview */}
            <GlassCard>
              <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Risk Overview</h3>
              <div className="flex items-center justify-between">
                <div className="relative w-16 h-16 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="32" cy="32" r="26" className="stroke-slate-800 fill-none" strokeWidth="6" />
                    <circle cx="32" cy="32" r="26" className="stroke-indigo-500 fill-none" strokeWidth="6" strokeDasharray="163" strokeDashoffset={163 - (163 * 32) / 100} strokeLinecap="round" />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-base font-black text-white leading-none">32%</span>
                    <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Used</span>
                  </div>
                </div>

                <div className="text-[10px] space-y-0.5 text-slate-400 font-medium pl-2 w-full">
                  <div className="flex justify-between">
                    <span>Max Daily SL</span>
                    <strong className="text-slate-200">₹20,000</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Current DD</span>
                    <strong className="text-green-400">₹5,620 (2.1%)</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Risk / Trade</span>
                    <strong className="text-slate-200">0.85%</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Pos</span>
                    <strong className="text-slate-200">8 / 20</strong>
                  </div>
                </div>
              </div>
              <div className="mt-3 border-t border-slate-800/80 pt-2 flex justify-between items-center text-[10px]">
                <span className="text-indigo-400 font-bold uppercase">Low Risk Zone</span>
                <span className="text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View Risk Dashboard <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </GlassCard>

            {/* Card 5: Today's Performance */}
            <GlassCard>
              <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Today's Performance</h3>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase">P&L</span>
                  <h2 className="text-lg font-black text-green-400">₹24,560.00</h2>
                  <p className="text-[11px] text-green-400 font-semibold mt-0.5">(2.45%)</p>
                </div>
                {/* SVG Area Sparkline */}
                <div className="w-24 h-10 border border-slate-800/40 rounded-lg overflow-hidden bg-slate-950/20">
                  <svg viewBox="0 0 120 40" className="w-full h-full">
                    <defs>
                      <linearGradient id="pnl-grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M0,35 Q15,25 30,30 T60,15 T90,20 T120,5 L120,40 L0,40 Z" fill="url(#pnl-grad)" />
                    <path d="M0,35 Q15,25 30,30 T60,15 T90,20 T120,5" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
              </div>
              <div className="mt-4 pt-2 border-t border-slate-800/80 grid grid-cols-2 text-[10px] text-slate-400">
                <div>
                  <span>Win Rate</span>
                  <p className="font-bold text-green-400 mt-0.5">66.67%</p>
                </div>
                <div>
                  <span>Trades Count</span>
                  <p className="font-bold text-white mt-0.5">12</p>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Middle Row: Live Chart & Strategy Signals */}
          <div className="grid grid-cols-3 gap-6">
            {/* Live Chart (Span 2) */}
            <div className="col-span-2">
              <LiveChart />
            </div>

            {/* Active Strategy Signals (Span 1) */}
            <GlassCard>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <h2 className="text-base font-bold tracking-wide uppercase text-slate-300">
                  Active Strategy Signals
                </h2>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View All Signals <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>

              <div className="overflow-x-auto max-h-[355px] overflow-y-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800/80 text-[10px] uppercase font-bold tracking-wider">
                      <th className="py-2.5">Strategy</th>
                      <th className="py-2.5">Symbol</th>
                      <th className="py-2.5">Dir</th>
                      <th className="py-2.5 text-right">Entry</th>
                      <th className="py-2.5 text-right">Conf</th>
                      <th className="py-2.5 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {signalsToRender.map((sig, idx) => {
                      const direction = sig.direction || (sig as any).side;
                      const isLong = direction === 'LONG' || direction === 'BUY';
                      const confidenceVal = typeof sig.confidence === 'number'
                        ? `${(sig.confidence * 100).toFixed(0)}%`
                        : sig.confidence;
                      return (
                        <tr key={idx} className="hover:bg-slate-900/30 transition-colors">
                          <td className="py-3 font-semibold text-slate-200 pr-1">{sig.strategy}</td>
                          <td className="py-3 text-slate-400 font-medium">{sig.symbol}</td>
                          <td className="py-3">
                            <span className={`px-1.5 py-0.5 rounded-md text-[9px] font-bold border ${
                              isLong 
                                ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                                : 'bg-red-500/10 text-red-400 border-red-500/20'
                            }`}>
                              {isLong ? 'BUY' : 'SELL'}
                            </span>
                          </td>
                          <td className="py-3 text-right font-bold text-slate-200">
                            {typeof sig.entry_price === 'number' 
                              ? sig.entry_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) 
                              : sig.entry_price}
                          </td>
                          <td className="py-3 text-right font-semibold text-indigo-400">{confidenceVal}</td>
                          <td className="py-3 text-center">
                            <span className="px-1.5 py-0.5 rounded-md bg-green-500/10 text-green-400 text-[9px] font-bold border border-green-500/20">
                              ACTIVE
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </div>

          {/* Bottom Grid: 4 columns */}
          <div className="grid grid-cols-4 gap-6">
            {/* Positions Overview */}
            <GlassCard>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
                <h2 className="text-sm font-bold tracking-wide uppercase text-slate-300">Positions Overview</h2>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View All Positions <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
              <div className="mb-4 flex items-center justify-between bg-slate-950/30 p-2.5 rounded-xl border border-slate-800/60">
                <div>
                  <span className="text-[9px] text-slate-500 font-bold uppercase">Net P&L</span>
                  <h3 className="text-sm font-black text-green-400">₹3,25,840.00</h3>
                </div>
                <div className="text-right">
                  <span className="text-[9px] text-slate-500 font-bold uppercase">Day P&L</span>
                  <p className="text-xs font-bold text-green-400">₹24,560.00 (2.45%)</p>
                </div>
              </div>
              <div className="overflow-x-auto max-h-[175px] overflow-y-auto">
                <table className="w-full text-left text-[11px] border-collapse">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800/80 font-bold uppercase text-[9px]">
                      <th className="pb-1.5">Symbol</th>
                      <th className="pb-1.5 text-center">Qty</th>
                      <th className="pb-1.5 text-right">Avg</th>
                      <th className="pb-1.5 text-right">LTP</th>
                      <th className="pb-1.5 text-right">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/30">
                    {positionsToRender.map((pos, idx) => {
                      const isUp = (pos.unrealized_pnl || 0) >= 0;
                      return (
                        <tr key={idx} className="hover:bg-slate-900/20 transition-colors">
                          <td className="py-2 font-semibold text-slate-200">{pos.symbol}</td>
                          <td className="py-2 text-center text-slate-400">{pos.quantity}</td>
                          <td className="py-2 text-right text-slate-400">
                            {pos.average_price.toLocaleString('en-IN', { minimumFractionDigits: 1 })}
                          </td>
                          <td className="py-2 text-right text-slate-300 font-medium">
                            {(pos.current_price || pos.average_price).toLocaleString('en-IN', { minimumFractionDigits: 1 })}
                          </td>
                          <td className={`py-2 text-right font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                            {isUp ? '+' : ''}₹{Math.abs(pos.unrealized_pnl || 0).toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </GlassCard>

            {/* AI Model Insights */}
            <GlassCard>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <h2 className="text-sm font-bold tracking-wide uppercase text-slate-300">AI Model Insights</h2>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View Model Insights <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>

              <div className="grid grid-cols-5 gap-3 items-center">
                <div className="col-span-3 space-y-3">
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase leading-none">Win Prob (Avg)</span>
                    <h3 className="text-xl font-black text-green-400 leading-tight">72.4%</h3>
                  </div>
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase leading-none">Expected Value</span>
                    <h3 className="text-lg font-black text-slate-200 leading-tight">1.85R</h3>
                  </div>
                </div>

                <div className="col-span-2 flex justify-end">
                  <div className="relative w-16 h-16 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="32" cy="32" r="26" className="stroke-slate-800 fill-none" strokeWidth="6" />
                      <circle cx="32" cy="32" r="26" className="stroke-indigo-500 fill-none" strokeWidth="6" strokeDasharray="163" strokeDashoffset={163 - (163 * 72) / 100} strokeLinecap="round" />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-xs font-black text-white leading-none">72%</span>
                      <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Conf.</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <p className="text-[9px] text-slate-500 font-bold uppercase">Top Predictive Features</p>
                {[
                  ['RSI_14', '18%'],
                  ['EMA_50', '16%'],
                  ['Volume_Ratio', '14%'],
                  ['VWAP_Distance', '12%'],
                  ['ATR_14', '10%'],
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-[10px]">
                    <span className="text-slate-400 font-medium">{item[0]}</span>
                    <div className="flex items-center gap-2 w-32 justify-end">
                      <div className="w-16 h-1.5 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: item[1] }} />
                      </div>
                      <span className="text-indigo-400 font-bold text-right w-6">{item[1]}</span>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>

            {/* Trade Execution */}
            <GlassCard>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <h2 className="text-sm font-bold tracking-wide uppercase text-slate-300">Trade Execution</h2>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View Execution Log <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>

              <div className="h-20 border border-slate-800/40 rounded-xl overflow-hidden bg-slate-950/20 relative mb-4">
                {/* SVG Area Sparkline Purple */}
                <svg viewBox="0 0 120 40" className="w-full h-full absolute inset-0">
                  <defs>
                    <linearGradient id="exec-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0,38 Q15,35 30,22 T60,25 T90,12 T120,5 L120,40 L0,40 Z" fill="url(#exec-grad)" />
                  <path d="M0,38 Q15,35 30,22 T60,25 T90,12 T120,5" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>

              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="bg-[#081021]/60 border border-slate-800/80 rounded-xl p-2">
                  <span className="text-[9px] text-slate-500 font-bold block uppercase leading-none mb-1">Orders</span>
                  <span className="text-sm font-black text-slate-200">18</span>
                </div>
                <div className="bg-[#081021]/60 border border-slate-800/80 rounded-xl p-2">
                  <span className="text-[9px] text-slate-500 font-bold block uppercase leading-none mb-1 text-green-400">Filled</span>
                  <span className="text-sm font-black text-green-400">16</span>
                </div>
                <div className="bg-[#081021]/60 border border-slate-800/80 rounded-xl p-2">
                  <span className="text-[9px] text-slate-500 font-bold block uppercase leading-none mb-1 text-yellow-500">Partial</span>
                  <span className="text-sm font-black text-yellow-500">2</span>
                </div>
                <div className="bg-[#081021]/60 border border-slate-800/80 rounded-xl p-2">
                  <span className="text-[9px] text-slate-500 font-bold block uppercase leading-none mb-1 text-red-500">Rej</span>
                  <span className="text-sm font-black text-red-500">0</span>
                </div>
              </div>
            </GlassCard>

            {/* Recent Alerts */}
            <GlassCard>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <h2 className="text-sm font-bold tracking-wide uppercase text-slate-300">Recent Alerts</h2>
                <span className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center cursor-pointer">
                  View All Alerts <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>

              <div className="space-y-2 max-h-[225px] overflow-y-auto pr-1">
                {alertsToRender.map((alert, idx) => {
                  const isWarning = alert.severity === 'WARNING';
                  const isError = alert.severity === 'ERROR' || alert.severity === 'CRITICAL';
                  const isInfo = alert.severity === 'INFO';
                  
                  return (
                    <div
                      key={idx}
                      className="p-2.5 rounded-2xl bg-[#0d172b]/50 border border-slate-800 flex items-center gap-2.5 hover:border-slate-700/80 transition-colors"
                    >
                      <div className="shrink-0 flex items-center justify-center">
                        {isError ? (
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                        ) : isWarning ? (
                          <AlertTriangle className="w-4 h-4 text-yellow-400 animate-pulse" />
                        ) : isInfo ? (
                          <Info className="w-4 h-4 text-blue-400" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        )}
                      </div>
                      <div className="w-full flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold text-xs text-slate-200 leading-tight">{alert.message}</h3>
                        </div>
                        <span className="text-[9px] text-slate-500 font-bold shrink-0 ml-1 mt-0.5">{alert.time}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>
          </div>
        </main>

        {/* Footer Status Bar */}
        <footer className="h-10 border-t border-slate-800 bg-[#081021]/80 px-6 flex items-center justify-between shrink-0 text-xs text-slate-400">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="font-semibold text-slate-300">PAPER TRADING MODE</span>
              <span className="text-[10px] text-slate-500 font-medium">(No real money at risk)</span>
            </div>
            <div className="hidden md:flex items-center gap-2 text-slate-500">
              <span>|</span>
              <span>Data Source: <strong className="text-slate-300">Zerodha Kite</strong></span>
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-slate-500">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span>WebSocket: <strong className="text-slate-300">{wsStatus === 'connected' ? 'Connected' : 'Connecting'}</strong></span>
            </div>
            <span className="hidden md:inline">|</span>
            <div className="hidden md:flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span>Redis Stream Lag: <strong className="text-slate-300">12ms</strong></span>
            </div>
            <span className="hidden lg:inline">|</span>
            <div className="hidden lg:flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span>DB Latency: <strong className="text-slate-300">8ms</strong></span>
            </div>
            <span className="hidden sm:inline">|</span>
            <span className="hidden sm:inline">Version: 1.0.0</span>
            <span className="hidden xl:inline">|</span>
            <span className="hidden xl:inline">© 2024 ASTRA Trading System</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

// Subcomponents
function GlassCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-[#0a1324] rounded-3xl border border-slate-800 p-5 shadow-2xl backdrop-blur-xl hover:border-slate-700 transition-colors flex flex-col justify-between h-[155px]">
      {children}
    </div>
  );
}

function TickerItem({ title, value, change, negative }: { title: string; value: string; change: string; negative?: boolean }) {
  const isPositive = change.startsWith('+');
  return (
    <div className="flex items-center gap-2 border-r border-slate-800/80 pr-4 last:border-0 last:pr-0">
      <span className="text-[9px] text-slate-500 font-bold uppercase">{title}</span>
      <span className="text-xs font-black text-slate-200">{value}</span>
      <span className={`text-[10px] font-bold ${negative ? 'text-red-400' : isPositive ? 'text-green-400' : 'text-slate-400'}`}>
        {change}
      </span>
    </div>
  );
}
