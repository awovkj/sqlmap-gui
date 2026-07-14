import { useEffect, useState } from "react";

/** Dropdown that falls back to free-text entry (and vice versa). */
export function SelectOrInput({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (val: string) => void;
  options: string[];
  placeholder?: string;
}) {
  const [customMode, setCustomMode] = useState(false);

  useEffect(() => {
    if (value && options.length > 0 && !options.includes(value)) {
      setCustomMode(true);
    }
  }, [value, options]);

  if (customMode || options.length === 0) {
    return (
      <div className="select-or-input">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        {options.length > 0 && (
          <button type="button" className="toggle-mode-btn" onClick={() => setCustomMode(false)}>
            选择
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="select-or-input">
      <select
        value={options.includes(value) ? value : ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">-- 请选择 --</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <button type="button" className="toggle-mode-btn" onClick={() => setCustomMode(true)}>
        自定义
      </button>
    </div>
  );
}
