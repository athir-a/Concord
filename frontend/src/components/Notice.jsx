const TONES = {
  danger: "bg-danger-soft text-danger",
  success: "bg-success-soft text-success",
};

export function Notice({ tone = "danger", children }) {
  return (
    <p role={tone === "danger" ? "alert" : "status"} className={`rounded-md px-3 py-2 ${TONES[tone]}`}>
      {children}
    </p>
  );
}
