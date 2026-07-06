import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "success" | "warning" | "danger" | "outline" | "neutral";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        {
          "bg-primary/20 text-primary": variant === "default",
          "bg-secondary text-secondary-foreground": variant === "secondary",
          "bg-bull/20 text-bull": variant === "success",
          "bg-yellow-500/20 text-yellow-400": variant === "warning",
          "bg-bear/20 text-bear": variant === "danger",
          "border border-border text-muted-foreground": variant === "outline",
          "bg-neutral/20 text-neutral": variant === "neutral",
        },
        className,
      )}
      {...props}
    />
  );
}
