import { create } from "zustand";
import { addCartItem, fetchCart, removeCartItem, updateCartItem } from "@/services/shop-api";
import { toast } from "@/stores/toast-store";
import type { Cart } from "@/types";

type CartState = {
  cart: Cart | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  add: (productId: string, quantity?: number) => Promise<void>;
  setQty: (itemId: string, quantity: number) => Promise<void>;
  remove: (itemId: string) => Promise<void>;
};

const emptyCart: Cart = { id: "", items: [], subtotal_paise: 0, total_paise: 0, item_count: 0 };

export const useCart = create<CartState>((set) => ({
  cart: null,
  loading: false,
  error: null,

  refresh: async () => {
    set({ loading: true, error: null });
    try {
      set({ cart: await fetchCart(), loading: false });
    } catch {
      set({ cart: emptyCart, error: "Cart is unavailable offline.", loading: false });
    }
  },

  add: async (productId, quantity = 1) => {
    set({ error: null });
    try {
      set({ cart: await addCartItem(productId, quantity) });
      toast.ok("Added to cart.");
    } catch {
      set({ error: "Could not add to cart. Please try again." });
      toast.bad("Could not add to cart. Please try again.");
      throw new Error("add-to-cart-failed");
    }
  },

  setQty: async (itemId, quantity) => {
    set({ error: null });
    try {
      set({ cart: await updateCartItem(itemId, quantity) });
    } catch {
      set({ error: "Could not update quantity." });
    }
  },

  remove: async (itemId) => {
    set({ error: null });
    try {
      set({ cart: await removeCartItem(itemId) });
    } catch {
      set({ error: "Could not remove the item." });
    }
  },
}));
