export interface ParsedIdRow {
  line: number
  raw: string
  studentId: number | null
}

export interface ParsedBatchCsv {
  rows: ParsedIdRow[]
  validIds: number[]
  invalidCount: number
  duplicateCount: number
}

export function parseStudentIdsCsv(text: string): ParsedBatchCsv {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  const dataLines = lines.length > 0 && /^student_id$/i.test(lines[0].split(',')[0].trim()) ? lines.slice(1) : lines

  const rows: ParsedIdRow[] = dataLines.map((raw, i) => {
    const cell = raw.split(',')[0].trim()
    const parsed = Number(cell)
    const studentId = cell !== '' && Number.isInteger(parsed) && parsed > 0 ? parsed : null
    return { line: i + 1, raw: cell, studentId }
  })

  const seen = new Set<number>()
  let duplicateCount = 0
  const validIds: number[] = []
  for (const row of rows) {
    if (row.studentId === null) continue
    if (seen.has(row.studentId)) {
      duplicateCount += 1
      continue
    }
    seen.add(row.studentId)
    validIds.push(row.studentId)
  }

  return {
    rows,
    validIds,
    invalidCount: rows.filter((r) => r.studentId === null).length,
    duplicateCount,
  }
}

export function buildBatchTemplateCsv(): string {
  return 'student_id\n1\n2\n3\n'
}
