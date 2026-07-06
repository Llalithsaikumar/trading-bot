import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "ghost" | "link" | "bull" | "bear";
  size?: "sm" | "md" | "lg" | "icon";
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
        {
          "bg-primary text-primary-foreground hover:bg-primary/90": variant === "default",
          "bg-destructive text-white hover:bg-destructive/90": variant === "destructive",
          "border border-border bg-transparent hover:bg-secondary": variant === "outline",
          "hover:bg-secondary": variant === "ghost",
          "underline-offset-4 hover:underline text-primary h-auto p-0": variant === "link",
          "bg-bull text-white hover:bg-bull/90": variant === "bull",
          "bg-bear text-white hover:bg-bear/90": variant === "bear",
        },
        {
          "h-7 px-3 text-xs": size === "sm",
          "h-9 px-4 text-sm": size === "md",
          "h-11 px-6 text-base": size === "lg",
          "h-9 w-9 p-0": size === "icon",
        },
        className,
      )}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  ),
);
Button.displayName = "Button";
