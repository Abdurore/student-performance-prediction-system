import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, getStoredToken, setStoredToken } from './api'

function mockFetchOnce(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok ?? true,
    status: response.status ?? 200,
    statusText: response.statusText ?? 'OK',
    json: response.json ?? (async () => ({})),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('token storage', () => {
  afterEach(() => localStorage.clear())

  it('round-trips a token through localStorage', () => {
    expect(getStoredToken()).toBeNull()
    setStoredToken('abc123')
    expect(getStoredToken()).toBe('abc123')
  })

  it('clears the token when set to null', () => {
    setStoredToken('abc123')
    setStoredToken(null)
    expect(getStoredToken()).toBeNull()
  })
})

describe('api client', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('attaches the bearer token when one is stored', async () => {
    setStoredToken('my-token')
    const fetchMock = mockFetchOnce({ json: async () => ({ ok: true }) })
    await api.get('/whoami')
    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer my-token')
  })

  it('omits the Authorization header when no token is stored', async () => {
    const fetchMock = mockFetchOnce({ json: async () => ({}) })
    await api.get('/public')
    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBeNull()
  })

  it('sends JSON bodies with a Content-Type header on post', async () => {
    const fetchMock = mockFetchOnce({ json: async () => ({}) })
    await api.post('/students', { name: 'Ada' })
    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ name: 'Ada' }))
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json')
  })

  it('returns undefined for a 204 response without parsing a body', async () => {
    const fetchMock = mockFetchOnce({ status: 204, json: async () => { throw new Error('should not be called') } })
    const result = await api.del('/interventions/1')
    expect(result).toBeUndefined()
    expect(fetchMock).toHaveBeenCalled()
  })

  it('throws ApiError with the server-provided string detail on failure', async () => {
    mockFetchOnce({ ok: false, status: 403, json: async () => ({ detail: 'Forbidden.' }) })
    await expect(api.get('/students/1')).rejects.toMatchObject(
      new ApiError(403, 'Forbidden.'),
    )
  })

  it('joins a FastAPI validation-error array into one message', async () => {
    mockFetchOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: 'field required' }, { msg: 'must be positive' }] }),
    })
    try {
      await api.post('/students', {})
      expect.fail('expected api.post to throw')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(422)
      expect((err as ApiError).message).toBe('field required; must be positive')
    }
  })

  it('falls back to statusText when the error body is not JSON', async () => {
    mockFetchOnce({ ok: false, status: 500, statusText: 'Internal Server Error', json: async () => { throw new Error('not json') } })
    await expect(api.get('/boom')).rejects.toMatchObject({ status: 500, message: 'Internal Server Error' })
  })
})
