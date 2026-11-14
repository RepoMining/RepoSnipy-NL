<script setup>
import { ref, watch } from 'vue'

import { api, parseRepoInput } from '../api'

const props = defineProps({
  open: { type: Boolean, default: false },
  initialName: { type: String, default: '' },
})

const emit = defineEmits(['close', 'done'])

const name = ref('')
const token = ref('')
const busy = ref(false)
const error = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      name.value = props.initialName || ''
      error.value = ''
      busy.value = false
    }
  },
)

async function submit() {
  const repo = parseRepoInput(name.value)
  if (!repo) {
    error.value = 'Enter owner/repo or a complete GitHub repository URL'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const result = await api.indexRepo(repo, token.value.trim())
    emit('done', result)
  } catch (cause) {
    error.value = cause.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="open" class="modal-mask" @click.self="!busy && emit('close')">
    <div class="modal">
      <h3 class="modal__title">Encode a repository into the index</h3>
      <p class="modal__desc">
        RepoSim4Py will fetch the repository code, docstrings, README, and
        dependency files, generate channel embeddings, and persist them to the
        local index. The first request loads a large local model and may take
        several minutes.
      </p>

      <div class="field">
        <label>Repository</label>
        <input v-model="name" type="text" spellcheck="false" placeholder="owner/repo" :disabled="busy" />
      </div>

      <div class="field">
        <label>GitHub token (optional but strongly recommended)</label>
        <input
          v-model="token"
          type="password"
          spellcheck="false"
          placeholder="ghp_..."
          :disabled="busy"
        />
      </div>

      <div v-if="error" class="notice notice--error" style="padding: 12px 14px">
        <span class="notice__icon">⚠️</span>
        <div class="notice__text">{{ error }}</div>
      </div>

      <div v-if="busy" class="progress-note">
        <span class="spinner" />
        <span>Fetching and encoding. Keep this page open…</span>
      </div>

      <div class="modal__actions">
        <button class="btn" type="button" :disabled="busy" @click="emit('close')">Cancel</button>
        <button class="btn btn--primary" type="button" :disabled="busy" @click="submit">
          {{ busy ? 'Processing…' : 'Start encoding' }}
        </button>
      </div>
    </div>
  </div>
</template>
