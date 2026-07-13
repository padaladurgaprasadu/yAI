import React from 'react';
import { motion } from 'framer-motion';

export const BentoFeatures = ({ 
  title = "Powerful Features", 
  subtitle = "Everything you need to scale your business, beautifully designed."
}) => {
  const features = [
    { title: "Real-time Analytics", description: "Monitor your metrics instantly.", className: "md:col-span-2 bg-blue-500/10 border-blue-500/20" },
    { title: "AI Automation", description: "Let AI handle the busywork.", className: "md:col-span-1 bg-purple-500/10 border-purple-500/20" },
    { title: "Global CDN", description: "Lightning fast delivery worldwide.", className: "md:col-span-1 bg-emerald-500/10 border-emerald-500/20" },
    { title: "Enterprise Security", description: "Bank-grade encryption by default.", className: "md:col-span-2 bg-orange-500/10 border-orange-500/20" },
  ];

  return (
    <section className="py-24 bg-background text-foreground">
      <div className="container mx-auto px-4 md:px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">{title}</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">{subtitle}</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {features.map((feature, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              viewport={{ once: true }}
              className={`p-8 rounded-3xl border border-border bg-card hover:shadow-2xl transition-all duration-300 ${feature.className}`}
            >
              <div className="h-full flex flex-col justify-end">
                <h3 className="text-2xl font-bold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
