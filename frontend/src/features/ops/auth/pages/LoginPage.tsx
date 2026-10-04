import { useNavigate } from "react-router-dom";
import { LoginForm } from "../components/LoginForm";

export default function LoginPage() {
  const navigate = useNavigate();
  return (
    <main className="mx-auto max-w-3xl p-8">
      <LoginForm onLoggedIn={() => navigate("/ops/tickets")} />
    </main>
  );
}
