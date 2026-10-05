import { useReducedMotion, type Variants } from "framer-motion";

/** Central motion policy: page fade+slideUp 0.3s stagger, cards lift, buttons tap. */
export function useMotionOK(): boolean {
  return !useReducedMotion();
}

/** Page container: staggers children fade+slideUp. */
export const pageContainer: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06, delayChildren: 0.02 },
  },
};

/** Page item: fade + slideUp 0.3s. */
export const pageItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] },
  },
};

/** Shared tween for hover/tap (snappy, Linear-like). */
export const snappyTransition = { type: "tween" as const, duration: 0.18, ease: "easeOut" as const };
