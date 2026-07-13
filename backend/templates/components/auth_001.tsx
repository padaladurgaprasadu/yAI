import React from 'react';
import { motion } from 'framer-motion';

export const GlassAuth = ({
  type = "login", // 'login' or 'signup'
  companyName = "yAI Core"
}) => {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background overflow-hidden relative">
      {/* Decorative Blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-primary/30 rounded-full mix-blend-multiply blur-3xl opacity-70 animate-blob" />
      <div className="absolute top-[20%] right-[-10%] w-96 h-96 bg-secondary/30 rounded-full mix-blend-multiply blur-3xl opacity-70 animate-blob animation-delay-2000" />
      <div className="absolute bottom-[-20%] left-[20%] w-96 h-96 bg-purple-500/30 rounded-full mix-blend-multiply blur-3xl opacity-70 animate-blob animation-delay-4000" />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md p-8 rounded-3xl bg-card/40 backdrop-blur-xl border border-white/10 shadow-2xl"
      >
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">{companyName}</h2>
          <p className="text-muted-foreground mt-2">
            {type === 'login' ? "Welcome back. Sign in to your account." : "Create an account to get started."}
          </p>
        </div>
        
        <form className="space-y-4 flex flex-col" onSubmit={(e) => e.preventDefault()}>
          {type === 'signup' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Name</label>
              <input 
                type="text" 
                className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder:text-muted-foreground"
                placeholder="John Doe"
              />
            </div>
          )}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Email</label>
            <input 
              type="email" 
              className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder:text-muted-foreground"
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-foreground">Password</label>
              {type === 'login' && <a href="#" className="text-xs text-primary hover:underline">Forgot password?</a>}
            </div>
            <input 
              type="password" 
              className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-foreground placeholder:text-muted-foreground"
              placeholder="••••••••"
            />
          </div>
          
          <button className="w-full py-3 mt-4 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 transition-colors shadow-lg shadow-primary/25">
            {type === 'login' ? "Sign In" : "Sign Up"}
          </button>
        </form>
        
        <div className="mt-6 text-center text-sm text-muted-foreground">
          {type === 'login' ? (
            <p>Don't have an account? <a href="#" className="text-primary hover:underline font-medium">Sign up</a></p>
          ) : (
            <p>Already have an account? <a href="#" className="text-primary hover:underline font-medium">Sign in</a></p>
          )}
        </div>
      </motion.div>
    </div>
  );
};
