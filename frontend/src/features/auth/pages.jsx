import { Check, Circle } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { homeFor, useAuth } from "../../app/auth";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { Notice } from "../../components/Notice";
import { api } from "../../lib/api";
import { useForm } from "../../lib/useForm";

const LINK = "font-medium text-accent hover:underline";

const PASSWORD_RULES = [
  ["More than eight characters", (p) => p.length > 8],
  ["An uppercase letter", (p) => /[A-Z]/.test(p)],
  ["A lowercase letter", (p) => /[a-z]/.test(p)],
  ["A special character", (p) => /[^A-Za-z0-9\s]/.test(p)],
];

/** Live help while typing. The server still checks, and has the final word. */
export function PasswordChecklist({ password }) {
  return (
    <ul className="mt-2 space-y-1 text-[13px]">
      {PASSWORD_RULES.map(([label, passes]) => {
        const met = passes(password);
        return (
          <li key={label} className={`flex items-center gap-1.5 ${met ? "text-success" : "text-ink-muted"}`}>
            {met ? <Check size={13} aria-hidden="true" /> : <Circle size={13} aria-hidden="true" />}
            {label}
            <span className="sr-only">{met ? "(met)" : "(not met yet)"}</span>
          </li>
        );
      })}
    </ul>
  );
}

function Heading({ title, subtitle }) {
  return (
    <div className="mb-5">
      <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-1 text-ink-muted">{subtitle}</p>}
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const form = useForm({ email: "", password: "" }, async (values) => {
    const user = await login(values);
    navigate(location.state?.from || homeFor(user), { replace: true });
  });

  return (
    <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
      <Heading title="Log in" />
      {form.formError && <Notice>{form.formError}</Notice>}
      <Field label="Email" type="email" autoComplete="email" autoFocus {...form.field("email")} />
      <Field label="Password" type="password" autoComplete="current-password" {...form.field("password")} />
      <Button type="submit" loading={form.submitting} className="w-full">Log in</Button>
      <div className="flex justify-between text-[13px]">
        <Link to="/signup" className={LINK}>Create an account</Link>
        <Link to="/forgot-password" className={LINK}>Forgot password?</Link>
      </div>
    </form>
  );
}

export function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const form = useForm({ name: "", company: "", email: "", password: "" }, async (values) => {
    const user = await signup(values);
    navigate(homeFor(user), { replace: true });
  });

  return (
    <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
      <Heading title="Create your account" subtitle="See and manage your subscriptions in one place." />
      {form.formError && <Notice>{form.formError}</Notice>}
      <Field label="Your name" autoComplete="name" autoFocus {...form.field("name")} />
      <Field label="Company (optional)" autoComplete="organization" {...form.field("company")} />
      <Field label="Email" type="email" autoComplete="email" {...form.field("email")} />
      <div>
        <Field label="Password" type="password" autoComplete="new-password" required {...form.field("password")} />
        <PasswordChecklist password={form.values.password} />
      </div>
      <Button type="submit" loading={form.submitting} className="w-full">Create account</Button>
      <p className="text-[13px] text-ink-muted">
        Already have an account? <Link to="/login" className={LINK}>Log in</Link>
      </p>
    </form>
  );
}

export function ForgotPasswordPage() {
  const [message, setMessage] = useState(null);
  const form = useForm({ email: "" }, async (values) => {
    const result = await api("/auth/password-reset", { method: "POST", body: values });
    setMessage(result.detail);
  });

  return (
    <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
      <Heading title="Reset your password" subtitle="We'll email you a link to choose a new one." />
      {form.formError && <Notice>{form.formError}</Notice>}
      {message && <Notice tone="success">{message}</Notice>}
      <Field label="Email" type="email" autoComplete="email" autoFocus {...form.field("email")} />
      <Button type="submit" loading={form.submitting} className="w-full">Send reset link</Button>
      <Link to="/login" className={`block text-[13px] ${LINK}`}>Back to log in</Link>
    </form>
  );
}

export function ResetPasswordPage() {
  const { uid, token } = useParams();
  const [message, setMessage] = useState(null);
  const form = useForm({ password: "" }, async (values) => {
    const result = await api("/auth/password-reset/confirm", {
      method: "POST",
      body: { uid, token, password: values.password },
    });
    setMessage(result.detail);
  });

  if (message) {
    return (
      <div className="space-y-4">
        <Heading title="Password changed" />
        <Notice tone="success">{message}</Notice>
        <Link to="/login" className={`block ${LINK}`}>Go to log in</Link>
      </div>
    );
  }

  return (
    <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
      <Heading title="Choose a new password" />
      {form.formError && <Notice>{form.formError}</Notice>}
      <div>
        <Field label="New password" type="password" autoComplete="new-password" autoFocus required {...form.field("password")} />
        <PasswordChecklist password={form.values.password} />
      </div>
      <Button type="submit" loading={form.submitting} className="w-full">Change password</Button>
    </form>
  );
}
