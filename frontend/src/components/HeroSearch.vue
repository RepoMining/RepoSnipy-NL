<script setup>
import { computed } from 'vue'

import { formatNumber } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  meta: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'search', 'pick'])

const REQUIREMENT_SAMPLES = [
  'Extract tables from PDF files and export CSV',
  'Make asynchronous HTTP requests in Python',
  'Build a REST API quickly',
]

// Every semantic channel uses 768-dimensional vectors.
const channelDim = computed(
  () => props.meta?.layers?.[0]?.dim ?? 768,
)

function onInput(event) {
  emit('update:modelValue', event.target.value)
}

function submit() {
  emit('search')
}
</script>

<template>
  <section class="hero" :class="{ 'hero--compact': compact }">
    <template v-if="!compact">
      <div class="hero__badge">
        <span>⚡</span>
        <span>
          RepoSim4Py-powered
          <b>multi-channel semantic retrieval</b>
        </span>
      </div>
      <h1 class="hero__title">
        Find the most relevant Python repositories
      </h1>
      <p class="hero__sub">
        Enter a GitHub repository to find related projects, or describe the
        capability you need and search the existing semantic index.
      </p>
    </template>

    <div class="search">
      <div class="search__box">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.2-3.2" />
        </svg>
        <input
          class="search__input"
          type="text"
          spellcheck="false"
          autocomplete="off"
          placeholder="Enter owner/repo or a requirement, e.g. extract PDF tables to CSV"
          :value="modelValue"
          :disabled="disabled"
          @input="onInput"
          @keyup.enter="submit"
        />
        <button class="btn btn--primary" type="button" :disabled="busy || disabled" @click="submit">
          <span v-if="busy" class="spinner" />
          <span>{{ busy ? 'Searching' : 'Search' }}</span>
        </button>
      </div>

      <div v-if="meta?.samples?.length" class="search__hint">
        <span>Repositories:</span>
        <button
          v-for="sample in meta.samples.slice(0, 4)"
          :key="sample"
          class="chip-btn"
          type="button"
          @click="emit('pick', sample)"
        >
          {{ sample }}
        </button>
      </div>
      <div class="search__hint">
        <span>Requirements:</span>
        <button
          v-for="sample in REQUIREMENT_SAMPLES"
          :key="sample"
          class="chip-btn"
          type="button"
          @click="emit('pick', sample)"
        >
          {{ sample }}
        </button>
      </div>
    </div>

    <div v-if="!compact && meta?.status === 'ready'" class="stats">
      <div class="stat">
        <div class="stat__value">{{ formatNumber(meta.index_size) }}</div>
        <div class="stat__label">Indexed repositories</div>
      </div>
      <div class="stat">
        <div class="stat__value">{{ meta.layers?.length ?? 5 }}</div>
        <div class="stat__label">Retrieval channels</div>
      </div>
      <div class="stat">
        <div class="stat__value">{{ channelDim }}</div>
        <div class="stat__label">Vector dimension</div>
      </div>
      <div class="stat">
        <div class="stat__value">{{ (meta.device || 'cpu').toUpperCase() }}</div>
        <div class="stat__label">Compute device</div>
      </div>
    </div>
  </section>
</template>
