<template>
	<div class="relative w-full h-full flex flex-col min-h-[160px] bg-[#1e1e1e] text-white rounded-md overflow-hidden">
		<!-- Top Bar for Editor -->
		<div class="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c] text-xs font-mono select-none">
			<div class="flex items-center space-x-2">
				<span class="font-semibold text-gray-300 uppercase tracking-wider">{{ props.language }}</span>
				<span v-if="props.readOnly" class="bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded text-[10px]">Read-Only</span>
			</div>
			<div class="text-[11px] text-gray-400">
				{{ props.language === 'javascript' ? 'JS' : props.language.toUpperCase() }}
			</div>
		</div>

		<!-- Editor Container -->
		<div ref="editorContainer" class="flex-1 w-full h-full min-h-[140px]"></div>

		<!-- Fallback Textarea if Monaco is loading or failed -->
		<textarea
			v-if="useFallback"
			v-model="codeValue"
			:readonly="props.readOnly"
			class="w-full h-full p-3 font-mono text-xs bg-[#1e1e1e] text-green-400 focus:outline-none resize-none"
			placeholder="Enter code here..."
		></textarea>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
	modelValue: {
		type: String,
		default: '',
	},
	language: {
		type: String,
		default: 'html', // 'html', 'css', 'javascript'
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['update:modelValue', 'change'])

const editorContainer = ref(null)
const useFallback = ref(false)
const codeValue = ref(props.modelValue || '')

let editorInstance = null

watch(() => props.modelValue, (newVal) => {
	if (codeValue.value !== newVal) {
		codeValue.value = newVal || ''
		if (editorInstance) {
			editorInstance.setValue(newVal || '')
		}
	}
})

watch(codeValue, (newVal) => {
	emit('update:modelValue', newVal)
	emit('change', newVal)
})

onMounted(async () => {
	try {
		const monaco = await import('monaco-editor')
		if (!editorContainer.value) return

		editorInstance = monaco.editor.create(editorContainer.value, {
			value: codeValue.value,
			language: props.language === 'js' ? 'javascript' : props.language,
			theme: 'vs-dark',
			automaticLayout: true,
			readOnly: props.readOnly,
			fontSize: 13,
			fontFamily: "'Fira Code', 'Cascadia Code', Consolas, Monaco, monospace",
			minimap: { enabled: false },
			scrollBeyondLastLine: false,
			lineNumbersMinChars: 3,
			tabSize: 2,
			wordWrap: 'on',
			padding: { top: 8, bottom: 8 },
		})

		editorInstance.onDidChangeModelContent(() => {
			const val = editorInstance.getValue()
			codeValue.value = val
		})
	} catch (err) {
		console.warn('Monaco Editor import failed, falling back to textarea editor:', err)
		useFallback.value = true
	}
})

onBeforeUnmount(() => {
	if (editorInstance) {
		editorInstance.dispose()
		editorInstance = null
	}
})
</script>
