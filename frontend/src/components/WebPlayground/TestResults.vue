<template>
	<div class="w-full bg-surface-white border border-outline-gray-2 rounded-lg p-4 shadow-sm space-y-3">
		<div class="flex items-center justify-between border-b pb-2">
			<div class="flex items-center space-x-2">
				<h4 class="text-sm font-semibold text-ink-gray-9">{{ __('Test Results') }}</h4>
				<span
					v-if="props.submitted"
					class="text-xs px-2 py-0.5 rounded font-medium"
					:class="props.passed ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-red-100 text-red-800 border border-red-300'"
				>
					{{ props.passed ? __('Passed') : __('Failed') }}
				</span>
			</div>
			<div class="text-sm font-bold font-mono">
				<span :class="props.passed ? 'text-emerald-600' : 'text-amber-600'">
					{{ props.score }}%
				</span>
				<span class="text-xs text-ink-gray-5 ml-1 font-normal">({{ props.earnedPoints }} / {{ props.totalPoints }} {{ __('pts') }})</span>
			</div>
		</div>

		<!-- List of assertions -->
		<div v-if="!props.results || !props.results.length" class="text-xs text-ink-gray-5 py-2 text-center italic">
			{{ __('Click "Run" or "Submit" to evaluate your code against test cases.') }}
		</div>

		<div v-else class="space-y-2 max-h-[220px] overflow-y-auto pr-1">
			<div
				v-for="(res, idx) in props.results"
				:key="idx"
				class="p-2.5 rounded-md border text-xs flex items-start justify-between gap-2"
				:class="res.passed ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950' : 'bg-red-50/60 border-red-200 text-red-950'"
			>
				<div class="flex items-start space-x-2 flex-1 min-w-0">
					<span class="mt-0.5 shrink-0">
						<svg v-if="res.passed" class="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
						</svg>
						<svg v-else class="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
						</svg>
					</span>
					<div class="flex-1 min-w-0">
						<div class="font-medium text-ink-gray-9 flex items-center gap-1">
							<span>{{ res.title }}</span>
							<span v-if="res.required" class="text-[10px] text-red-600 bg-red-100 px-1 rounded">{{ __('Required') }}</span>
						</div>
						<div class="text-[11px] text-ink-gray-6 mt-0.5 leading-snug">{{ res.message }}</div>
					</div>
				</div>
				<div class="text-xs font-mono font-semibold shrink-0" :class="res.passed ? 'text-emerald-700' : 'text-red-700'">
					{{ res.earned_points }} / {{ res.points }} {{ __('pts') }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	results: {
		type: Array,
		default: () => [],
	},
	score: {
		type: Number,
		default: 0,
	},
	earnedPoints: {
		type: Number,
		default: 0,
	},
	totalPoints: {
		type: Number,
		default: 0,
	},
	passed: {
		type: Boolean,
		default: false,
	},
	submitted: {
		type: Boolean,
		default: false,
	},
})
</script>
