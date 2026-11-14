/** API client for the RepoSnipy-NL FastAPI service. */

const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, options) {
  let response
  try {
    response = await fetch(`${BASE}${path}`, options)
  } catch (cause) {
    const error = new Error('Cannot reach the API. Confirm that the backend is running at http://localhost:8000.')
    error.offline = true
    error.cause = cause
    throw error
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    const detail = data?.detail
    const error = new Error(typeof detail === 'string' ? detail : `Request failed (HTTP ${response.status})`)
    error.status = response.status
    // A 503 usually means the index is loading or the backend is restarting.
    if (response.status === 503) error.offline = true
    throw error
  }
  return data
}

export const api = {
  meta: () => request('/api/meta'),

  repo: (name) => request(`/api/repo?name=${encodeURIComponent(name)}`),

  search: (name, mode, limit) =>
    request(
      `/api/search?name=${encodeURIComponent(name)}&mode=${encodeURIComponent(mode)}&limit=${limit}`,
    ),

  searchRequirement: (query, mode, limit) =>
    request('/api/search/requirement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, mode, limit }),
    }),

  indexRepo: (name, githubToken) =>
    request('/api/index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, github_token: githubToken || null }),
    }),
}

const REPO_PATTERN =
  /^((git@|http(s)?:\/\/)?(github\.com)(\/|:))?(?<owner>[\w.-]+)\/(?<repo>[\w.-]+?)(\.git)?\/?$/

/** Normalize a GitHub URL, SSH address, or owner/repo input. */
export function parseRepoInput(raw) {
  const text = (raw ?? '').trim()
  if (!text) return null
  const match = REPO_PATTERN.exec(text)
  if (!match?.groups) return null
  return `${match.groups.owner}/${match.groups.repo}`
}

/** 12345 -> 12.3k */
export function formatStars(value) {
  const num = Number(value) || 0
  if (num >= 1000) {
    return `${(num / 1000).toFixed(num >= 10000 ? 0 : 1)}k`
  }
  return String(num)
}

export function formatNumber(value) {
  const num = Number(value) || 0
  return num.toLocaleString('en-US')
}
