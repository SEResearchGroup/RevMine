/**
 * Card – reusable content card for the design system.
 *
 * Variants:
 *   "default"   – white with border and subtle shadow
 *   "flat"      – white with border, no shadow
 *   "elevated"  – white with stronger shadow (modal-like inner panel)
 *
 * Usage:
 *   <Card>…content…</Card>
 *   <Card variant="flat" className="p-6">…</Card>
 *   <Card.Header>Title</Card.Header>   (optional sub-components)
 *   <Card.Body>…</Card.Body>
 */

function Card({ children, variant = "default", className = "", ...props }) {
  const variants = {
    default:  "bg-white rounded-xl border border-gray-200 shadow-card",
    flat:     "bg-white rounded-xl border border-gray-200",
    elevated: "bg-white rounded-xl border border-gray-200 shadow-card-hover",
  };

  return (
    <div
      className={`${variants[variant] ?? variants.default} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

function CardHeader({ children, className = "", ...props }) {
  return (
    <div
      className={`px-5 py-4 border-b border-gray-200 flex items-center justify-between ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

function CardBody({ children, className = "", ...props }) {
  return (
    <div className={`p-5 ${className}`} {...props}>
      {children}
    </div>
  );
}

function CardFooter({ children, className = "", ...props }) {
  return (
    <div
      className={`px-5 py-4 border-t border-gray-200 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

Card.Header = CardHeader;
Card.Body   = CardBody;
Card.Footer = CardFooter;

export default Card;
