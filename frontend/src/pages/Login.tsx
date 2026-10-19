// Only one user exists (set in the backend .env: MASTER_USERNAME / MASTER_PASSWORD).
import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api, setToken } from "../api";
import { Logo } from "../components/Layout";
import { Button, ErrorText, Field, inputClass } from "../components/ui";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api<{ token: string }>("/api/auth/login", { body: { username, password } });
      setToken(res.token);
      window.location.href = "/";
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand p-4">
      <div className="pointer-events-none fixed -left-24 -top-24 size-96 rounded-full bg-teal-200/50 blur-3xl" aria-hidden />
      <div className="pointer-events-none fixed -bottom-32 -right-24 size-[28rem] rounded-full bg-rose-200/50 blur-3xl" aria-hidden />
      <div className="relative w-full max-w-sm animate-fade-in">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <form onSubmit={submit} className="space-y-4 rounded-card border border-white bg-surface/90 p-6 shadow-xl shadow-teal-900/10 backdrop-blur sm:p-7">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Welcome back</h1>
            <p className="mt-1 text-sm text-muted">Log in to manage your job search.</p>
          </div>
          <Field label="Username">
            <input className={inputClass} autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} />
          </Field>
          <Field label="Password">
            <input className={inputClass} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <ErrorText error={error} />
          <Button type="submit" kind="primary" icon={LogIn} loading={busy} className="w-full">Log in</Button>
        </form>
      </div>
    </div>
  );
}
