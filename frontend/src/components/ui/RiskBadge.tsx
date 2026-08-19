import type { RiskTier } from '@/types/prediction'

const LABELS: Record<RiskTier, string> = {
  low: 'Low risk',
  moderate: 'Moderate risk',
  high: 'High risk',
  critical: 'Critical risk',
}

export function RiskBadge({ tier }: { tier: RiskTier }) {
  return <span className={`risk-badge-${tier}`}>{LABELS[tier]}</span>
}
