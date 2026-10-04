import { useState } from "react";
import { useLogin } from "../hooks/useAuth";
import { getErrorMessage } from "@/shared/lib/errors";

export function LoginForm({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [agentName, setAgentName] = useState("");
  const login = useLogin(onLoggedIn);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (agentName.trim()) login.mutate(agentName.trim());
  }

  return (
    <form aria-label="Ops login" onSubmit={handleSubmit} className="max-w-sm space-y-3">
      <h1 className="text-2xl font-semibold">Ops console login</h1>
      <div>
        <label htmlFor="agent-name" className="block text-sm">
          Agent name
        </label>
        <input
          id="agent-name"
          value={agentName}
          onChange={(e) => setAgentName(e.target.value)}
          required
          autoComplete="username"
          className="w-full rounded border px-2 py-1"
        />
      </div>
      {login.isError && (
        <p role="alert" className="text-sm text-red-700">
          {getErrorMessage(login.error)}
        </p>
      )}
      <button
        type="submit"
        disabled={login.isPending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {login.isPending ? "Logging in…" : "Log in"}
      </button>
    </form>
  );
}
