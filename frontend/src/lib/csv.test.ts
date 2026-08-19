import { describe, expect, it } from 'vitest'
import { buildBatchTemplateCsv, parseStudentIdsCsv } from './csv'

describe('parseStudentIdsCsv', () => {
  it('parses a header + valid ID rows into validIds', () => {
    const result = parseStudentIdsCsv('student_id\n1\n2\n3\n')
    expect(result.validIds).toEqual([1, 2, 3])
    expect(result.invalidCount).toBe(0)
    expect(result.duplicateCount).toBe(0)
  })

  it('works without a header row too', () => {
    const result = parseStudentIdsCsv('4\n5\n')
    expect(result.validIds).toEqual([4, 5])
  })

  it('skips duplicate IDs and counts them separately from valid ones', () => {
    const result = parseStudentIdsCsv('student_id\n1\n2\n2\n3\n')
    expect(result.validIds).toEqual([1, 2, 3])
    expect(result.duplicateCount).toBe(1)
  })

  it('flags non-numeric and non-positive rows as invalid, excluding them from validIds', () => {
    const result = parseStudentIdsCsv('student_id\nabc\n0\n-5\n3.5\n7\n')
    expect(result.validIds).toEqual([7])
    expect(result.invalidCount).toBe(4)
  })

  it('ignores blank lines', () => {
    const result = parseStudentIdsCsv('student_id\n1\n\n\n2\n')
    expect(result.validIds).toEqual([1, 2])
  })

  it('only reads the first column when extra columns are present', () => {
    const result = parseStudentIdsCsv('student_id,name\n1,Alice\n2,Bob\n')
    expect(result.validIds).toEqual([1, 2])
  })

  it('returns an empty result for an empty file', () => {
    const result = parseStudentIdsCsv('')
    expect(result.validIds).toEqual([])
    expect(result.invalidCount).toBe(0)
  })
})

describe('buildBatchTemplateCsv', () => {
  it('produces a header the parser recognises, with example valid IDs', () => {
    const csv = buildBatchTemplateCsv()
    const parsed = parseStudentIdsCsv(csv)
    expect(parsed.validIds.length).toBeGreaterThan(0)
    expect(parsed.invalidCount).toBe(0)
  })
})
