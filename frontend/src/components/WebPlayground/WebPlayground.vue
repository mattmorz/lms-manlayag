<template>
	<div class="w-full flex flex-col space-y-4 my-4 font-sans text-ink-gray-9">
		<!-- Header / Title & Instructions -->
		<div v-if="exercise" class="bg-surface-white p-4 border border-outline-gray-2 rounded-lg shadow-sm space-y-2">
			<div class="flex items-center justify-between flex-wrap gap-2">
				<h3 class="text-lg font-bold text-ink-gray-9 flex items-center gap-2">
					<span>{{ exercise.title }}</span>
					<span v-if="userPassed" class="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded font-medium border border-emerald-300">
						✓ {{ __('Passed') }}
					</span>
				</h3>

				<!-- Attempt Counter -->
				<div class="flex items-center space-x-3 text-xs text-ink-gray-6 font-mono">
					<div v-if="exercise.max_attempts && exercise.max_attempts > 0">
						{{ __('Attempts') }}: <span class="font-bold text-ink-gray-9">{{ attemptCount }} / {{ exercise.max_attempts }}</span>
					</div>
					<div v-else>
						{{ __('Attempts') }}: <span class="font-bold text-ink-gray-9">{{ attemptCount }} ({{ __('Unlimited') }})</span>
					</div>
					<div>
						{{ __('Passing Score') }}: <span class="font-bold text-emerald-700">{{ exercise.passing_score }}%</span>
					</div>
				</div>
			</div>

			<!-- Instructions HTML -->
			<div v-if="exercise.instructions" class="prose-sm text-ink-gray-7 mt-2 leading-relaxed" v-html="exercise.instructions"></div>
		</div>

		<!-- Toolbar Actions -->
		<div class="flex items-center justify-between bg-surface-gray-2 p-2.5 border border-outline-gray-2 rounded-lg gap-2 flex-wrap">
			<!-- Tab Switcher for Code Editors -->
			<div class="flex items-center space-x-1 bg-surface-gray-3 p-1 rounded-md">
				<button
					type="button"
					v-for="tab in ['html', 'css', 'js']"
					:key="tab"
					class="px-3 py-1 text-xs font-semibold rounded transition-all uppercase"
					:class="activeEditorTab === tab ? 'bg-surface-white text-ink-gray-9 shadow-sm' : 'text-ink-gray-6 hover:text-ink-gray-9'"
					@click="activeEditorTab = tab"
				>
					{{ tab }}
				</button>
			</div>

			<!-- Action Buttons -->
			<div class="flex items-center space-x-2">
				<Button
					variant="subtle"
					size="sm"
					@click="clearCurrentEditor"
				>
					{{ __('Clear') }}
				</Button>

				<Button
					variant="subtle"
					size="sm"
					@click="confirmReset"
				>
					{{ __('Reset') }}
				</Button>

				<Button
					variant="outline"
					size="sm"
					@click="runCode"
				>
					<template #prefix>
						<svg class="w-3.5 h-3.5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
						</svg>
					</template>
					{{ __('Run') }}
				</Button>

				<Button
					v-if="props.exerciseId"
					variant="solid"
					size="sm"
					:disabled="submitting || isMaxAttemptsReached"
					@click="submitExercise"
				>
					{{ submitting ? __('Submitting...') : __('Submit') }}
				</Button>
			</div>
		</div>

		<!-- Main Workspace Grid: Ace Editors (Left) & Preview / Console (Right) -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
			<!-- Left: Ace Editors -->
			<div class="flex flex-col space-y-2 h-[460px]">
				<AceEditor
					v-show="activeEditorTab === 'html'"
					v-model="htmlCode"
					language="html"
					:read-only="isMaxAttemptsReached"
					@change="onCodeChange"
				/>
				<AceEditor
					v-show="activeEditorTab === 'css'"
					v-model="cssCode"
					language="css"
					:read-only="isMaxAttemptsReached"
					@change="onCodeChange"
				/>
				<AceEditor
					v-show="activeEditorTab === 'js'"
					v-model="jsCode"
					language="javascript"
					:read-only="isMaxAttemptsReached || (exercise && !exercise.allow_javascript)"
					@change="onCodeChange"
				/>
			</div>

			<!-- Right: Live Preview & Console Output -->
			<div class="flex flex-col space-y-3 h-[460px]">
				<div class="flex-1 min-h-0">
					<PreviewFrame
						ref="previewRef"
						:document-content="previewDoc"
						@iframe-ready="onIframeReady"
					/>
				</div>

				<ConsolePanel
					v-if="!exercise || exercise.allow_console"
					:logs="consoleLogs"
					class="h-[140px] shrink-0"
					@clear="consoleLogs = []"
				/>
			</div>
		</div>

		<!-- Bottom: Test Results Panel -->
		<TestResults
			v-if="exercise && exercise.test_cases && exercise.test_cases.length"
			:results="testEvaluation.results"
			:score="testEvaluation.score"
			:earned-points="testEvaluation.earnedPoints"
			:total-points="testEvaluation.totalPoints"
			:passed="testEvaluation.passed"
			:submitted="hasSubmitted"
		/>

		<!-- Submission Limit Warning Banner -->
		<div v-if="isMaxAttemptsReached" class="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-md text-xs">
			<strong>{{ __('Notice:') }}</strong> {{ __('You have reached the maximum allowed attempts ({0}). Further submissions are disabled.').format(exercise.max_attempts) }}
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Button, call, toast } from 'frappe-ui'
import AceEditor from './AceEditor.vue'
import PreviewFrame from './PreviewFrame.vue'
import ConsolePanel from './ConsolePanel.vue'
import TestResults from './TestResults.vue'
import { buildSandboxedDocument, runDomTests } from './playgroundUtils.js'

const props = defineProps({
	exerciseId: {
		type: String,
		default: '',
	},
})

const defaultHtml = `<h1>Hello, Manlayag!</h1>\n\n<p>Welcome to the Web Playground.</p>\n\n<button id="demoButton">Click Me</button>`
const defaultCss = `body {\n    font-family: Arial, sans-serif;\n    padding: 2rem;\n}\n\nh1 {\n    margin-bottom: 0.5rem;\n}\n\nbutton {\n    padding: 0.5rem 1rem;\n    cursor: pointer;\n}`
const defaultJs = `document.getElementById("demoButton").addEventListener("click", () => {\n    alert("Hello from Manlayag!");\n});`

const exercise = ref(null)
const activeEditorTab = ref('html')
const htmlCode = ref(defaultHtml)
const cssCode = ref(defaultCss)
const jsCode = ref(defaultJs)
const previewDoc = ref('')
const consoleLogs = ref([])
const submitting = ref(false)
const hasSubmitted = ref(false)
const attemptCount = ref(0)
const userPassed = ref(false)
const previewRef = ref(null)

const testEvaluation = ref({
	passed: false,
	score: 0,
	earnedPoints: 0,
	totalPoints: 0,
	results: [],
})

let debounceTimer = null

const isMaxAttemptsReached = computed(() => {
	if (!exercise.value || !exercise.value.max_attempts) return false
	return exercise.value.max_attempts > 0 && attemptCount.value >= exercise.value.max_attempts
})

const handleWindowMessage = (event) => {
	if (event.data && event.data.type === 'web_playground_console') {
		const now = new Date()
		const timeStr = now.toTimeString().split(' ')[0]
		consoleLogs.value.push({
			type: event.data.logType || 'log',
			message: event.data.message || '',
			time: timeStr,
		})
	}
}

const loadExercise = () => {
	if (!props.exerciseId) {
		runCode()
		return
	}
	call('lms.lms.api.get_web_playground_exercise', { exercise_id: props.exerciseId })
		.then((res) => {
			exercise.value = res
			attemptCount.value = res.attempt_count || 0
			userPassed.value = !!res.user_passed

			if (res.latest_code) {
				htmlCode.value = res.latest_code.html || ''
				cssCode.value = res.latest_code.css || ''
				jsCode.value = res.latest_code.js || ''
			} else {
				htmlCode.value = res.starter_html || defaultHtml
				cssCode.value = res.starter_css || defaultCss
				jsCode.value = res.starter_js || defaultJs
			}

			runCode()
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
			runCode()
		})
}

const runCode = () => {
	consoleLogs.value = []
	previewDoc.value = buildSandboxedDocument(
		htmlCode.value,
		cssCode.value,
		jsCode.value,
		{
			allowConsole: exercise.value ? exercise.value.allow_console : true,
			allowJs: exercise.value ? exercise.value.allow_javascript : true,
		}
	)

	setTimeout(() => {
		evaluateTests()
	}, 150)
}

const evaluateTests = () => {
	if (!previewRef.value) return
	const doc = previewRef.value.getIframeDocument()
	if (!doc) return
	const testCases = exercise.value ? exercise.value.test_cases || [] : []
	testEvaluation.value = runDomTests(doc, testCases)
}

const onIframeReady = () => {
	evaluateTests()
}

const onCodeChange = () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		if (props.exerciseId) {
			localStorage.setItem(`wpe_draft_${props.exerciseId}`, JSON.stringify({
				html: htmlCode.value,
				css: cssCode.value,
				js: jsCode.value,
			}))
		}
	}, 1500)
}

const clearCurrentEditor = () => {
	if (activeEditorTab.value === 'html') htmlCode.value = ''
	else if (activeEditorTab.value === 'css') cssCode.value = ''
	else if (activeEditorTab.value === 'js') jsCode.value = ''
	runCode()
}

const confirmReset = () => {
	if (confirm(__('Are you sure you want to reset your code? Your current changes will be lost.'))) {
		if (exercise.value) {
			htmlCode.value = exercise.value.starter_html || defaultHtml
			cssCode.value = exercise.value.starter_css || defaultCss
			jsCode.value = exercise.value.starter_js || defaultJs
		} else {
			htmlCode.value = defaultHtml
			cssCode.value = defaultCss
			jsCode.value = defaultJs
		}
		runCode()
		toast.success(__('Code reset to starter template.'))
	}
}

const submitExercise = () => {
	if (!props.exerciseId) return
	if (isMaxAttemptsReached.value) {
		toast.error(__('Maximum attempts reached.'))
		return
	}

	evaluateTests()
	submitting.value = true

	call('lms.lms.api.create_web_playground_submission', {
		exercise: props.exerciseId,
		html_code: htmlCode.value,
		css_code: cssCode.value,
		javascript_code: jsCode.value,
		score: testEvaluation.value.score,
		passed: testEvaluation.value.passed ? 1 : 0,
		test_results: JSON.stringify(testEvaluation.value.results),
	})
		.then((res) => {
			hasSubmitted.value = true
			attemptCount.value = res.attempt_number
			if (res.passed) {
				userPassed.value = true
				toast.success(__('Congratulations! Exercise submitted and passed with {0}% score.').format(res.score))
			} else {
				toast.error(__('Submitted! Score: {0}%. Requirements not fully met.').format(res.score))
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
		})
		.finally(() => {
			submitting.value = false
		})
}

onMounted(() => {
	window.addEventListener('message', handleWindowMessage)
	loadExercise()
})

onBeforeUnmount(() => {
	window.removeEventListener('message', handleWindowMessage)
	clearTimeout(debounceTimer)
})
</script>
