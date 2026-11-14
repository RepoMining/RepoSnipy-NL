<script setup>
defineProps({
  active: { type: String, default: 'blend' },
})

defineEmits(['change'])

const MODES = [
  {
    key: 'blend',
    label: 'README + Docstring',
    hint: 'README 0.33 / docstring 0.67 weighted fusion',
  },
  { key: 'readme', label: 'README only', hint: 'Project the requirement into README space' },
  { key: 'doc', label: 'Docstring only', hint: 'Project the requirement into docstring space' },
]
</script>

<template>
  <div class="modes">
    <span class="modes__group-label">Requirement channels</span>
    <button
      v-for="mode in MODES"
      :key="mode.key"
      class="mode-tab"
      :class="{
        'mode-tab--active': active === mode.key,
        'mode-tab--domain': mode.key === 'blend',
      }"
      type="button"
      :title="mode.hint"
      @click="$emit('change', mode.key)"
    >
      <i class="mode-tab__dot" />
      {{ mode.label }}
    </button>
  </div>
</template>
