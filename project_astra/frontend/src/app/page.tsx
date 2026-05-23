export default function Home() {
  return (
    <main className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Project Astra</h1>
        <p className="text-xl text-gray-400">Agentic AI Trading Platform</p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Market Status</h2>
            <p className="text-green-400">Open</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Open Positions</h2>
            <p className="text-blue-400">0</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Today's PnL</h2>
            <p className="text-gray-400">₹0.00</p>
          </div>
        </div>
        
        <div className="mt-8 bg-gray-800 p-6 rounded-lg">
          <h2 className="text-2xl font-semibold mb-4">System Status</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Backend API</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between">
              <span>WebSocket</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between">
              <span>Paper Trading Mode</span>
              <span className="text-yellow-400">Active</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
