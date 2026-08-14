<template>
	<div class="w-full h-full flex flex-col bg-white rounded-md border border-outline-gray-2 overflow-hidden shadow-sm">
		<!-- Header bar -->
		<div class="flex items-center justify-between px-3 py-1.5 bg-surface-gray-2 border-b border-outline-gray-2 text-xs select-none">
			<div class="flex items-center space-x-2">
				<span class="inline-block w-2.5 h-2.5 rounded-full bg-green-500"></span>
				<span class="font-semibold text-ink-gray-7">{{ __('Live Preview') }}</span>
			</div>
			<div class="flex items-center space-x-2 text-ink-gray-5">
				<span class="text-[10px] px-1.5 py-0.5 rounded bg-surface-gray-3 border font-mono">sandbox="allow-scripts"</span>
				<button
					type="button"
					class="p-1 hover:bg-surface-gray-3 rounded text-ink-gray-6 transition-colors"
					:title="__('Refresh Preview')"
					@click="refresh"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Sandboxed Iframe Container -->
		<div class="relative flex-1 w-full h-full min-h-[220px] bg-white">
			<iframe
				ref="iframeRef"
				class="w-full h-full border-0"
				sandbox="allow-scripts"
				:srcdoc="props.documentContent"
				@load="onIframeLoad"
			></iframe>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
	documentContent: {
		type: String,
		default: '',
	},
})

const emit = defineEmits(['loaded', 'iframeReady'])
const iframeRef = ref(null)

const refresh = () => {
	if (iframeRef.value) {
		const doc = props.documentContent
		iframeRef.value.srcdoc = ''
		setTimeout(() => {
			if (iframeRef.value) {
				iframeRef.value.srcdoc = doc
			}
		}, 50)
	}
}

const onIframeLoad = () => {
	if (iframeRef.value && iframeRef.value.contentDocument) {
		emit('loaded', iframeRef.value.contentDocument)
		emit('iframeReady', iframeRef.value)
	}
}

defineExpose({
	getIframeDocument() {
		return iframeRef.value ? iframeRef.value.contentDocument : null
	},
	refresh,
})
</script>
