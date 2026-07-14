import type { ReactNode } from "react";

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="param-section">
      <div className="param-section-header">{title}</div>
      <div className="param-section-body">{children}</div>
    </div>
  );
}
