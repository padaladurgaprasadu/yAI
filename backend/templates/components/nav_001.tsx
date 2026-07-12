import React, { useState } from 'react';
import { Menu, X, User, Bell } from 'lucide-react';

export const GlassNavbar = ({ 
  logo = "yAI", 
  links = [
    { label: "Dashboard", href: "#" },
    { label: "Projects", href: "#" },
    { label: "Settings", href: "#" }
  ]
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 w-full z-50 border-b border-border/40 bg-background/60 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
              {logo}
            </span>
            <div className="hidden md:ml-10 md:flex md:space-x-8">
              {links.map((link, idx) => (
                <a key={idx} href={link.href} className="text-muted-foreground hover:text-foreground inline-flex items-center px-1 pt-1 text-sm font-medium transition-colors">
                  {link.label}
                </a>
              ))}
            </div>
          </div>
          
          <div className="hidden md:flex items-center space-x-4">
            <button className="p-2 rounded-full text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Bell className="h-5 w-5" />
            </button>
            <button className="flex items-center justify-center h-8 w-8 rounded-full bg-primary text-primary-foreground">
              <User className="h-5 w-5" />
            </button>
          </div>
          
          <div className="-mr-2 flex items-center md:hidden">
            <button 
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
            >
              {isOpen ? <X className="block h-6 w-6" /> : <Menu className="block h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {isOpen && (
        <div className="md:hidden border-t border-border/40 bg-background/95 backdrop-blur-md">
          <div className="pt-2 pb-3 space-y-1">
            {links.map((link, idx) => (
              <a key={idx} href={link.href} className="block pl-3 pr-4 py-2 border-l-4 border-transparent text-base font-medium text-muted-foreground hover:text-foreground hover:bg-muted hover:border-primary">
                {link.label}
              </a>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};
