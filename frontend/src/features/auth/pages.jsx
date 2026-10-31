import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { homeFor, useAuth } from "../../app/auth";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { Notice } from "../../components/Notice";
import { api } from "../../lib/api";
import { useForm } from "../../lib/useForm";

const PASSWORD_HINT = "At least 9 characters, with an uppercase letter, a lowercase letter and a special character.";
const LINK = "font-medium text-accent hover:underline";

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
      <Field label="Password" type="password" autoComplete="new-password" hint={PASSWORD_HINT} {...form.field("password")} />
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
      <Field label="New password" type="password" autoComplete="new-password" autoFocus hint={PASSWORD_HINT} {...form.field("password")} />
      <Button type="submit" loading={form.submitting} className="w-full">Change password</Button>
    </form>
  );
}
