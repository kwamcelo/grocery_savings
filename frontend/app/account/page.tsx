"use client";

import { FormEvent, useState } from "react";
import { LogIn, Mail, UserPlus } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { supabase } from "@/lib/supabase";

export default function AccountPage() {
  const { isConfigured, isLoading, user, signOut } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitEmailAuth(mode: "sign-in" | "sign-up") {
    if (!supabase) return;

    if (!email.trim() || password.length < 6) {
      setError("Enter an email and a password with at least 6 characters.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    const result =
      mode === "sign-up"
        ? await supabase.auth.signUp({ email: email.trim(), password })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password });

    setIsSubmitting(false);

    if (result.error) {
      setError(result.error.message);
      return;
    }

    setMessage(
      mode === "sign-up"
        ? "Account created. Check your email if confirmation is required."
        : "Signed in.",
    );
  }

  async function handleEmailAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitEmailAuth("sign-in");
  }

  async function handleGoogleSignIn() {
    if (!supabase) return;
    setError(null);
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
  }

  if (!isConfigured) {
    return (
      <div className="stack">
        <section className="page-title">
          <div>
            <h1>Account</h1>
            <p>Sign-in is not set up yet. Add your Supabase settings to the app first.</p>
          </div>
        </section>
      </div>
    );
  }

  if (isLoading) {
    return <p className="muted">Loading account...</p>;
  }

  if (user) {
    return (
      <div className="stack">
        <section className="page-title">
          <div>
            <h1>Account</h1>
            <p>You are signed in as {user.email ?? "your account"}.</p>
          </div>
        </section>
        <section className="panel stack">
          <p className="muted">
            Your receipts stay private unless you choose to share item prices.
          </p>
          <button type="button" onClick={signOut}>
            Sign out
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Create an account</h1>
          <p>
            Save your receipts privately, or choose to share item prices so others can
            find better grocery deals nearby.
          </p>
        </div>
      </section>

      <section className="panel stack">
        <button type="button" onClick={handleGoogleSignIn}>
          <LogIn size={18} aria-hidden="true" />
          Continue with Google
        </button>

        <form className="auth-form" onSubmit={handleEmailAuth}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          <div className="actions">
            <button disabled={isSubmitting} type="submit">
              <Mail size={18} aria-hidden="true" />
              Sign in
            </button>
            <button
              className="secondary"
              disabled={isSubmitting}
              type="button"
              onClick={() => submitEmailAuth("sign-up")}
            >
              <UserPlus size={18} aria-hidden="true" />
              Create account
            </button>
          </div>
        </form>

        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="save-status">{message}</p> : null}

        <p className="muted">
          If you share prices, only item prices, store, and date are used. Your full
          receipt and total spending stay private.
        </p>
      </section>
    </div>
  );
}
