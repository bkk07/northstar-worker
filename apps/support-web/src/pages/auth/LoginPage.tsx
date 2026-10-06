import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Headset } from "lucide-react";
import { Button, Card, Input } from "@/components/ui";
import { staffApiErrorMessage } from "@/lib/api-client";
import { useStaffAuth } from "@/stores/auth-store";

// Internal staff login — deliberately different from the storefront.
// Demo credentials: admin@northstar.shop / admin (password is `admin`).
export function LoginPage() {
  const nav = useNavigate();
  const login = useStaffAuth((s) => s.login);
  const [email, setEmail] = useState("admin@northstar.shop");
  const [password, setPassword] = useState("admin");
  const [show, setShow] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) {
      setSubmitError("Enter your work email and password.");
      return;
    }
    setPending(true);
    setSubmitError(null);
    try {
      await login(email.trim(), password);
      nav("/dashboard");
    } catch (err) {
      setSubmitError(
        err instanceof Error && err.message.includes("not staff")
          ? err.message
          : staffApiErrorMessage(err, "Staff login failed. Please try again."),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="sp-auth-wrap">
      <div className="flex items-center gap-2 font-bold">
        <Headset size={20} aria-hidden /> Support Console
      </div>
      <p className="sp-muted mt-1">Internal staff only. Customer accounts cannot sign in here.</p>
      <Card className="mt-4">
        <form className="flex flex-col gap-3" onSubmit={onSubmit}>
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
          {submitError ? <p className="text-sm text-red-600" role="alert">{submitError}</p> : null}
          <Button type="submit" disabled={pending}>{pending ? "Signing in…" : "Log in to console"}</Button>
          <p className="sp-muted text-center">Demo: admin@northstar.shop / admin</p>
        </form>
      </Card>
    </div>
  );
}
