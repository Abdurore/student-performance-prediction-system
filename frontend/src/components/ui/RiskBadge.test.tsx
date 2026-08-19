import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RiskBadge } from './RiskBadge'
import type { RiskTier } from '@/types/prediction'

describe('RiskBadge', () => {
  const cases: Array<[RiskTier, string]> = [
    ['low', 'Low risk'],
    ['moderate', 'Moderate risk'],
    ['high', 'High risk'],
    ['critical', 'Critical risk'],
  ]

  it.each(cases)('renders the label for tier "%s"', (tier, label) => {
    render(<RiskBadge tier={tier} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('applies a tier-specific CSS class so colour stays consistent across the app', () => {
    render(<RiskBadge tier="critical" />)
    expect(screen.getByText('Critical risk')).toHaveClass('risk-badge-critical')
  })
})
