'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, RefreshCw, BarChart2, Play, Settings, ShieldAlert, Signal 
} from 'lucide-react';
import wsClient from '@/lib/websocket';

export default function Sidebar() {
  const pathname = usePathname();
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    wsClient.addStatusListener(setWsStatus);
    return () => wsClient.removeStatusListener(setWsStatus);
  }, []);

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Backtest', path: '/backtest', icon: BarChart2 },
    { name: 'Replay Console', path: '/replay', icon: Play },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-900 flex flex-col justify-between min-h-screen sticky top-0">
      <div>
        {/* Logo Section */}
        <div className="p-6 border-b border-slate-900 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center glow-blue">
            <RefreshCw className="w-5 h-5 text-white animate-spin-slow" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-wider">PROJECT ASTRA</h1>
            <span className="text-[10px] text-slate-500 font-medium tracking-widest uppercase">AI Trading System</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path;
            return (
              <Link 
                key={item.path} 
                href={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive 
                    ? 'bg-blue-600/10 text-blue-400 border-l-2 border-blue-500' 
                    : 'text-slate-400 hover:bg-slate-900 hover:text-white'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Connection Status */}
      <div className="p-6 border-t border-slate-900 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">WebSocket Status</span>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${
              wsStatus === 'connected' 
                ? 'bg-emerald-500 animate-pulse glow-green' 
                : wsStatus === 'connecting'
                ? 'bg-amber-500 animate-pulse'
                : 'bg-rose-500'
            }`} />
            <span className={`font-medium ${
              wsStatus === 'connected' 
                ? 'text-emerald-400' 
                : wsStatus === 'connecting'
                ? 'text-amber-400'
                : 'text-rose-400'
            }`}>
              {wsStatus === 'connected' ? 'Connected' : wsStatus === 'connecting' ? 'Connecting' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
