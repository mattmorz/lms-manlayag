<template>
	<div class="relative w-full h-full flex flex-col min-h-[180px] bg-[#1e1e1e] text-white rounded-md overflow-hidden border border-[#3c3c3c]">
		<!-- Top Bar for Editor -->
		<div class="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c] text-xs font-mono select-none">
			<div class="flex items-center space-x-2">
				<span class="font-semibold text-gray-300 uppercase tracking-wider">{{ props.language }}</span>
				<span v-if="props.readOnly" class="bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded text-[10px]">Read-Only</span>
			</div>
			<div class="text-[11px] text-gray-400 font-mono">
				Ace Editor
			</div>
		</div>

		<!-- Ace Editor Container -->
		<div ref="editorRef" class="flex-1 w-full h-full min-h-[160px]"></div>

		<!-- Fallback Textarea if Ace fails to mount -->
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

const editorRef = ref(null)
const useFallback = ref(false)
const codeValue = ref(props.modelValue || '')

let aceEditor = null

watch(() => props.modelValue, (newVal) => {
	if (codeValue.value !== newVal) {
		codeValue.value = newVal || ''
		if (aceEditor && aceEditor.getValue() !== codeValue.value) {
			aceEditor.setValue(codeValue.value, 1)
		}
	}
})

watch(codeValue, (newVal) => {
	emit('update:modelValue', newVal)
	emit('change', newVal)
})

onMounted(async () => {
	try {
		const ace = await import('ace-builds')
		await import('ace-builds/src-noconflict/mode-html')
		await import('ace-builds/src-noconflict/mode-css')
		await import('ace-builds/src-noconflict/mode-javascript')
		await import('ace-builds/src-noconflict/theme-twilight')

		if (!editorRef.value) return

		aceEditor = ace.edit(editorRef.value, {
			value: codeValue.value,
			mode: getAceMode(props.language),
			theme: 'ace/theme/twilight',
			readOnly: props.readOnly,
			fontSize: 13,
			showPrintMargin: false,
			useSoftTabs: true,
			tabSize: 2,
			wrap: true,
			highlightActiveLine: true,
			displayIndentGuides: true,
		})

		aceEditor.on('change', () => {
			const val = aceEditor.getValue()
			if (codeValue.value !== val) {
				codeValue.value = val
			}
		})
	} catch (err) {
		console.warn('Ace Editor initialization failed, falling back to textarea:', err)
		useFallback.value = true
	}
})

function getAceMode(lang) {
	const l = (lang || '').toLowerCase()
	if (l === 'html') return 'ace/mode/html'
	if (l === 'css') return 'ace/mode/css'
	if (l === 'js' || l === 'javascript') return 'ace/mode/javascript'
	return 'ace/mode/html'
}

onBeforeUnmount(() => {
	if (aceEditor) {
		aceEditor.destroy()
		aceEditor = null
	}
})
</script>
