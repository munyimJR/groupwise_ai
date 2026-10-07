"use client";

import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

/** A restrained hover lift for clickable cards and primary actions. */
export function HoverLift({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={cn("will-change-transform", className)}
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.985 }}
      transition={{ type: "spring", stiffness: 420, damping: 28, mass: 0.6 }}
    >
      {children}
    </motion.div>
  );
}
