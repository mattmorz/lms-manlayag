<template>
	<div
		ref="contentRoot"
		:class="
			normalizedHighlightTheme === 'light'
				? 'highlight-theme-light'
				: 'highlight-theme-dark'
		"
	>
		<div v-if="props.youtube">
			<div
				class="video-player rounded-md border border-gray-100 mb-4"
				:src="props.youtube"
				data-plyr-provider="youtube"
			></div>
		</div>

		<!-- Render Parsed Editor.js & Markdown Blocks -->
		<div v-for="(block, idx) in parsedBlocks" :key="idx" class="my-2">
			<!-- Web Playground Block -->
			<div v-if="block.type === 'web_playground' && block.exerciseId">
				<WebPlayground :exerciseId="block.exerciseId" />
			</div>

			<!-- Embed Shortcodes (Legacy String Fallback) -->
			<div v-else-if="block.raw && block.raw.includes('{{ YouTubeVideo')">
				<div
					class="video-player rounded-md border border-gray-100 mb-4"
					:src="getId(block.raw)"
					data-plyr-provider="youtube"
				></div>
			</div>
			<div v-else-if="block.raw && block.raw.includes('{{ Quiz')">
				<Quiz :quiz="getId(block.raw)" />
			</div>
			<div v-else-if="block.raw && block.raw.includes('{{ Video')">
				<video
					controls
					width="100%"
					controlsList="nodownload"
					oncontextmenu="return false;"
				>
					<source :src="getId(block.raw)" type="video/mp4" />
				</video>
			</div>
			<div v-else-if="block.raw && block.raw.includes('{{ PDF')">
				<iframe
					:src="getPDFSource(block.raw)"
					width="100%"
					height="700px"
					frameborder="0"
					allowfullscreen
				></iframe>
			</div>
			<div v-else-if="block.raw && block.raw.includes('{{ Audio')">
				<audio width="100%" controls controlsList="nodownload">
					<source :src="getId(block.raw)" type="audio/mp3" />
				</audio>
			</div>
			<div v-else-if="block.raw && block.raw.includes('{{ Embed')">
				<iframe
					width="100%"
					height="400"
					:src="getId(block.raw)"
					frameborder="0"
					allowfullscreen
				></iframe>
			</div>

			<!-- Formatted HTML Block (codeBox, markdown, table, header, list, etc.) -->
			<div v-else v-html="block.html"></div>
		</div>

		<div v-if="props.quizId">
			<Quiz :quiz="props.quizId" />
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import Quiz from '@/components/QuizBlock.vue'
import WebPlayground from '@/components/WebPlayground/WebPlayground.vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import hljsDarkTheme from 'highlight.js/styles/atom-one-dark.css?inline'
import hljsLightTheme from 'highlight.js/styles/atom-one-light.css?inline'
import { useScreenSize } from '@/utils/composables'

const screenSize = useScreenSize()
const contentRoot = ref(null)
const highlightThemeStyleId = 'lesson-highlight-theme-style'

const highlightCode = (str, lang) => {
	let validLang = (lang || 'xml').toLowerCase()
	if (validLang === 'html') validLang = 'xml'
	try {
		if (validLang && hljs.getLanguage(validLang)) {
			return hljs.highlight(str, { language: validLang, ignoreIllegals: true }).value
		}
		return hljs.highlightAuto(str).value
	} catch (e) {
		return String(str)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
	}
}

const markdown = new MarkdownIt({
	html: false,
	linkify: true,
	highlight: (str, lang) => {
		return `<pre class="hljs"><code>${highlightCode(str, lang)}</code></pre>`
	},
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

const renderInlineContent = (text) => {
	if (!text) return ''
	let str = String(text)

	// If str contains backticks `code`, convert backticks to inline code pills
	if (str.includes('`')) {
		const codeBlocks = []
		str = str.replace(/`([^`]+)`/g, (match, p1) => {
			const idx = codeBlocks.length
			const escapedInside = String(p1)
				.replace(/&/g, '&amp;')
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
			codeBlocks.push(`<code class="inline-code">${escapedInside}</code>`)
			return `%%INLINECODE${idx}%%`
		})

		str = str.replace(/%%INLINECODE(\d+)%%/g, (match, p1) => {
			return codeBlocks[parseInt(p1, 10)] || ''
		})
	}

	return str
}

const parsedBlocks = computed(() => {
	if (!props.content) return []

	try {
		const json = JSON.parse(props.content)
		if (json && Array.isArray(json.blocks)) {
			return json.blocks.map((b) => {
				if (b.type === 'codeBox' || b.type === 'code') {
					const code = b.data?.code || b.data?.text || ''
					const lang = (b.data?.language || 'html').toLowerCase()
					const highlightedHtml = highlightCode(code, lang)
					return {
						type: 'codeBox',
						html: `<pre class="hljs"><code class="language-${lang}">${highlightedHtml}</code></pre>`,
					}
				} else if (b.type === 'header') {
					const level = b.data?.level || 2
					const text = b.data?.text || ''
					return {
						type: 'header',
						html: `<h${level}>${renderInlineContent(text)}</h${level}>`,
					}
				} else if (b.type === 'table') {
					const rows = b.data?.content || []
					if (!rows.length) return { type: 'table', html: '' }
					let tableHtml = '<div class="overflow-x-auto my-4"><table>'
					if (b.data?.withHeadings && rows.length > 0) {
						tableHtml +=
							'<thead><tr>' +
							rows[0].map((c) => `<th>${renderInlineContent(c)}</th>`).join('') +
							'</tr></thead>'
						tableHtml +=
							'<tbody>' +
							rows
								.slice(1)
								.map(
									(r) =>
										'<tr>' +
										r.map((c) => `<td>${renderInlineContent(c)}</td>`).join('') +
										'</tr>'
								)
								.join('') +
							'</tbody>'
					} else {
						tableHtml +=
							'<tbody>' +
							rows
								.map(
									(r) =>
										'<tr>' +
										r.map((c) => `<td>${renderInlineContent(c)}</td>`).join('') +
										'</tr>'
								)
								.join('') +
							'</tbody>'
					}
					tableHtml += '</table></div>'
					return { type: 'table', html: tableHtml }
				} else if (b.type === 'paragraph' || b.type === 'markdown') {
					const text = b.data?.text || ''
					return {
						type: 'markdown',
						html: renderInlineContent(text),
					}
				} else if (b.type === 'list') {
					const items = b.data?.items || []
					const tag = b.data?.style === 'ordered' ? 'ol' : 'ul'
					const listHtml =
						`<${tag}>` +
						items
							.map((i) => `<li>${renderInlineContent(i.content || i)}</li>`)
							.join('') +
						`</${tag}>`
					return { type: 'list', html: listHtml }
				} else if (b.type === 'latex') {
					const formula = b.data?.formula || ''
					return {
						type: 'latex',
						html: `<div class="math-block">$$${formula}$$</div>`,
					}
				} else if (b.type === 'web_playground') {
					return {
						type: 'web_playground',
						exerciseId: b.data?.exercise_id || b.data?.exercise,
					}
				}
				return {
					type: b.type,
					html: markdown.render(b.data?.text || JSON.stringify(b.data || {})),
				}
			})
		}
	} catch (e) {
		// Fallback for non-JSON string content
	}

	// Legacy plain text / raw string content split by double newlines
	return props.content.split('\n\n').map((blockStr) => {
		return {
			type: 'markdown',
			html: markdown.render(blockStr),
			raw: blockStr,
		}
	})
})

const getYouTubeVideoSource = (block) => {
	if (block.includes('{{')) {
		block = getId(block)
	}
	return `https://www.youtube.com/embed/${block}`
}

const getPDFSource = (block) => {
	return `${getId(block)}#toolbar=0`
}

const getId = (block) => {
	const match = block.match(/\(["']([^"']+?)["']\)/)
	return match ? match[1] : ''
}

const ensureHighlightTheme = () => {
	const rawCss =
		normalizedHighlightTheme.value === 'light'
			? hljsLightTheme
			: hljsDarkTheme

	const css = typeof rawCss === 'string' ? rawCss : (rawCss?.default || String(rawCss || ''))

	let styleEl = document.getElementById(highlightThemeStyleId)
	if (!styleEl) {
		styleEl = document.createElement('style')
		styleEl.setAttribute('id', highlightThemeStyleId)
		document.head?.appendChild(styleEl)
	}

	if (css && styleEl.textContent !== css) {
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
:deep(pre) {
	margin: 1.25rem 0;
	border-radius: 0.5rem;
	overflow: hidden;
}

:deep(pre code.hljs) {
	display: block;
	overflow-x: auto;
	padding: 1rem 1.25rem;
	border-radius: 0.5rem;
	font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
	font-size: 0.875rem;
	line-height: 1.6;
}

.highlight-theme-dark :deep(pre code.hljs) {
	background: #1e1e1e;
	color: #d4d4d4;
	border: 1px solid #333333;
}

.highlight-theme-light :deep(pre code.hljs) {
	background: #f8fafc;
	color: #0f172a;
	border: 1px solid #e2e8f0;
}
</style>
