import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useEffect, useState } from "react";
import { useAuth } from "@/stores/auth-store";

function SessionBoot({ children }: { children: ReactNode }) {
  const boot = useAuth((s) => s.boot);
  useEffect(() => {
    void boot();
  }, [boot]);
  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <SessionBoot>{children}</SessionBoot>
    </QueryClientProvider>
  );
}
