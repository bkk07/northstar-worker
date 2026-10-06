import { create } from "zustand";
import { STAFF_TOKEN_KEY } from "@/lib/api-client";
import { staffLoginApi, staffMeApi, type StaffUser } from "@/services/auth-api";

type StaffAuthState = {
  user: StaffUser | null;
  token: string | null;
  booted: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  boot: () => Promise<void>;
};

function persist(token: string | null) {
  if (token) localStorage.setItem(STAFF_TOKEN_KEY, token);
  else localStorage.removeItem(STAFF_TOKEN_KEY);
}

export const useStaffAuth = create<StaffAuthState>((set) => ({
  user: null,
  token: localStorage.getItem(STAFF_TOKEN_KEY),
  booted: false,

  login: async (email, password) => {
    const bundle = await staffLoginApi({ email, password });
    if (bundle.user.role !== "SUPPORT_AGENT") {
      throw new Error("This account is not staff. Use a SUPPORT_AGENT login.");
    }
    persist(bundle.access_token);
    set({ user: bundle.user, token: bundle.access_token, booted: true });
  },

  logout: () => {
    persist(null);
    set({ user: null, token: null, booted: true });
  },

  boot: async () => {
    const token = localStorage.getItem(STAFF_TOKEN_KEY);
    if (!token) {
      set({ user: null, token: null, booted: true });
      return;
    }
    try {
      const user = await staffMeApi();
      if (user.role !== "SUPPORT_AGENT") throw new Error("not staff");
      set({ user, token, booted: true });
    } catch {
      persist(null);
      set({ user: null, token: null, booted: true });
    }
  },
}));
