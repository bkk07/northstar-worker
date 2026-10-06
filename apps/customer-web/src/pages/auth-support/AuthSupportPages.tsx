import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Card, Badge, Button, Input, EmptyState } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-client";
import { useAuth } from "@/stores/auth-store";

const emailOk = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="text-[13px] text-red-600" role="alert">{msg}</p>;
}

export function LoginPage() {
  const nav = useNavigate();
  const login = useAuth((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (!emailOk(email)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Enter your password.";
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    setPending(true);
    setSubmitError(null);
    try {
      await login(email.trim(), password);
      nav("/products");
    } catch (err) {
      setSubmitError(apiErrorMessage(err, "Login failed. Please try again."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="ns-form">
      <h1 className="ns-title">Welcome back</h1>
      <p className="ns-muted">Log in to shop and track orders.</p>
      <Card className="ns-form-card">
        <form className="flex flex-col gap-3" onSubmit={onSubmit} noValidate>
          <div>
            <label className="ns-label" htmlFor="email">Email</label>
            <Input
              id="email" type="email" placeholder="you@example.com" autoComplete="email"
              value={email} onChange={(e) => setEmail(e.target.value)}
            />
            <FieldError msg={errors.email} />
          </div>
          <div>
            <label className="ns-label" htmlFor="password">Password</label>
            <Input
              id="password" type={show ? "text" : "password"} placeholder="••••••••"
              autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)}
            />
            <FieldError msg={errors.password} />
          </div>
          <Button type="button" variant="ghost" onClick={() => setShow((s) => !s)}>
            {show ? "Hide password" : "Show password"}
          </Button>
          {submitError ? <p className="text-sm text-red-600" role="alert">{submitError}</p> : null}
          <Button type="submit" disabled={pending}>{pending ? "Logging in…" : "Log in"}</Button>
          <p className="ns-muted text-center">
            New here? <Link to="/signup" className="underline">Create an account</Link>
          </p>
        </form>
      </Card>
    </div>
  );
}

export function SignupPage() {
  const nav = useNavigate();
  const signup = useAuth((s) => s.signup);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (name.trim().length < 1) next.name = "Enter your name.";
    if (!emailOk(email)) next.email = "Enter a valid email address.";
    if (password.length < 8) next.password = "Password must be at least 8 characters.";
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    setPending(true);
    setSubmitError(null);
    try {
      await signup(name.trim(), email.trim(), password);
      setDone(true);
      setTimeout(() => nav("/products"), 800);
    } catch (err) {
      setSubmitError(apiErrorMessage(err, "Sign-up failed. Please try again."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="ns-form">
      <h1 className="ns-title">Create your account</h1>
      <p className="ns-muted">One account for shopping, orders, and support.</p>
      <Card className="ns-form-card">
        {done ? (
          <p className="text-sm text-emerald-700" role="status">Account created — taking you to products…</p>
        ) : (
          <form className="flex flex-col gap-3" onSubmit={onSubmit} noValidate>
            <div>
              <label className="ns-label" htmlFor="name">Name</label>
              <Input id="name" placeholder="Jane Doe" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
              <FieldError msg={errors.name} />
            </div>
            <div>
              <label className="ns-label" htmlFor="email2">Email</label>
              <Input id="email2" type="email" placeholder="you@example.com" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <FieldError msg={errors.email} />
            </div>
            <div>
              <label className="ns-label" htmlFor="pw2">Password</label>
              <Input id="pw2" type={show ? "text" : "password"} placeholder="Min. 8 characters" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <FieldError msg={errors.password} />
            </div>
            <Button type="button" variant="ghost" onClick={() => setShow((s) => !s)}>
              {show ? "Hide password" : "Show password"}
            </Button>
            {submitError ? <p className="text-sm text-red-600" role="alert">{submitError}</p> : null}
            <Button type="submit" disabled={pending}>{pending ? "Creating account…" : "Sign up"}</Button>
          </form>
        )}
      </Card>
    </div>
  );
}

export function SupportPage() {
  return (
    <Card>
      <div className="ns-row-between">
        <h1 className="ns-title">Support tickets</h1>
        <Badge>Phase 5</Badge>
      </div>
      <EmptyState
        title="No tickets yet"
        hint="After delivery you can raise a ticket (refund, replacement, return, cancellation, delivery, payment, general)."
        action={<Link to="/orders" className="ns-btn ns-btn-secondary ns-btn-sm">View orders</Link>}
      />
    </Card>
  );
}

export function TicketDetailPage() {
  const { id } = useParams();
  return (
    <Card>
      <Badge>Phase 5{id ? ` · ${id}` : ""}</Badge>
      <h1 className="ns-title mt-2">Ticket conversation</h1>
      <p className="ns-muted">Status, messages, and support responses arrive in Phase 5.</p>
    </Card>
  );
}
