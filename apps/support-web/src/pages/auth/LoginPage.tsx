import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Headset } from "lucide-react";
import { Button, Card, Input } from "@/components/ui";

// Internal staff login — deliberately different from the storefront.
// Phase 1 demo credentials: admin@shop.local / admin (password is `admin`).
export function LoginPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@shop.local");
  const [password, setPassword] = useState("admin");
  const [show, setShow] = useState(false);

  return (
    <div className="sp-auth-wrap">
      <div className="flex items-center gap-2 font-bold">
        <Headset size={20} aria-hidden /> Support Console
      </div>
      <p className="sp-muted mt-1">Internal staff only. Real auth arrives in Phase 2.</p>
      <Card className="mt-4">
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            nav("/dashboard");
          }}
        >
          <div>
            <label className="sp-label" htmlFor="s-email">Work email</label>
            <Input id="s-email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </div>
          <div>
            <label className="sp-label" htmlFor="s-pw">Password</label>
            <Input
              id="s-pw"
              type={show ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <Button type="button" variant="ghost" onClick={() => setShow((s) => !s)}>
            {show ? "Hide password" : "Show password"}
          </Button>
          <Button type="submit">Log in to console</Button>
          <p className="sp-muted text-center">Demo: admin@shop.local / admin</p>
        </form>
      </Card>
    </div>
  );
}
