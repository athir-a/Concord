import { useState } from "react";

/** Form state plus server-side errors mapped onto fields. The backend is the validator. */
export function useForm(initialValues, onSubmit) {
  const [values, setValues] = useState(initialValues);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const field = (name) => ({
    name,
    value: values[name],
    error: fieldErrors[name],
    onChange: (event) => {
      setValues((current) => ({ ...current, [name]: event.target.value }));
      setFieldErrors((current) => ({ ...current, [name]: undefined }));
    },
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
      if (Object.keys(fields).length === 0) setFormError(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return { field, values, handleSubmit, submitting, formError };
}
