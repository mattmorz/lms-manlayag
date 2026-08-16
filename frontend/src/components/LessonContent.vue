<template>
	<div
		ref="contentRoot"
		:class="
			normalizedHighlightTheme === 'light'
				? 'highlight-theme-light'
				: 'highlight-theme-dark'
		"
	>
		<div v-if="youtube">
			<div
				class="video-player rounded-md border border-gray-100 mb-4"
				:src="youtube"
				data-plyr-provider="youtube"
			></div>
		</div>
		<div v-for="block in content?.split('\n\n')">
			<div v-if="block.includes('{{ YouTubeVideo')">
				<div
					class="video-player rounded-md border border-gray-100 mb-4"
					:src="getId(block)"
					data-plyr-provider="youtube"
				></div>
			</div>
			<div v-else-if="block.includes('{{ Quiz')">
				<Quiz :quiz="getId(block)" />
			</div>
			<div v-else-if="block.includes('{{ Video')">
				<video
					controls
					width="100%"
					controlsList="nodownload"
					oncontextmenu="return false;"
				>
					<source :src="getId(block)" type="video/mp4" />
				</video>
			</div>
			<div v-else-if="block.includes('{{ PDF')">
				<iframe
					:src="getPDFSource(block)"
					width="100%"
					height="700px"
					frameborder="0"
					allowfullscreen
				></iframe>
			</div>
			<div v-else-if="block.includes('{{ Audio')">
				<audio width="100%" controls controlsList="nodownload">
					<source :src="getId(block)" type="audio/mp3" />
				</audio>
			</div>
			<div v-else-if="block.includes('{{ Embed')">
				<iframe
					width="100%"
					height="400"
					:src="getId(block)"
					frameborder="0"
					allowfullscreen
				>
				</iframe>
			</div>
			<div v-else v-html="renderBlockContent(block)"></div>
		</div>
		<div v-if="quizId">
			<Quiz :quiz="quizId" />
		</div>
	</div>
</template>
<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import Quiz from '@/components/QuizBlock.vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import hljsDarkTheme from 'highlight.js/styles/atom-one-dark.css?inline'
import hljsLightTheme from 'highlight.js/styles/atom-one-light.css?inline'
import { useScreenSize } from '@/utils/composables'

const screenSize = useScreenSize()
const contentRoot = ref(null)
const highlightThemeStyleId = 'lesson-highlight-theme-style'

const markdown = new MarkdownIt({
	html: true,
	linkify: true,
})

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
	youtube: {
		type: String,
		required: false,
	},
	quizId: {
		type: String,
		required: false,
	},
	highlightTheme: {
		type: String,
		default: 'dark',
	},
})

const normalizedHighlightTheme = computed(() =>
	props.highlightTheme === 'light' ? 'light' : 'dark'
)

const getYouTubeVideoSource = (block) => {
	if (block.includes('{{')) {
		block = getId(block)
	}
	return `https://www.youtube.com/embed/${block}`
}

const getPDFSource = (block) => {
	return `${getId(block)}#toolbar=0`
}

const renderBlockContent = (block) => {
	if (!block) return ''
	// Pre-process any backticks `code` in the block HTML/text string
	const formatted = block.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>')
	return markdown.render(formatted)
}

const getId = (block) => {
	return block.match(/\(["']([^"']+?)["']\)/)[1]
}

const ensureHighlightTheme = () => {
	const css =
		normalizedHighlightTheme.value === 'light'
			? hljsLightTheme
			: hljsDarkTheme

	let styleEl = document.getElementById(highlightThemeStyleId)
	if (!styleEl) {
		styleEl = document.createElement('style')
		styleEl.setAttribute('id', highlightThemeStyleId)
		document.head?.appendChild(styleEl)
	}

	if (styleEl.textContent !== css) {
		styleEl.textContent = css
	}
}

const applySyntaxHighlighting = async () => {
	await nextTick()
	ensureHighlightTheme()

	if (!contentRoot.value) return
	const codeElements = contentRoot.value.querySelectorAll('pre code')
	codeElements.forEach((el) => {
		if (!el.classList.contains('hljs')) {
			el.classList.add('hljs')
		}
		delete el.dataset.highlighted
		hljs.highlightElement(el)
	})
}

onMounted(() => {
	applySyntaxHighlighting()
})

watch(
	() => [props.content, props.quizId, props.youtube, props.highlightTheme],
	() => {
		applySyntaxHighlighting()
	}
)
</script>

<style scoped>
.highlight-theme-dark :deep(pre code.hljs),

.highlight-theme-dark :deep(pre code.hljs) {
	display: block;
	overflow-x: auto;
	padding: 0.75rem 0.9rem;
	border-radius: 0.35rem;
	background: #282c34;
	color: #abb2bf;
}

.highlight-theme-light :deep(pre code.hljs),

.highlight-theme-light :deep(pre code.hljs) {
	display: block;
	overflow-x: auto;
	padding: 0.75rem 0.9rem;
	border-radius: 0.35rem;
	background: #fafafa;
	color: #383a42;
	border: 1px solid #e5e7eb;
}

:deep(code),
:deep(.inline-code) {
	background-color: #f3f4f6 !important;
	color: #d97706 !important;
	font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
	font-size: 0.875em !important;
	padding: 0.15rem 0.4rem !important;
	border-radius: 0.375rem !important;
	border: 1px solid #e5e7eb !important;
	word-break: break-word !important;
}

:deep(code::before),
:deep(code::after),
:deep(.inline-code::before),
:deep(.inline-code::after) {
	content: "" !important;
}
</style>
