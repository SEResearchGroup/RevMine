import { Loader2 } from "lucide-react";

/**
 * Button – unified button component for the design system.
 *
 * Variants:
 *   "primary"   – solid blue, white text  (default)
 *   "secondary" – light gray background, dark text
 *   "outline"   – transparent, blue border and text
 *   "danger"    – red, for destructive actions
 *   "ghost"     – no background, muted text, subtle hover
 *
 * Usage:
 *   <Button variant="primary" icon={Plus} onClick={handleCreate}>
 *     New Workspace
 *   </Button>
 *   <Button variant="outline" loading>Saving...</Button>
 *   <Button variant="secondary" size="sm" icon={Filter}>Filter</Button>
 */

const BASE =
  "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none";

const VARIANTS = {
  primary:
    "bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500",
  secondary:
    "bg-gray-100 text-gray-700 hover:bg-gray-200 focus-visible:ring-gray-400",
  outline:
    "border border-blue-600 text-blue-600 bg-transparent hover:bg-blue-50 focus-visible:ring-blue-500",
  danger:
    "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500",
  ghost:
    "text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus-visible:ring-gray-400",
};

const SIZES = {
  sm:  "px-3 py-1.5 text-sm",
  md:  "px-5 py-2.5 text-sm",
  lg:  "px-6 py-3 text-base",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  icon: Icon,
  iconPosition = "left",
  loading = false,
  disabled = false,
  className = "",
  type = "button",
  ...props
}) {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={`${BASE} ${VARIANTS[variant] ?? VARIANTS.primary} ${SIZES[size] ?? SIZES.md} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : Icon && iconPosition === "left" ? (
        <Icon className="w-4 h-4" />
      ) : null}

      {children}

      {!loading && Icon && iconPosition === "right" && (
        <Icon className="w-4 h-4" />
      )}
    </button>
  );
}
