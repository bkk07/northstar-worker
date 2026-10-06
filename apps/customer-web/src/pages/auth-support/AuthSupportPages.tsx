import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, Badge, Button, Input, EmptyState } from "@/components/ui";

// Phase 1: auth shell. Real JWT + Argon2 flow arrives Phase 2.
export function LoginPage() {
  const [show, setShow] = useState(false);
  return (
    <div className="ns-form">
      <h1 className="ns-title">Welcome back</h1>
      <p className="ns-muted">Log in to shop and track orders. Auth wires up in Phase 2.</p>
      <Card className="ns-form-card">
        <form className="flex flex-col gap-3" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label className="ns-label" htmlFor="email">Email</label>
            <Input id="email" type="email" placeholder="you@example.com" autoComplete="email" />
          </div>
          <div>
            <label className="ns-label" htmlFor="password">Password</label>
            <Input id="password" type={show ? "text" : "password"} placeholder="••••••••" autoComplete="current-password" />
          </div>
          <Button type="button" variant="ghost" onClick={() => setShow((s) => !s)}>
            {show ? "Hide password" : "Show password"}
          </Button>
          <Button type="submit">Log in</Button>
          <p className="ns-muted text-center">
            New here? <Link to="/signup" className="underline">Create an account</Link>
          </p>
        </form>
      </Card>
    </div>
  );
}

export function SignupPage() {
  const [show, setShow] = useState(false);
  return (
    <div className="ns-form">
      <h1 className="ns-title">Create your account</h1>
      <p className="ns-muted">Sign up arrives in Phase 2 with validation and loading/error states.</p>
      <Card className="ns-form-card">
        <form className="flex flex-col gap-3" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label className="ns-label" htmlFor="name">Name</label>
            <Input id="name" placeholder="Jane Doe" autoComplete="name" />
          </div>
          <div>
            <label className="ns-label" htmlFor="email2">Email</label>
            <Input id="email2" type="email" placeholder="you@example.com" autoComplete="email" />
          </div>
          <div>
            <label className="ns-label" htmlFor="pw2">Password</label>
            <Input id="pw2" type={show ? "text" : "password"} placeholder="Min. 8 characters" autoComplete="new-password" />
          </div>
          <Button type="button" variant="ghost" onClick={() => setShow((s) => !s)}>
            {show ? "Hide password" : "Show password"}
          </Button>
          <Button type="submit">Sign up</Button>
        </form>
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
      <Badge>Phase 5 · {id}</Badge>
      <h1 className="ns-title mt-2">Ticket conversation</h1>
      <p className="ns-muted">Status, messages, and support responses arrive in Phase 5.</p>
    </Card>
  );
}
