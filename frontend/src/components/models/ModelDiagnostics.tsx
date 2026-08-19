import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import type { ClassificationMetrics, RegressionMetrics } from '@/types/model'

function isClassification(metrics: Record<string, unknown>): metrics is Record<string, unknown> & ClassificationMetrics {
  return 'confusion_matrix' in metrics && 'roc_curve' in metrics
}

function isRegression(metrics: Record<string, unknown>): metrics is Record<string, unknown> & RegressionMetrics {
  return 'residual_plot_data' in metrics && 'predicted_vs_actual_data' in metrics
}

function ConfusionMatrix({ matrix }: { matrix: number[][] }) {
  const [[tn, fp], [fn, tp]] = matrix
  const cells = [
    { label: 'True negative', value: tn, tone: 'bg-green-50 text-[#15803D]' },
    { label: 'False positive', value: fp, tone: 'bg-red-50 text-[#B91C1C]' },
    { label: 'False negative', value: fn, tone: 'bg-red-50 text-[#B91C1C]' },
    { label: 'True positive', value: tp, tone: 'bg-green-50 text-[#15803D]' },
  ]
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Confusion matrix</p>
      <div className="grid max-w-xs grid-cols-2 gap-1.5">
        {cells.map((cell) => (
          <div key={cell.label} className={`rounded-md p-3 text-center ${cell.tone}`}>
            <p className="text-lg font-semibold">{cell.value}</p>
            <p className="text-[11px]">{cell.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ModelDiagnostics({ metrics }: { metrics: Record<string, unknown> }) {
  if (isClassification(metrics)) {
    const rocPoints = [...metrics.roc_curve.fpr.map((fpr, i) => ({ fpr, tpr: metrics.roc_curve.tpr[i] }))].sort(
      (a, b) => a.fpr - b.fpr,
    )
    const calibrationPoints = metrics.calibration_curve.prob_pred.map((prob_pred, i) => ({
      prob_pred,
      prob_true: metrics.calibration_curve.prob_true[i],
    }))

    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ConfusionMatrix matrix={metrics.confusion_matrix} />
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            ROC curve (AUC {metrics.roc_auc.toFixed(3)})
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={rocPoints}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="fpr" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} label={{ value: 'FPR', position: 'insideBottom', offset: -3, fontSize: 10 }} />
              <YAxis dataKey="tpr" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Line type="monotone" dataKey="tpr" stroke="#0F2038" strokeWidth={2} dot={false} />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#CBD5E1" strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Calibration curve</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={calibrationPoints}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="prob_pred" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} label={{ value: 'Predicted', position: 'insideBottom', offset: -3, fontSize: 10 }} />
              <YAxis dataKey="prob_true" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Line type="monotone" dataKey="prob_true" stroke="#D97706" strokeWidth={2} dot={{ r: 2 }} />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#CBD5E1" strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  if (isRegression(metrics)) {
    const predVsActual = metrics.predicted_vs_actual_data.y_true.map((y_true, i) => ({
      y_true,
      y_pred: metrics.predicted_vs_actual_data.y_pred[i],
    }))
    const residuals = metrics.residual_plot_data.y_true.map((y_true, i) => ({
      y_true,
      residual: metrics.residual_plot_data.residual[i],
    }))
    const bounds = [...predVsActual.map((p) => p.y_true), ...predVsActual.map((p) => p.y_pred)]
    const minB = Math.min(...bounds)
    const maxB = Math.max(...bounds)

    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Predicted vs actual (R² {metrics.r2.toFixed(3)})
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="y_true" type="number" name="Actual" tick={{ fontSize: 10 }} domain={[minB, maxB]} />
              <YAxis dataKey="y_pred" type="number" name="Predicted" tick={{ fontSize: 10 }} domain={[minB, maxB]} />
              <ZAxis range={[20, 20]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(v: number) => v.toFixed(2)} />
              <Scatter data={predVsActual} fill="#0F2038" fillOpacity={0.5} />
              <ReferenceLine segment={[{ x: minB, y: minB }, { x: maxB, y: maxB }]} stroke="#D97706" strokeDasharray="4 4" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Residuals (RMSE {metrics.rmse.toFixed(3)})
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="y_true" type="number" name="Actual" tick={{ fontSize: 10 }} />
              <YAxis dataKey="residual" type="number" name="Residual" tick={{ fontSize: 10 }} />
              <ZAxis range={[20, 20]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(v: number) => v.toFixed(2)} />
              <Scatter data={residuals} fill="#EA580C" fillOpacity={0.5} />
              <ReferenceLine y={0} stroke="#CBD5E1" strokeDasharray="4 4" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  return <p className="text-sm text-slate-500">No diagnostic data available for this model.</p>
}
