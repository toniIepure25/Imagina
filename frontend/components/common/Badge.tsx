export default function Badge({
  children,
  color = "bg-accent/20 text-accent-glow",
}: {
  children: React.ReactNode;
  color?: string;
}) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {children}
    </span>
  );
}
