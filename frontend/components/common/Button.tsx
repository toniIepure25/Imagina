"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}

const variants = {
  primary: "bg-accent text-white shadow-[0_0_24px_rgba(91,108,255,0.24)] hover:bg-accent-glow hover:text-background",
  secondary: "border border-surface-border text-foreground/80 hover:bg-surface hover:border-accent/50",
  danger: "bg-danger text-white hover:bg-red-600 shadow-[0_0_20px_rgba(239,68,68,0.16)]",
  ghost: "text-foreground/60 hover:text-foreground hover:bg-surface",
};

const sizes = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-8 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className = "", disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={`rounded-lg font-medium transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-glow/70 ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled}
      {...props}
    />
  )
);
Button.displayName = "Button";
export default Button;
