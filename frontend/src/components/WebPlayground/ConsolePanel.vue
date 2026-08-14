<template>
	<div class="w-full flex flex-col bg-[#1e1e1e] text-white rounded-md border border-[#3c3c3c] overflow-hidden">
		<!-- Console Header -->
		<div class="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c] text-xs font-mono select-none">
			<div class="flex items-center space-x-2">
				<span class="font-semibold text-gray-300">{{ __('Console Output') }}</span>
				<span class="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.2 rounded-full">{{ logs.length }}</span>
			</div>
			<button
				type="button"
				class="text-[11px] text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
				@click="clearLogs"
			>
				{{ __('Clear') }}
			</button>
		</div>

		<!-- Log Entries -->
		<div class="p-3 font-mono text-xs overflow-y-auto max-h-[160px] min-h-[80px] space-y-1 bg-[#1e1e1e]">
			<div v-if="!logs.length" class="text-gray-500 italic text-[11px]">
				{{ __('Console output will appear here when code executes...') }}
			</div>
			<div
				v-for="(log, idx) in logs"
				:key="idx"
				class="flex items-start space-x-2 py-0.5 border-b border-gray-800/60 leading-relaxed font-mono"
				:class="{
					'text-gray-200': log.type === 'log',
					'text-amber-400 bg-amber-950/20 px-1 rounded': log.type === 'warn',
					'text-red-400 bg-red-950/30 px-1 rounded': log.type === 'error',
				}"
			>
				<span class="text-gray-500 text-[10px] shrink-0 select-none">[{{ log.time }}]</span>
				<span class="font-semibold shrink-0 uppercase text-[10px] tracking-wide" :class="getTypeBadgeClass(log.type)">
					{{ log.type }}
				</span>
				<span class="whitespace-pre-wrap break-all flex-1">{{ log.message }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
	logs: {
		type: Array,
		default: () => [],
	},
})

const emit = defineEmits(['clear'])

const clearLogs = () => {
	emit('clear')
}

const getTypeBadgeClass = (type) => {
	if (type === 'error') return 'text-red-400'
	if (type === 'warn') return 'text-amber-400'
	return 'text-blue-400'
}
</script>
