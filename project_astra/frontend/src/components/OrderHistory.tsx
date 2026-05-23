'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import wsClient from '@/lib/websocket';
import { Order } from '@/lib/types';
import { ListTodo } from 'lucide-react';

export default function OrderHistory() {
  const { data } = useQuery({
    queryKey: ['orders'],
    queryFn: () => api.getOrders(),
    refetchInterval: 5000,
  });

  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    if (data?.orders) {
      setOrders(data.orders);
    }
  }, [data]);

  useEffect(() => {
    // Subscribe to websocket order updates
    const handleWsOrder = (topic: string, updateData: any) => {
      if (topic === 'orders') {
        setOrders(prev => {
          const index = prev.findIndex(o => o.order_id === updateData.order_id);
          if (index !== -1) {
            const updated = [...prev];
            updated[index] = {
              ...updated[index],
              status: updateData.status,
              filled_quantity: updateData.filled_quantity,
              price: updateData.price
            };
            return updated;
          } else {
            return [updateData, ...prev].slice(0, 50);
          }
        });
      }
    };

    wsClient.subscribe(['orders'], handleWsOrder);
    return () => wsClient.unsubscribe(['orders'], handleWsOrder);
  }, []);

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'FILLED':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'PARTIAL':
        return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
      case 'REJECTED':
      case 'CANCELLED':
        return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
      default:
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-900 shadow-xl space-y-4">
      <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
        <ListTodo className="w-5 h-5 text-blue-400" />
        <div>
          <h3 className="font-bold text-white tracking-wide">Order Execution Log</h3>
          <p className="text-xs text-slate-400">Chronological history of broker orders</p>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
        {orders.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No orders logged yet.
          </div>
        ) : (
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-950/40 text-slate-500">
              <tr>
                <th className="px-4 py-3">Order ID</th>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Side</th>
                <th className="px-4 py-3 text-right">Qty</th>
                <th className="px-4 py-3 text-right">Price</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900/60">
              {orders.map((ord) => {
                const isBuy = ord.side === 'BUY';
                return (
                  <tr key={ord.id || ord.order_id} className="hover:bg-slate-900/25 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{ord.order_id}</td>
                    <td className="px-4 py-3 font-semibold text-white">{ord.symbol}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isBuy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                      }`}>
                        {ord.side}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{ord.quantity}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      {ord.price ? `₹${ord.price.toFixed(2)}` : 'MARKET'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${getStatusStyle(ord.status)}`}>
                        {ord.status}
                      </span>
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
