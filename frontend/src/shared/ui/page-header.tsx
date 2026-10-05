import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { pageContainer, pageItem } from "@/shared/ui/motion";

/**
 * Page header with staggered fade+slideUp entrance (0.3s).
 * Falls back to a plain header when prefers-reduced-motion is set.
 */
export function PageHeader({
  eyebrow,
  title,
  desc,
  actions,
}: {
  eyebrow?: string;
  title: string;
  desc?: string;
  actions?: ReactNode;
}) {
  const reduce = useReducedMotion();
  const body = (
    <>
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-indigo-600">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
          {title}
        </h1>
        {desc && <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">{desc}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </>
  );
  if (reduce) {
    return <div className="flex flex-wrap items-start justify-between gap-4">{body}</div>;
  }
  return (
    <motion.div
      variants={pageContainer}
      initial="hidden"
      animate="show"
      className="flex flex-wrap items-start justify-between gap-4"
    >
      <motion.div variants={pageItem} className="flex flex-wrap items-start justify-between gap-4 w-full">
        {body}
      </motion.div>
    </motion.div>
  );
}

/** Wrap page sections so they stagger in on enter (fade+slideUp 0.3s). */
export function PageEnter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div variants={pageContainer} initial="hidden" animate="show" className={className}>
      {children}
    </motion.div>
  );
}

export function PageEnterItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div variants={pageItem} className={className}>
      {children}
    </motion.div>
  );
}

export function Section({
  title,
  desc,
  actions,
  children,
}: {
  title: string;
  desc?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="ns-section-title">{title}</h2>
          {desc && <p className="ns-section-desc">{desc}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
