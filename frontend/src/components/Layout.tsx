import React from 'react';

interface LayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ sidebar, children }) => {
  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Sidebar */}
      <aside className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center space-x-3">
            <img 
              src="/images/Logo1.png" 
              alt="Buy The Dip Bot Logo" 
              className="w-12 h-12 flex-shrink-0"
            />
            <div>
              <h1 className="text-xl font-bold text-white">Buy The Dip Bot</h1>
              <p className="text-sm text-slate-400 mt-1">Market Analysis Dashboard</p>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {sidebar}
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-8 bg-slate-900">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout; 