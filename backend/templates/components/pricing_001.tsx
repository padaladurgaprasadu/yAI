import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';

export const PricingCards = () => {
  const tiers = [
    {
      name: "Starter",
      price: "$0",
      description: "Perfect for exploring the platform.",
      features: ["1 Project", "Basic Components", "Community Support", "1GB Storage"],
      cta: "Get Started Free",
      popular: false
    },
    {
      name: "Pro",
      price: "$29",
      description: "For professional developers and teams.",
      features: ["Unlimited Projects", "Premium Components", "Priority Support", "50GB Storage", "Custom Domains", "Analytics"],
      cta: "Upgrade to Pro",
      popular: true
    },
    {
      name: "Enterprise",
      price: "$99",
      description: "For large scale organizations.",
      features: ["Everything in Pro", "Dedicated Account Manager", "SLA", "Custom Integrations", "Advanced Security"],
      cta: "Contact Sales",
      popular: false
    }
  ];

  return (
    <section className="py-24 bg-background text-foreground">
      <div className="container mx-auto px-4 md:px-6">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold tracking-tight mb-4">Simple, transparent pricing</h2>
          <p className="text-lg text-muted-foreground">Choose the plan that best fits your needs.</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {tiers.map((tier, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.5 }}
              className={`relative flex flex-col p-8 rounded-2xl border ${
                tier.popular 
                  ? 'border-primary shadow-2xl shadow-primary/20 bg-card' 
                  : 'border-border bg-card/50'
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-4 left-0 right-0 flex justify-center">
                  <span className="bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider py-1 px-3 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}
              
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                <p className="text-muted-foreground text-sm h-10">{tier.description}</p>
              </div>
              
              <div className="mb-8">
                <span className="text-5xl font-extrabold">{tier.price}</span>
                <span className="text-muted-foreground">/mo</span>
              </div>
              
              <ul className="space-y-4 mb-8 flex-1">
                {tier.features.map((feature, i) => (
                  <li key={i} className="flex items-center">
                    <Check className="h-5 w-5 text-primary mr-3 flex-shrink-0" />
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <button className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors ${
                tier.popular 
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}>
                {tier.cta}
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
