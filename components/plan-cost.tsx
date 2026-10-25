export function PlanCost({ amount, group = false }: { amount: number | null; group?: boolean }) {
  return amount === null ? <strong>{group ? "Cost not verified" : "Price not available"}</strong> : <><strong>~{new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(amount)}</strong>{!group && <span> / person</span>}</>;
}
