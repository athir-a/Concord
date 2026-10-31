const DATE = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
const DATE_TIME = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const MONTH = new Intl.DateTimeFormat("en-IN", { month: "short", year: "2-digit" });

/** Display only. Amounts arrive as strings and all arithmetic happens on the server. */
export function money(value, currency = "INR") {
  if (value === null || value === undefined) return "–";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(Number(value));
}

export function compactMoney(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", notation: "compact", maximumFractionDigits: 1,
  }).format(Number(value));
}

// Date-only values are parsed as local dates, or they can shift a day across time zones.
function parseDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
}

export const date = (value) => (value ? DATE.format(parseDate(value)) : "–");
export const dateTime = (value) => (value ? DATE_TIME.format(new Date(value)) : "–");
export const month = (value) => MONTH.format(parseDate(value));

export function today() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function addDays(isoDate, days) {
  const value = new Date(`${isoDate}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export const titleCase = (value) => (value ? value[0].toUpperCase() + value.slice(1).replace(/_/g, " ") : "");

export const INTERVALS = { daily: "day", weekly: "week", monthly: "month", yearly: "year" };

export const PAYMENT_METHODS = [
  ["bank_transfer", "Bank transfer"], ["upi", "UPI"], ["card", "Card"],
  ["cash", "Cash"], ["cheque", "Cheque"], ["other", "Other"],
];

export function newKey() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** For headline figures, where paise only add noise. Exact amounts are on the records. */
export function wholeMoney(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
}
