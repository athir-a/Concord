import { useState } from "react";

// These have their own editors outside the form's values, and show their own errors.
const CUSTOM_EDITORS = new Set(["customer", "lines", "variants", "products"]);

/** Form state plus server-side errors mapped onto fields. The backend is the validator. */
export function useForm(initialValues, onSubmit) {
  const [values, setValues] = useState(initialValues);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: undefined }));
  };

  const field = (name) => ({
    name,
    value: values[name] ?? "",
    error: fieldErrors[name],
    onChange: (event) => set(name, event.target.value),
  });

  const check = (name) => ({
    name,
    checked: Boolean(values[name]),
    onChange: (event) => set(name, event.target.checked),
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    setFieldErrors({});
    try {
      await onSubmit(values);
    } catch (error) {
      const fields = error.fields || {};
      setFieldErrors(fields);
      // Errors on fields this form doesn't show still need to reach the user.
      const shown = Object.keys(fields).filter((name) => name in values || CUSTOM_EDITORS.has(name));
      if (shown.length === 0) setFormError(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return { field, check, set, values, handleSubmit, submitting, formError, fieldErrors };
}
