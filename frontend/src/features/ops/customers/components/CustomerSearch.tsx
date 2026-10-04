import { useState } from "react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCustomerSearch } from "../hooks/useCustomers";
import { useUiFlags } from "../../tickets/hooks/useTickets";

export function CustomerSearch() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const search = useCustomerSearch(query);
  const flags = useUiFlags();

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
      <form onSubmit={handleSearch} className="flex gap-2">
        <label htmlFor="customer-search" className="sr-only">
          Search customers
        </label>
        <input
          id="customer-search"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Name, email, or code"
          className="rounded border px-2 py-1"
        />
        <button type="submit" className="rounded-md bg-slate-900 px-4 py-1 text-sm text-white">
          Search
        </button>
      </form>
      {search.isPending && query && <LoadingState what="customers" />}
      {search.isError && <ErrorState message={getErrorMessage(search.error)} />}
      {search.data && (
        <ul className="mt-3 space-y-2 text-sm">
          {search.data.length === 0 && <li>No customers found.</li>}
          {search.data.map((customer) => (
            <li key={customer.id} className="rounded border p-2">
              {customer.name} ({customer.code}) — {customer.email}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
