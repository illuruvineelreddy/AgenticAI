'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import wsClient from '@/lib/websocket';
import { Alert } from '@/lib/types';
import { Bell, X } from 'lucide-react';

export default function AlertPanel() {
  const { data, refetch } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(10),
    refetchInterval: 10000,
  });

  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    if (data?.alerts) {
      setAlerts(data.alerts.filter(a => !a.is_read));
    }
  }, [data]);

  useEffect(() => {
    // Subscribe to WS alerts
    const handleWsAlert = (topic: string, updateData: any) => {
      if (topic === 'alerts') {
        setAlerts(prev => [updateData, ...prev].slice(0, 10));
      }
    };

    wsClient.subscribe(['alerts'], handleWsAlert);
    return () => wsClient.unsubscribe(['alerts'], handleWsAlert);
  }, []);

  const handleDismiss = async (id: number) => {
    try {
      await api.markAlertRead(id);
      setAlerts(prev => prev.filter(a => a.id !== id));
      refetch();
    } catch (e) {
      console.error("Failed to dismiss alert", e);
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'ERROR':
        return 'bg-rose-500/10 border-rose-500/20 text-rose-400';
      case 'WARNING':
        return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
      default:
        return 'bg-blue-500/10 border-blue-500/20 text-blue-400';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
      <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
        <Bell className="w-5 h-5 text-blue-400 animate-swing" />
        <div>
          <h3 className="font-bold text-white tracking-wide">System Notifications</h3>
          <p className="text-xs text-slate-400">Critical operational alerts and events</p>
        </div>
      </div>

      <div className="space-y-2 max-h-[250px] overflow-y-auto pr-1">
        {alerts.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-sm">
            No active system alerts. All systems nominal.
          </div>
        ) : (
          alerts.map((alert) => (
            <div 
              key={alert.id} 
              className={`p-3 rounded-lg border flex items-start justify-between gap-3 text-xs ${getSeverityStyle(alert.severity)}`}
            >
              <div>
                <span className="font-bold tracking-wide uppercase block text-[10px] opacity-80">{alert.title}</span>
                <p className="mt-0.5 leading-relaxed font-medium">{alert.message}</p>
                {alert.source && <span className="text-[9px] text-slate-500 mt-1 block">Source: {alert.source}</span>}
              </div>
              <button 
                onClick={() => handleDismiss(alert.id)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
