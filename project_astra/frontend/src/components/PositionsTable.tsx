'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import wsClient from '@/lib/websocket';
import { Position } from '@/lib/types';
import { Layers } from 'lucide-react';

export default function PositionsTable() {
  const { data, refetch } = useQuery({
    queryKey: ['positions'],
    queryFn: api.getPositions,
    refetchInterval: 5000,
  });

  const [positions, setPositions] = useState<Position[]>([]);

  useEffect(() => {
    if (data?.positions) {
      setPositions(data.positions);
    }
  }, [data]);

  useEffect(() => {
    // Subscribe to websocket position updates
    const handleWsPosition = (topic: string, updateData: any) => {
      if (topic === 'positions') {
        setPositions(prev => {
          const index = prev.findIndex(p => p.symbol === updateData.symbol);
          if (index !== -1) {
            const updated = [...prev];
            updated[index] = {
              ...updated[index],
              quantity: updateData.quantity,
              average_price: updateData.average_price,
              current_price: updateData.current_price,
              unrealized_pnl: updateData.unrealized_pnl
            };
            // Filter out closed positions
            return updated.filter(p => p.quantity > 0);
          } else if (updateData.quantity > 0) {
            return [...prev, updateData];
          }
          return prev;
        });
      }
    };

    wsClient.subscribe(['positions'], handleWsPosition);
    return () => wsClient.unsubscribe(['positions'], handleWsPosition);
  }, []);

  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
      <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
        <Layers className="w-5 h-5 text-blue-400" />
        <div>
          <h3 className="font-bold text-white tracking-wide">Open Positions</h3>
          <p className="text-xs text-slate-400">Currently active trades in the market</p>
        </div>
      </div>

      <div className="overflow-x-auto">
        {positions.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No active positions at the moment.
          </div>
        ) : (
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-950/40 text-slate-500">
              <tr>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Side</th>
                <th className="px-4 py-3 text-right">Quantity</th>
                <th className="px-4 py-3 text-right">Avg Price</th>
                <th className="px-4 py-3 text-right">Last Price</th>
                <th className="px-4 py-3 text-right">Unrealized P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900/60">
              {positions.map((pos) => {
                const isLong = pos.side === 'LONG';
                const pnl = pos.unrealized_pnl || 0;
                return (
                  <tr key={pos.id} className="hover:bg-slate-900/25 transition-colors">
                    <td className="px-4 py-3 font-semibold text-white">{pos.symbol}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isLong ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {pos.side}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{pos.quantity}</td>
                    <td className="px-4 py-3 text-right font-medium">₹{pos.average_price.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      ₹{pos.current_price ? pos.current_price.toFixed(2) : pos.average_price.toFixed(2)}
                    </td>
                    <td className={`px-4 py-3 text-right font-bold ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ₹{pnl.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
