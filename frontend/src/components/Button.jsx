const VARIANTS = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  secondary: "bg-surface text-ink border border-line-strong hover:bg-canvas",
  ghost: "text-ink-muted hover:bg-canvas hover:text-ink",
};

export function Button({ variant = "primary", loading = false, disabled, className = "", children, ...props }) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md px-3.5 font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {loading ? "Working…" : children}
    </button>
  );
}
