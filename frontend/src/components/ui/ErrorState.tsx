import { AlertTriangle, RotateCw } from 'lucide-react'

interface ErrorStateProps {
  message?: string
  onRetry: () => void
}

export function ErrorState({ message = 'Something went wrong while loading this data.', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-red-100 bg-red-50 px-6 py-10 text-center">
      <AlertTriangle size={22} className="text-[#B91C1C]" />
      <p className="text-sm font-medium text-[#B91C1C]">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-1 flex items-center gap-1.5 rounded-md border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-[#B91C1C] hover:bg-red-100"
      >
        <RotateCw size={14} />
        Retry
      </button>
    </div>
  )
}
