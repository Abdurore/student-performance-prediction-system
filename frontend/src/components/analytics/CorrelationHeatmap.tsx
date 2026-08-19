import type { CorrelationsResponse } from '@/types/analytics'

function cellColor(value: number): string {
  const clamped = Math.max(-1, Math.min(1, value))
  if (clamped >= 0) {
    // 0 -> white, 1 -> amber
    const alpha = clamped
    return `rgba(217, 119, 6, ${alpha})`
  }
  // 0 -> white, -1 -> navy
  const alpha = -clamped
  return `rgba(15, 32, 56, ${alpha})`
}

export function CorrelationHeatmap({ data }: { data: CorrelationsResponse }) {
  const { features, matrix } = data
  const cellSize = 26

  return (
    <div className="overflow-auto">
      <div
        className="grid"
        style={{
          gridTemplateColumns: `140px repeat(${features.length}, ${cellSize}px)`,
        }}
      >
        <div />
        {features.map((f) => (
          <div key={f} className="flex h-[110px] items-end justify-center pb-1" style={{ width: cellSize }}>
            <span
              className="origin-bottom-left whitespace-nowrap text-[10px] text-slate-500"
              style={{ transform: 'rotate(-60deg)' }}
            >
              {f}
            </span>
          </div>
        ))}
        {matrix.map((row, i) => (
          <div key={features[i]} className="contents">
            <div className="flex h-[26px] items-center truncate pr-2 text-[11px] text-slate-500" title={features[i]}>
              {features[i]}
            </div>
            {row.map((value, j) => (
              <div
                key={`${features[i]}-${features[j]}`}
                title={`${features[i]} × ${features[j]}: ${value.toFixed(2)}`}
                className="border border-white"
                style={{ width: cellSize, height: cellSize, backgroundColor: cellColor(value) }}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
        <span>-1</span>
        <span
          className="h-3 w-32 rounded"
          style={{ background: 'linear-gradient(to right, #0F2038, #ffffff, #D97706)' }}
        />
        <span>+1</span>
      </div>
    </div>
  )
}
