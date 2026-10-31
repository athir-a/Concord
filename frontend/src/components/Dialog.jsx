import { X } from "lucide-react";
import { useEffect, useRef } from "react";

/** The browser's native dialog gives us focus trapping and Escape to close for free. */
export function Dialog({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  return (
    <dialog
      ref={ref}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className={`m-auto w-[calc(100%-2rem)] rounded-lg border border-line bg-surface p-0 text-ink backdrop:bg-ink/30 ${wide ? "max-w-2xl" : "max-w-md"}`}
    >
      <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <h2 className="font-semibold">{title}</h2>
        <button type="button" aria-label="Close" onClick={onClose} className="rounded-md p-1 text-ink-muted hover:bg-canvas hover:text-ink">
          <X size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="p-5">{children}</div>
    </dialog>
  );
}
