import { create } from "zustand";
import { TOKEN_KEY } from "@/lib/api-client";
import { loginApi, meApi, registerApi, type User } from "@/services/auth-api";

type AuthState = {
  user: User | null;
  token: string | null;
  booted: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  boot: () => Promise<void>;
};

function persist(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem(TOKEN_KEY),
  booted: false,

  login: async (email, password) => {
    const bundle = await loginApi({ email, password });
    persist(bundle.access_token);
    set({ user: bundle.user, token: bundle.access_token, booted: true });
  },

  signup: async (name, email, password) => {
    const bundle = await registerApi({ name, email, password });
    persist(bundle.access_token);
    set({ user: bundle.user, token: bundle.access_token, booted: true });
  },

  logout: () => {
    persist(null);
    set({ user: null, token: null, booted: true });
  },

  boot: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      set({ user: null, token: null, booted: true });
      return;
    }
    try {
      const user = await meApi();
      set({ user, token, booted: true });
    } catch {
      persist(null);
      set({ user: null, token: null, booted: true });
    }
  },
}));
