import React from 'react';
import { motion } from 'framer-motion';

export const AnimatedHero = ({ 
  title = "Build faster with Template Intelligence", 
  subtitle = "Stop reinventing the wheel. Use premium components and generate only your unique business logic.",
  primaryCta = "Get Started",
  secondaryCta = "View Documentation"
}) => {
  return (
    <section className="relative w-full min-h-[80vh] flex flex-col items-center justify-center overflow-hidden bg-background text-foreground">
      {/* Background decoration */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl opacity-50 mix-blend-multiply" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-3xl opacity-50 mix-blend-multiply" />
      </div>
      
      <div className="relative z-10 container mx-auto px-4 md:px-6 flex flex-col items-center text-center space-y-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="inline-block rounded-full border border-border bg-muted/50 px-3 py-1 text-sm text-muted-foreground backdrop-blur-sm"
        >
          ✨ Introducing the all-new architecture
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
          className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl"
        >
          {title}
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
          className="text-xl text-muted-foreground max-w-2xl"
        >
          {subtitle}
        </motion.p>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          className="flex flex-col sm:flex-row items-center gap-4 pt-4"
        >
          <button className="px-8 py-4 bg-primary text-primary-foreground font-semibold rounded-lg shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-200">
            {primaryCta}
          </button>
          <button className="px-8 py-4 bg-secondary text-secondary-foreground font-semibold rounded-lg hover:bg-secondary/80 transition-all duration-200">
            {secondaryCta}
          </button>
        </motion.div>
      </div>
    </section>
  );
};
