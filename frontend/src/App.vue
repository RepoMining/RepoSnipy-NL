<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api, formatNumber, parseRepoInput } from './api'
import AppHeader from './components/AppHeader.vue'
import HeroSearch from './components/HeroSearch.vue'
import IndexDialog from './components/IndexDialog.vue'
import ModeTabs from './components/ModeTabs.vue'
import RepoSummary from './components/RepoSummary.vue'
import RequirementModeTabs from './components/RequirementModeTabs.vue'
import ResultList from './components/ResultList.vue'

const THEME_KEY = 'reposnipy.theme'

const MODE_LABELS = {
  domain: 'Similar domain',
  code: 'Code similarity',
  doc: 'Docstring similarity',
  readme: 'README similarity',
  requirement: 'Dependency similarity',
}

const MODE_NOTES = {
  code: 'Score = normalized code-channel cosine',
  doc: 'Score = normalized docstring-channel cosine',
  readme: 'Score = normalized README-channel cosine',
  requirement: 'Score = normalized dependency-channel cosine',
}

const REQUIREMENT_MODE_LABELS = {
  blend: 'Blended requirement match',
  readme: 'Requirement · README',
  doc: 'Requirement · Docstring',
}

/* ------------------------------- 状态 ---------------------------------- */

const theme = ref('dark')
const meta = ref(null)
const metaState = ref('loading')
const metaError = ref('')

const input = ref('')
const searchKind = ref('repo')
const query = ref(null)
const requirement = ref(null)
const queryError = ref('')
const queryErrorKind = ref('')

const mode = ref('domain')
const requirementMode = ref('blend')
const limit = ref(10)
const results = ref([])
const resultsLoading = ref(false)
const resultsError = ref('')
const searchBusy = ref(false)

const showIndexDialog = ref(false)

let pollTimer = null
let heartbeatTimer = null
let searchSeq = 0
// 后端是否掉过线。用它而不是 metaState 判断恢复，
// 因为后端重启时 /api/meta 会先返回 loading 再返回 ready。
let backendDown = false

// 空闲时每隔几秒静默探一次后端，掉线了才提示，避免界面一直假装"就绪"
const HEARTBEAT_MS = 6000

/* ------------------------------- 主题 ---------------------------------- */

function applyTheme(value) {
  document.documentElement.dataset.theme = value
  try {
    localStorage.setItem(THEME_KEY, value)
  } catch {
    /* 隐私模式下写入失败可以忽略 */
  }
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

watch(theme, applyTheme)

/* ---------------------------- 初始化 / 元信息 --------------------------- */

async function loadMeta() {
  try {
    const data = await api.meta()
    meta.value = data
    if (data.status === 'ready') {
      metaState.value = 'ready'
      metaError.value = ''
      // 后端刚恢复：把之前失败的结果自动补回来
      if (backendDown) {
        backendDown = false
        if (query.value || requirement.value) loadResults()
      }
      scheduleHeartbeat()
    } else if (data.status === 'error') {
      metaState.value = 'error'
      metaError.value = data.error || data.message
    } else {
      metaState.value = 'loading'
      schedulePoll()
    }
  } catch (cause) {
    metaState.value = 'error'
    metaError.value = cause.message
    schedulePoll()
  }
}

function schedulePoll() {
  if (pollTimer) return
  pollTimer = setTimeout(() => {
    pollTimer = null
    loadMeta()
  }, 1500)
}

function scheduleHeartbeat() {
  if (heartbeatTimer) return
  heartbeatTimer = setTimeout(() => {
    heartbeatTimer = null
    loadMeta().then(() => {
      if (metaState.value === 'ready') scheduleHeartbeat()
    })
  }, HEARTBEAT_MS)
}

/* ------------------------------- 检索 ---------------------------------- */

/** 后端掉线时统一处理：顶部状态切成断开，并持续重连。 */
function noteBackendProblem(cause) {
  if (!cause?.offline) return
  backendDown = true
  metaState.value = 'error'
  metaError.value = cause.message
  schedulePoll()
}

function modeAvailable(repo, key) {
  if (!repo) return false
  const layers = repo.available_layers || []
  if (key === 'domain') return layers.length > 0
  return layers.includes(key)
}

async function loadResults() {
  const isRequirement = searchKind.value === 'requirement'
  if (isRequirement ? !requirement.value : !query.value) return
  const seq = ++searchSeq
  resultsLoading.value = true
  resultsError.value = ''
  try {
    const data = isRequirement
      ? await api.searchRequirement(
          requirement.value.query,
          requirementMode.value,
          limit.value,
        )
      : await api.search(query.value.name, mode.value, limit.value)
    if (seq !== searchSeq) return // 已经有更新的请求了，丢弃这次结果
    backendDown = false
    results.value = data.results || []
    if (isRequirement) {
      requirement.value = {
        query: data.query,
        normalized_query: data.normalized_query,
        mode: data.mode,
        weights: data.weights,
      }
    }
  } catch (cause) {
    if (seq !== searchSeq) return
    results.value = []
    resultsError.value = cause.message
    noteBackendProblem(cause)
  } finally {
    if (seq === searchSeq) resultsLoading.value = false
  }
}

async function runSearch(rawName) {
  const text = String(rawName ?? input.value).trim()
  const name = parseRepoInput(text)
  queryError.value = ''
  queryErrorKind.value = ''

  if (!text) {
    query.value = null
    requirement.value = null
    results.value = []
    queryErrorKind.value = 'invalid'
    queryError.value = 'Enter owner/repo, a GitHub URL, or a natural-language requirement'
    return
  }

  if (!name && text.length < 2) {
    query.value = null
    requirement.value = null
    results.value = []
    queryErrorKind.value = 'invalid'
    queryError.value = 'The requirement is too short'
    return
  }

  input.value = name || text
  searchBusy.value = true
  try {
    if (name) {
      searchKind.value = 'repo'
      requirement.value = null
      const repo = await api.repo(name)
      query.value = repo
      if (!modeAvailable(repo, mode.value)) {
        mode.value = (repo.available_layers || [])[0] ?? 'domain'
      }
    } else {
      searchKind.value = 'requirement'
      query.value = null
      requirement.value = { query: text }
    }
    await loadResults()
    syncHash()
  } catch (cause) {
    query.value = null
    requirement.value = null
    results.value = []
    noteBackendProblem(cause)
    if (cause.status === 404) {
      queryErrorKind.value = 'not-indexed'
      queryError.value = cause.message
    } else {
      queryErrorKind.value = 'failed'
      queryError.value = cause.message
    }
  } finally {
    searchBusy.value = false
  }
}

function retryAll() {
  loadMeta()
  if (query.value || requirement.value) loadResults()
}

watch(mode, () => {
  if (searchKind.value === 'repo' && query.value) {
    loadResults()
    syncHash()
  }
})

watch(requirementMode, () => {
  if (searchKind.value === 'requirement' && requirement.value) {
    loadResults()
    syncHash()
  }
})

watch(limit, () => {
  if (query.value || requirement.value) loadResults()
})

/* ----------------------------- URL 同步 -------------------------------- */

function syncHash() {
  const params = new URLSearchParams()
  if (searchKind.value === 'requirement' && requirement.value) {
    params.set('q', requirement.value.query)
    params.set('requirement_mode', requirementMode.value)
  } else if (query.value) {
    params.set('repo', query.value.name)
    params.set('mode', mode.value)
  }
  const next = params.toString()
  history.replaceState(null, '', next ? `#${next}` : '#')
}

function restoreFromHash() {
  const params = new URLSearchParams(location.hash.replace(/^#/, ''))
  const requirementText = params.get('q')
  const savedRequirementMode = params.get('requirement_mode')
  if (savedRequirementMode && REQUIREMENT_MODE_LABELS[savedRequirementMode]) {
    requirementMode.value = savedRequirementMode
  }
  if (requirementText) {
    searchKind.value = 'requirement'
    requirement.value = { query: requirementText }
    input.value = requirementText
    return true
  }
  const repo = params.get('repo')
  // 旧链接里的 mode=repo（已废弃的仓库整体比对）统一落到同领域
  const savedMode = params.get('mode') === 'repo' ? 'domain' : params.get('mode')
  if (savedMode && MODE_LABELS[savedMode]) mode.value = savedMode
  if (repo) {
    searchKind.value = 'repo'
    input.value = repo
    return true
  }
  return false
}

/* ------------------------------- 其他 ---------------------------------- */

async function onIndexed() {
  showIndexDialog.value = false
  await loadMeta()
  if (input.value) await runSearch(input.value)
}

const modeLabel = computed(() => {
  if (searchKind.value === 'requirement') {
    return REQUIREMENT_MODE_LABELS[requirementMode.value] ?? 'Requirement match'
  }
  return MODE_LABELS[mode.value] ?? 'Similar repositories'
})
// 「同领域」的说明直接读接口返回的生效权重，避免权重调整后文案与后端不一致
const modeNote = computed(() => {
  if (searchKind.value === 'requirement') {
    const weights = requirement.value?.weights
    if (weights) {
      const parts = Object.entries(weights)
        .filter(([, value]) => value > 0)
        .map(([key, value]) => `${key} ${value}`)
      return `Score = ${parts.join(' / ')} weighted cosine; bars are normalized within this result set`
    }
    return 'Score = weighted README/docstring cosine; bars are normalized within this result set'
  }
  if (mode.value === 'domain') {
    const w = meta.value?.domain_weights
    if (w) {
      return `Score = code ${w.code} / doc ${w.doc} / readme ${w.readme} / requirement ${w.requirement} weighted fusion; bars are normalized within this result set`
    }
    return 'Score = weighted fusion across four channels; bars are normalized within this result set'
  }
  return MODE_NOTES[mode.value] ?? ''
})
const notReady = computed(() => metaState.value !== 'ready')

onMounted(() => {
  let stored = 'dark'
  try {
    stored = localStorage.getItem(THEME_KEY) || 'dark'
  } catch {
    stored = 'dark'
  }
  theme.value = stored
  applyTheme(stored)

  loadMeta()

  if (restoreFromHash()) {
    runSearch(input.value)
  }
})

onBeforeUnmount(() => {
  if (pollTimer) clearTimeout(pollTimer)
  if (heartbeatTimer) clearTimeout(heartbeatTimer)
})
</script>

<template>
  <AppHeader :state="metaState" :meta="meta" :theme="theme" @toggle-theme="toggleTheme" />

  <main class="main page">
    <HeroSearch
      v-model="input"
      :meta="meta"
      :compact="Boolean(query || requirement)"
      :busy="searchBusy"
      :disabled="notReady"
      @search="runSearch()"
      @pick="runSearch($event)"
    />

    <div v-if="metaState === 'error'" class="notice notice--error">
      <span class="notice__icon">🔌</span>
      <div>
        <div class="notice__title">API service disconnected</div>
        <div class="notice__text">{{ metaError }}</div>
        <div class="notice__text" style="margin-top: 6px">
          The page retries automatically every 1.5 seconds.
        </div>
        <button class="btn btn--sm" style="margin-top: 12px" type="button" @click="retryAll">
          Retry now
        </button>
      </div>
    </div>

    <div v-else-if="metaState === 'loading'" class="notice">
      <span class="notice__icon"><span class="spinner" /></span>
      <div>
        <div class="notice__title">Loading the vector index</div>
        <div class="notice__text">The first request reads the index and prepares channel matrices.</div>
      </div>
    </div>

    <template v-if="searchKind === 'repo' && query">
      <section class="section">
        <h2 class="section__title">Query repository</h2>
        <RepoSummary :repo="query" />
      </section>

      <section class="section">
        <h2 class="section__title">Retrieval mode</h2>
        <ModeTabs
          :active="mode"
          :repo="query"
          :weights="meta?.domain_weights"
          @change="mode = $event"
        />
      </section>

      <section class="section">
        <ResultList
          :results="results"
          :loading="resultsLoading"
          :error="resultsError"
          :limit="limit"
          :mode-label="modeLabel"
          :note="modeNote"
          @update:limit="limit = $event"
          @retry="loadResults"
        />
      </section>
    </template>

    <template v-else-if="searchKind === 'requirement' && requirement">
      <section class="section">
        <h2 class="section__title">Requirement query</h2>
        <div class="card query-card">
          <div class="query-card__main">
            <div class="requirement-card__label">Natural-language requirement</div>
            <blockquote class="requirement-card__query">{{ requirement.query }}</blockquote>
          </div>
          <div class="query-card__side">
            <div class="side-title">Semantic retrieval</div>
            <div class="query-card__meta">
              Reuses existing README and docstring embeddings without rebuilding the index.
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <h2 class="section__title">Retrieval channel</h2>
        <RequirementModeTabs
          :active="requirementMode"
          @change="requirementMode = $event"
        />
      </section>

      <section class="section">
        <ResultList
          :results="results"
          :loading="resultsLoading"
          :error="resultsError"
          :limit="limit"
          :mode-label="modeLabel"
          :note="modeNote"
          empty-text="No sufficiently relevant repositories were found. Try a clearer requirement or another channel."
          @update:limit="limit = $event"
          @retry="loadResults"
        />
      </section>
    </template>

    <div
      v-else-if="searchKind === 'repo' && queryErrorKind === 'not-indexed'"
      class="notice notice--warn"
    >
      <span class="notice__icon">📦</span>
      <div>
        <div class="notice__title">Repository is not indexed</div>
        <div class="notice__text">{{ queryError }}</div>
        <button
          class="btn btn--sm btn--primary"
          style="margin-top: 12px"
          type="button"
          @click="showIndexDialog = true"
        >
          Encode and add to index
        </button>
      </div>
    </div>

    <div v-else-if="queryError" class="notice notice--error">
      <span class="notice__icon">⚠️</span>
      <div>
        <div class="notice__title">Search failed</div>
        <div class="notice__text">{{ queryError }}</div>
      </div>
    </div>
  </main>

  <footer class="footer">
    <div class="page footer__inner">
      <span v-if="meta?.status === 'ready'">
        Dataset <b class="mono">{{ meta.dataset }}</b> · Index
        <b class="mono">{{ formatNumber(meta.index_size) }}</b> repositories · device
        <b class="mono">{{ meta.device }}</b> · loaded in {{ meta.load_seconds }}s
      </span>
      <span class="footer__spacer" />
      <a href="https://github.com/RepoMining/RepoSim4Py" target="_blank" rel="noreferrer">RepoSim4Py</a>
      <a href="https://github.com/RepoMining/RepoSnipy" target="_blank" rel="noreferrer">RepoSnipy</a>
      <a href="/docs" target="_blank" rel="noreferrer">API</a>
    </div>
  </footer>

  <IndexDialog
    :open="showIndexDialog"
    :initial-name="input"
    @close="showIndexDialog = false"
    @done="onIndexed"
  />
</template>
