<script setup>
import { computed } from 'vue'

const props = defineProps({
  active: { type: String, required: true },
  repo: { type: Object, default: null },
  weights: { type: Object, default: null },
})

defineEmits(['change'])

const CHANNEL_MODES = [
  { key: 'code', label: 'Code', hint: 'Code embeddings' },
  { key: 'doc', label: 'Docstring', hint: 'Docstring embeddings' },
  { key: 'readme', label: 'README', hint: 'README embeddings' },
  { key: 'requirement', label: 'Dependencies', hint: 'Dependency embeddings' },
]

const layers = computed(() => new Set(props.repo?.available_layers || []))

const domainHint = computed(() => {
  const w = props.weights
  const text = w
    ? `readme ${w.readme} / doc ${w.doc} / code ${w.code} / requirement ${w.requirement}`
    : 'readme / doc / code weighted fusion'
  return `Similar-domain search: weighted fusion across semantic channels (${text})`
})

function disabled(mode) {
  if (!props.repo) return true
  if (mode.key === 'domain') return layers.value.size === 0
  return !layers.value.has(mode.key)
}
</script>

<template>
  <div class="modes">
    <span class="modes__group-label">Default</span>
    <button
      class="mode-tab mode-tab--domain"
      :class="{ 'mode-tab--active': active === 'domain' }"
      type="button"
      :title="domainHint"
      :disabled="disabled({ key: 'domain' })"
      @click="$emit('change', 'domain')"
    >
      <i class="mode-tab__dot" />
      Similar domain
    </button>

    <span class="modes__divider" />

    <span class="modes__group-label">Single channel</span>
    <button
      v-for="mode in CHANNEL_MODES"
      :key="mode.key"
      class="mode-tab"
      :class="{ 'mode-tab--active': active === mode.key }"
      type="button"
      :title="mode.hint"
      :disabled="disabled(mode)"
      @click="$emit('change', mode.key)"
    >
      <i class="mode-tab__dot" />
      {{ mode.label }}
    </button>
  </div>
</template>
