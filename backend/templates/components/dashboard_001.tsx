import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
// Icons typically imported from lucide-react, mocked here as emojis for template simplicity
const Icons = { Menu: '☰', Home: '🏠', Users: '👥', Settings: '⚙️', Chart: '📊', Bell: '🔔', User: '👤' };

export const SidebarDashboard = ({
  companyName = "Admin Pro",
  children
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { name: "Overview", icon: Icons.Home, active: true },
    { name: "Analytics", icon: Icons.Chart, active: false },
    { name: "Customers", icon: Icons.Users, active: false },
    { name: "Settings", icon: Icons.Settings, active: false }
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex overflow-hidden">
      {/* Sidebar */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="flex-shrink-0 border-r border-border bg-card flex flex-col h-screen whitespace-nowrap overflow-hidden z-20"
          >
            <div className="h-16 flex items-center px-6 border-b border-border">
              <span className="text-xl font-bold tracking-tight">{companyName}</span>
            </div>
            
            <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
              {navItems.map((item, idx) => (
                <button 
                  key={idx}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left ${
                    item.active 
                      ? "bg-primary text-primary-foreground font-medium shadow-sm" 
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.name}</span>
                </button>
              ))}
            </nav>
            
            <div className="p-4 border-t border-border">
              <div className="flex items-center gap-3 px-4 py-3 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary">
                  {Icons.User}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-semibold">Admin User</span>
                  <span className="text-xs text-muted-foreground">admin@example.com</span>
                </div>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-border bg-background flex items-center justify-between px-4 sm:px-6 z-10 shrink-0">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors"
          >
            {Icons.Menu}
          </button>
          
          <div className="flex items-center gap-4">
            <button className="p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors relative">
              {Icons.Bell}
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            <button className="w-9 h-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
              A
            </button>
          </div>
        </header>
        
        {/* Page Content */}
        <div className="flex-1 overflow-auto bg-muted/20 p-4 sm:p-6 md:p-8">
          {children || (
            <div className="max-w-6xl mx-auto space-y-6">
              <h1 className="text-3xl font-bold">Dashboard Overview</h1>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map(i => (
                  <div key={i} className="p-6 rounded-2xl bg-card border border-border shadow-sm">
                    <h3 className="text-muted-foreground text-sm font-medium mb-2">Metric {i}</h3>
                    <p className="text-3xl font-bold">1,234</p>
                    <p className="text-xs text-green-500 mt-2 font-medium">+12.5% from last month</p>
                  </div>
                ))}
              </div>
              
              <div className="min-h-[400px] rounded-2xl bg-card border border-border shadow-sm p-6 flex items-center justify-center">
                <p className="text-muted-foreground">Content Area / Charts</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
