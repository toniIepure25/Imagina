import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { buttonStyles, type ButtonSize, type ButtonVariant } from "./Button";

export default function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: {
  href: ComponentProps<typeof Link>["href"];
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
} & Omit<ComponentProps<typeof Link>, "href" | "className" | "children">) {
  return (
    <Link href={href} className={buttonStyles({ variant, size, className })} {...props}>
      {children}
    </Link>
  );
}
