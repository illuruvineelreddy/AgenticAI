'use client';

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  color: 'blue' | 'green' | 'red' | 'amber';
  subtitle?: string;
}

export default function StatCard({ title, value, icon: Icon, color, subtitle }: StatCardProps) {
  const colorMap = {
    blue: {
      border: 'border-l-4 border-l-blue-500',
      iconBg: 'bg-blue-600/10 text-blue-400',
      glow: 'glow-blue'
    },
    green: {
      border: 'border-l-4 border-l-emerald-500',
      iconBg: 'bg-emerald-600/10 text-emerald-400',
      glow: 'glow-green'
    },
    red: {
      border: 'border-l-4 border-l-rose-500',
      iconBg: 'bg-rose-600/10 text-rose-400',
      glow: 'glow-red'
    },
    amber: {
      border: 'border-l-4 border-l-amber-500',
      iconBg: 'bg-amber-600/10 text-amber-400',
      glow: 'glow-amber'
    }
  };

  const selectedColor = colorMap[color];

  return (
    <div className={`glass-panel glass-panel-hover p-6 rounded-xl relative overflow-hidden transition-all duration-300 ${selectedColor.border}`}>
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">{title}</span>
          <h2 className="text-3xl font-extrabold text-white mt-1 tracking-tight">{value}</h2>
          {subtitle && <p className="text-[10px] text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${selectedColor.iconBg}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
