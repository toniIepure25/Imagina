export default function SectionRule({
  label,
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`} aria-hidden={label ? undefined : true}>
      <span className="section-rule flex-1" />
      {label ? <span className="hud-label shrink-0">{label}</span> : null}
    </div>
  );
}
