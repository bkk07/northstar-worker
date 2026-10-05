import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import { Search } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCustomerSearch } from "../hooks/useCustomers";
import { useUiFlags } from "../../tickets/hooks/useTickets";

export function CustomerSearch() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const search = useCustomerSearch(query);
  const flags = useUiFlags();
  const reduce = useReducedMotion();

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setQuery(draft);
  }

  // REMOVED_SEARCH_FIELD fault (S7): the input is absent by design and the
  // worker must fall back to the read API. Humans see the same surface.
  if (flags.data?.removed_search_field) {
    return (
      <p role="status" className="text-sm text-slate-600">
        Customer search is unavailable right now. Use the ticket queue instead.
      </p>
    );
  }

  return (
    <div>
      <form
        aria-label="Find customers"
        onSubmit={handleSearch}
        className="flex max-w-lg gap-2"
      >
        <div className="relative flex-1">
          <label htmlFor="customer-search" className="sr-only">
            Search customers
          </label>
          <Search
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          />
          <input
            id="customer-search"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Name, email, or code"
            autoComplete="off"
            className="ns-input pl-9"
          />
        </div>
        <button type="submit" className="ns-btn ns-btn-primary shrink-0">
          Search
        </button>
      </form>
      {search.isPending && query && <LoadingState what="customers" />}
      {search.isError && <ErrorState message={getErrorMessage(search.error)} />}
      {search.data &&
        (search.data.length === 0 ? (
          <div className="mt-3">
            <EmptyState title="No customers found" desc={`Nothing matches “${query}”.`} />
          </div>
        ) : (
          <ul className="mt-3 space-y-2">
            {search.data.map((customer, i) => (
              <motion.li
                key={customer.id}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: reduce ? 0 : Math.min(i * 0.04, 0.3), duration: 0.25 }}
                className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm"
              >
                <span
                  aria-hidden
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700"
                >
                  {customer.name
                    .split(" ")
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")
                    .toUpperCase()}
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium text-slate-900">
                    {customer.name}{" "}
                    <span className="font-mono text-xs font-normal text-slate-400">
                      ({customer.code})
                    </span>
                  </span>
                  <span className="block truncate text-[13px] text-slate-500">
                    {customer.email}
                  </span>
                </span>
              </motion.li>
            ))}
          </ul>
        ))}
    </div>
  );
}
