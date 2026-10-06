# support-web (Phase 1)

Separate internal support/admin console (spec §4). Different login experience
from the storefront; dashboard + ticket shells only. Manual + AI resolution
arrive in Phases 6–9.

- Dev: `npm install && npm run dev` → http://localhost:5175
- Demo login: `admin@shop.local` / `admin` (prefilled on the login page)
- Routes: `/login /dashboard /tickets /tickets/:id`
