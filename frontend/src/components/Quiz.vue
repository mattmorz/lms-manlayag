<template>
	<div v-if="quiz.data" :class="[isFullscreenActive ? 'max-w-3xl mx-auto px-6 py-10 bg-surface-gray-1 border rounded-lg shadow-sm mt-10' : '']">
		<!-- PROCTOR MODE BANNER -->
		<div
			v-if="isProctorEnabled"
			class="bg-surface-gray-2/80 backdrop-blur-md border border-red-500/30 rounded-lg p-3.5 mb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 shadow-sm"
		>
			<div class="flex items-center gap-2.5">
				<div class="flex h-2.5 w-2.5 relative">
					<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
					<span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
				</div>
				<div>
					<span class="font-bold text-red-600 dark:text-red-400 tracking-wider text-xs uppercase block sm:inline mr-2">
						{{ __('Proctor Mode Enabled') }}
					</span>
					<span class="text-[11px] text-ink-gray-6">
						{{ __('Tabs, windows, and cheating keyboard shortcuts are strictly monitored.') }}
					</span>
				</div>
			</div>
			<div v-if="activeQuestion > 0 && !quizSubmission.data" class="flex items-center gap-1.5 self-end sm:self-auto">
				<Badge
					variant="subtle"
					theme="red"
					size="sm"
					:label="__('{0} of {1} Warnings Used').format(proctorWarnings, maxProctorWarnings)"
				/>
			</div>
		</div>

		<!-- FULLSCREEN RE-ENTRY OVERLAY -->
		<div
			v-if="activeQuestion > 0 && !quizSubmission.data && isProctorEnabled && !isFullscreenActive"
			class="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col items-center justify-center text-center p-6"
		>
			<div class="max-w-md w-full bg-surface-gray-1 border border-outline-gray-3 rounded-2xl p-8 shadow-2xl space-y-6 relative overflow-hidden">
				<!-- Top decorative threat/secure pattern -->
				<div class="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-red-500 via-amber-500 to-red-500"></div>
				
				<div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-red-50 dark:bg-red-950/30 border-2 border-red-500/20 shadow-inner">
					<Lock class="h-10 w-10 text-red-600 dark:text-red-500 animate-bounce" />
				</div>
				<div class="space-y-3">
					<h3 class="text-2xl font-black text-ink-gray-9 tracking-tight">
						{{ __('Secure Session Paused') }}
					</h3>
					<p class="text-sm text-ink-gray-6 leading-relaxed">
						{{ __('To protect the integrity of this quiz, you must remain in Fullscreen mode. Exiting fullscreen or navigating away counts as a violation.') }}
					</p>
				</div>
				
				<div class="bg-surface-gray-2/60 border border-outline-gray-2 rounded-xl p-4 text-sm flex items-center justify-between shadow-sm">
					<span class="text-ink-gray-7 font-medium">{{ __('Violation Count') }}:</span>
					<div class="flex items-center gap-1.5">
						<span class="font-bold text-red-600 dark:text-red-400">
							{{ proctorWarnings }}
						</span>
						<span class="text-ink-gray-4">/</span>
						<span class="text-ink-gray-5">{{ maxProctorWarnings }}</span>
						<span class="text-xs text-ink-gray-6">({{ __('max') }})</span>
					</div>
				</div>

				<Button
					variant="solid"
					class="w-full flex justify-center py-3 font-bold text-base shadow-md hover:shadow-lg transition-all animate-pulse"
					@click="enterFullscreen"
				>
					{{ __('Return to Fullscreen') }}
				</Button>
			</div>
		</div>

		<div
			v-if="!(isPassed && isCheckpointQuiz)"
			class="bg-surface-blue-2 space-y-2 py-2 px-3 mb-4 rounded-md text-sm text-ink-blue-2 leading-5"
		>
			<div v-if="inVideo">
				{{ __('You will have to complete the quiz to continue the video') }}
			</div>
			<div v-if="isCheckpointQuiz && !inVideo" class="leading-5 font-semibold">
				<span v-if="isLoggedIn">
					{{ __('Complete the checkpoint quiz to unlock the next section.') }}
				</span>
				<span v-else>
					{{ __('Remaining lessons can be accessed after answering a checkpoint quiz.') }}
				</span>
			</div>
			<div class="leading-5">
				{{
					__('This quiz consists of {0} questions.').format(questions.length)
				}}
			</div>
			<div v-if="quiz.data?.duration" class="leading-5">
				{{
					__(
						'Please ensure that you complete all the questions in {0} minutes.'
					).format(quiz.data.duration)
				}}
			</div>
			<div v-if="quiz.data?.duration" class="leading-5">
				{{
					__(
						'If you fail to do so, the quiz will be automatically submitted when the timer ends.'
					)
				}}
			</div>
			<div v-if="quiz.data.passing_percentage" class="leading-relaxed">
				{{
					__(
						'You will have to get {0}% correct answers in order to pass the quiz.'
					).format(quiz.data.passing_percentage)
				}}
			</div>
			<div v-if="quiz.data.max_attempts" class="leading-5">
				{{
					__('You can attempt this quiz {0}.').format(
						quiz.data.max_attempts == 1
							? '1 time'
							: `${quiz.data.max_attempts} times`
					)
				}}
			</div>
			<div v-if="quiz.data.enable_negative_marking" class="leading-5">
				{{
					__(
						'If you answer incorrectly, {0} {1} will be deducted from your score for each incorrect answer.'
					).format(
						quiz.data.marks_to_cut,
						quiz.data.marks_to_cut == 1 ? 'mark' : 'marks'
					)
				}}
			</div>
		</div>

		<div v-if="quiz.data.duration" class="flex flex-col space-x-1 my-4">
			<div class="mb-2">
				<span class="text-ink-gray-9"> {{ __('Time') }}: </span>
				<span class="font-semibold text-ink-gray-9">
					{{ formatTimer(timer) }}
				</span>
			</div>
			<ProgressBar :progress="timerProgress" />
		</div>

		<div v-if="isPassed && isCheckpointQuiz" class="border rounded-md p-5 space-y-4">
			<div class="flex items-center justify-between gap-2">
				<div class="font-semibold text-lg text-ink-gray-9">
					{{ quiz.data.title }}
				</div>
				<div class="flex items-center gap-2">
					<Badge theme="green" variant="subtle" :label="__('Passed')">
						<template #prefix>
							<CheckCircle class="w-4 h-4 text-ink-green-2 mr-1" />
						</template>
					</Badge>
					<Button
						variant="ghost"
						class="text-ink-gray-7 hover:text-ink-gray-9 text-xs"
						@click="showSavedQuestions = !showSavedQuestions"
					>
						{{ showSavedQuestions ? __('Hide Questions') : __('Show Questions') }}
					</Button>
				</div>
			</div>
			<div v-if="showSavedQuestions" class="space-y-3">
				<div
					v-for="(question, index) in questions"
					:key="question.question || index"
					class="rounded-md border border-outline-gray-2 bg-surface-gray-2 p-4"
				>
					<div class="text-sm font-semibold text-ink-gray-9" v-html="question.question_detail || question.question"></div>
					<div class="mt-2 text-sm text-ink-gray-7">
						<span class="font-medium text-ink-gray-9">{{ __('Answer') }}:</span>
						<span class="ml-1">{{ getSavedAnswer(question.question) || __('No answer recorded') }}</span>
					</div>
				</div>
			</div>
		</div>

		<div v-else-if="activeQuestion == 0">
			<div class="border text-center p-20 rounded-md">
				<div class="font-semibold text-lg text-ink-gray-9">
					{{ quiz.data.title }}
				</div>
				<div v-if="quiz.data.due_date" class="mt-2 text-sm text-ink-gray-6">
					<strong>{{ __('Due Date') }}:</strong> {{ quiz.data.due_date }} {{ quiz.data.due_time || '' }}
				</div>
				<div v-if="quiz.data.due_date && isLateAttempt" class="mt-2 text-sm text-ink-red-3 font-semibold">
					{{ __('Warning: The deadline has passed. Late submissions will receive 0 marks.') }}
				</div>
				<div class="flex items-center justify-center space-x-2 mt-4">
					<Button
						v-if="
							isLoggedIn && (!quiz.data.max_attempts ||
							attempts.data?.length < quiz.data.max_attempts)
						"
						variant="solid"
						@click="startQuiz"
					>
						<span>
							{{ inVideo ? __('Start the Quiz') : __('Start') }}
						</span>
					</Button>
					<Button
						v-else-if="!isLoggedIn"
						variant="solid"
						@click="redirectToLogin"
					>
						<span>
							{{ __('Log In to Start') }}
						</span>
					</Button>
					<Button v-if="inVideo && (!enforcePass || isPassed)" @click="props.backToVideo()">
						{{ __('Resume Video') }}
					</Button>
				</div>
				<div
					v-if="
						quiz.data.max_attempts &&
						attempts.data?.length >= quiz.data.max_attempts
					"
					class="leading-5 text-ink-gray-7"
				>
					{{
						__(
							'You have already exceeded the maximum number of attempts allowed for this quiz.'
						)
					}}
				</div>
			</div>
		</div>
		<div v-else-if="!quizSubmission.data">
			<div v-for="(question, qtidx) in questions">
				<div
					v-if="qtidx == activeQuestion - 1 && questionDetails.data"
					class="border rounded-md p-5"
					:class="{ 'proctor-no-select': isIncludedInGrading }"
				>
					<div class="flex justify-between">
						<div class="text-sm text-ink-gray-5">
							<span class="mr-2">
								{{ __('Question {0}').format(activeQuestion) }}:
							</span>
							<span>
								{{ getInstructions(questionDetails.data) }}
							</span>
						</div>
						<div class="text-ink-gray-9 text-sm font-semibold item-left">
							{{ question.marks }}
							{{ question.marks == 1 ? __('Mark') : __('Marks') }}
						</div>
					</div>
					<div
						class="text-ink-gray-9 font-semibold mt-2 leading-5"
						v-html="questionDetails.data.question"
					></div>
					<div v-if="questionDetails.data.type == 'Choices'" v-for="index in 4">
						<label
							v-if="questionDetails.data[`option_${index}`]"
							class="flex items-center bg-surface-gray-3 rounded-md p-3 mt-4 w-full cursor-pointer focus:border-blue-600"
						>
							<input
								v-if="!showAnswers.length && !questionDetails.data.multiple"
								type="radio"
								:name="encodeURIComponent(questionDetails.data.question)"
								class="w-3.5 h-3.5 text-ink-gray-9 focus:ring-outline-gray-modals"
								@change="markAnswer(index)"
							/>

							<input
								v-else-if="!showAnswers.length && questionDetails.data.multiple"
								type="checkbox"
								:name="encodeURIComponent(questionDetails.data.question)"
								class="w-3.5 h-3.5 text-ink-gray-9 rounded-sm focus:ring-outline-gray-modals"
								@change="markAnswer(index)"
							/>
							<div
								v-else-if="quiz.data.show_answers"
								v-for="(answer, idx) in showAnswers"
							>
								<div v-if="index - 1 == idx">
									<CheckCircle
										v-if="answer == 1"
										class="w-4 h-4 text-ink-green-2"
									/>
									<MinusCircle
										v-else-if="answer == 2"
										class="w-4 h-4 text-ink-green-2"
									/>
									<XCircle
										v-else-if="answer == 0"
										class="w-4 h-4 text-ink-red-3"
									/>
									<MinusCircle v-else class="w-4 h-4" />
								</div>
							</div>
							<span
								class="ml-2 text-ink-gray-9"
								v-html="questionDetails.data[`option_${index}`]"
							>
							</span>
						</label>
						<div
							v-if="questionDetails.data[`explanation_${index}`]"
							class="mt-2 text-xs text-ink-gray-7"
							v-show="showAnswers.length"
						>
							{{ questionDetails.data[`explanation_${index}`] }}
						</div>
					</div>
					<div v-else-if="questionDetails.data.type == 'User Input'">
						<FormControl
							v-model="possibleAnswer"
							type="textarea"
							:disabled="showAnswers.length ? true : false"
							class="my-2"
						/>
						<div v-if="showAnswers.length">
							<Badge v-if="showAnswers[0]" :label="__('Correct')" theme="green">
								<template #prefix>
									<CheckCircle class="w-4 h-4 text-ink-green-2 mr-1" />
								</template>
							</Badge>
							<Badge v-else theme="red" :label="__('Incorrect')">
								<template #prefix>
									<XCircle class="w-4 h-4 text-ink-red-3 mr-1" />
								</template>
							</Badge>
						</div>
					</div>
					<div v-else>
						<TextEditor
							class="mt-4"
							:content="possibleAnswer"
							@change="(val) => (possibleAnswer = val)"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
						/>
					</div>
					<div class="flex items-center justify-between mt-4">
						<div class="text-sm text-ink-gray-5">
							{{
								__('Question {0} of {1}').format(
									activeQuestion,
									questions.length
								)
							}}
						</div>
						<Button
							v-if="
								quiz.data.show_answers &&
								!showAnswers.length &&
								questionDetails.data.type != 'Open Ended'
							"
							@click="checkAnswer()"
						>
							<span>
								{{ __('Check') }}
							</span>
						</Button>
						<Button
							v-else-if="activeQuestion != questions.length"
							@click="nextQuestion()"
						>
							<span>
								{{ __('Next') }}
							</span>
						</Button>
						<Button v-else @click="submitQuiz()">
							<span>
								{{ __('Submit') }}
							</span>
						</Button>
					</div>
				</div>
			</div>
		</div>
		<div v-else class="border rounded-md p-20 text-center space-y-2">
			<div class="text-lg font-semibold text-ink-gray-9">
				{{ __('Quiz Summary') }}
			</div>
			<div
				v-if="quizSubmission.data.is_open_ended"
				class="leading-5 text-ink-gray-7"
			>
				{{
					__(
						"Your submission has been successfully saved. The instructor will review and grade it shortly, and you'll be notified of your final result."
					)
				}}
			</div>
			<div v-else class="text-ink-gray-7">
				{{
					__(
						'You got {0}% correct answers with a score of {1} out of {2}'
					).format(
						Math.ceil(quizSubmission.data.percentage),
						quizSubmission.data.score,
						quizSubmission.data.score_out_of
					)
				}}
			</div>
			<div class="space-x-2 flex items-center justify-center flex-wrap">
				<Button
					@click="resetQuiz()"
					class="mt-2"
					v-if="
						!quiz.data.max_attempts ||
						attempts?.data.length < quiz.data.max_attempts
					"
				>
					<span>
						{{ __('Try Again') }}
					</span>
				</Button>
				<Button
					v-if="isPassed && hasNextLesson && !isCheckpointQuiz && isIncludedInGrading"
					variant="solid"
					class="mt-2"
					@click="proceedToNextLesson"
				>
					<span>
						{{ nextLessonLabel }}
					</span>
				</Button>
				<Button v-if="inVideo && (!enforcePass || isPassed)" class="mt-2" @click="props.backToVideo()">
					{{ __('Resume Video') }}
				</Button>
			</div>
		</div>
		<div
			v-if="
				quiz.data.show_submission_history &&
				attempts?.data &&
				attempts.data.length > 0
			"
			class="mt-10"
		>
			<ListView
				:columns="getSubmissionColumns()"
				:rows="attempts?.data"
				row-key="name"
				:options="{
					selectable: false,
					showTooltip: false,
					emptyState: { title: __('No Quiz submissions found') },
				}"
			>
			</ListView>
		</div>

		<!-- PROCTOR WARNING DIALOG -->
		<Dialog
			v-model="showProctorWarningModal"
			:options="{
				title: __('Proctor Warning'),
				size: 'sm',
				actions: [
					{
						label: __('I Understand'),
						variant: 'solid',
						onClick: (close) => {
							close()
						},
					},
				],
			}"
		>
			<template #body-content>
				<div class="space-y-4">
					<div class="text-sm text-ink-gray-7">
						{{ __('A proctoring violation has been detected:') }}
						<div class="mt-2 p-3 bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-400 font-semibold rounded-md flex items-center gap-2">
							<span class="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
							{{ lastWarningReason }}
						</div>
					</div>
					<div class="text-sm text-ink-gray-7 leading-relaxed">
						{{ __('Please remain in fullscreen and focus on the quiz. If you reach {0} warnings, your quiz will be automatically submitted.').format(maxProctorWarnings) }}
					</div>
					<div class="bg-surface-gray-2 border border-outline-gray-2 rounded-lg p-3 text-sm flex items-center justify-between">
						<span class="text-ink-gray-7">{{ __('Warnings Recorded') }}:</span>
						<span class="font-bold text-red-600">
							{{ proctorWarnings }} / {{ maxProctorWarnings }}
						</span>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import {
	Badge,
	Button,
	call,
	createResource,
	ListView,
	TextEditor,
	FormControl,
	toast,
	Dialog,
} from 'frappe-ui'
import { ref, watch, reactive, inject, computed, onMounted, onBeforeUnmount } from 'vue'
import { CheckCircle, XCircle, MinusCircle, Lock } from 'lucide-vue-next'
import { timeAgo } from '@/utils'
import { useRouter } from 'vue-router'
import ProgressBar from '@/components/ProgressBar.vue'
import { usersStore } from '@/stores/user'

const user = inject('$user') || usersStore().userResource
const activeQuestion = ref(0)
const currentQuestion = ref('')
const selectedOptions = reactive([0, 0, 0, 0])
const showAnswers = reactive([])
let questions = reactive([])
const possibleAnswer = ref(null)
const showSavedQuestions = ref(true)
const timer = ref(0)
let timerInterval = null

const isCheckpointQuiz = computed(() => {
	return props.isCheckpoint || new URLSearchParams(window.location.search).get('checkpoint') === '1'
})

const isIncludedInGrading = computed(() => {
	return new URLSearchParams(window.location.search).get('grading') === '1'
})

const isLoggedIn = computed(() => {
	return !!user.data
})

const redirectToLogin = () => {
	window.top.location.href = '/login'
}

const hasNextLesson = computed(() => {
	return window.parent && !!window.parent.currentLessonNext
})

const nextLessonLabel = computed(() => {
	return window.parent && window.parent.isAssessmentMode
		? __('Proceed to Next Activity')
		: __('Proceed to Next Lesson')
})

const proceedToNextLesson = () => {
	if (window.parent && window.parent.dispatchEvent) {
		window.parent.dispatchEvent(new Event('lms-lesson-next-trigger'))
	}
}

const isFullscreenActive = ref(false)
const proctorWarnings = ref(0)

const isProctorEnabled = computed(() => {
	const proctorParam = new URLSearchParams(window.location.search).get('proctor')
	if (proctorParam === '0') {
		return false
	}
	return isIncludedInGrading.value
})

const maxProctorWarnings = computed(() => {
	const warningsParam = new URLSearchParams(window.location.search).get('warnings')
	return warningsParam ? parseInt(warningsParam, 10) : 3
})

const showProctorWarningModal = ref(false)
const lastWarningReason = ref('')

const enterFullscreen = () => {
	const elem = document.documentElement
	if (elem.requestFullscreen) {
		elem.requestFullscreen()
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen()
	} else if (elem.mozRequestFullScreen) {
		elem.mozRequestFullScreen()
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen()
	}
}

const handleFullscreenChange = () => {
	const isCurrentlyFullscreen = !!(
		document.fullscreenElement ||
		document.webkitFullscreenElement ||
		document.mozFullScreenElement ||
		document.msFullscreenElement
	)
	isFullscreenActive.value = isCurrentlyFullscreen
	
	if (activeQuestion.value > 0 && !quizSubmission.data && isProctorEnabled.value && !isCurrentlyFullscreen) {
		triggerProctorViolation(__('Exited Fullscreen Mode'))
	}
}

const handleVisibilityChange = () => {
	if (document.hidden && activeQuestion.value > 0 && !quizSubmission.data && isProctorEnabled.value) {
		triggerProctorViolation(__('Switched Tab/Minimized Window'))
	}
}

const handleWindowBlur = () => {
	if (activeQuestion.value > 0 && !quizSubmission.data && isProctorEnabled.value) {
		triggerProctorViolation(__('Lost Window Focus'))
	}
}

const preventCheatInputs = (e) => {
	if (activeQuestion.value > 0 && !quizSubmission.data && isProctorEnabled.value) {
		if (e.type === 'copy' || e.type === 'cut' || e.type === 'paste' || e.type === 'contextmenu') {
			e.preventDefault()
			toast.warning(__('Copy/cut/paste and right-click are disabled in Proctor Mode.'))
			return false
		}
		if (e.type === 'keydown') {
			const isCtrl = e.ctrlKey || e.metaKey
			const isShift = e.shiftKey
			
			if (
				e.key === 'F12' ||
				(isCtrl && isShift && (e.key === 'I' || e.key === 'C' || e.key === 'J')) ||
				(isCtrl && e.key === 'u') ||
				(isCtrl && e.key === 'c') ||
				(isCtrl && e.key === 'v')
			) {
				e.preventDefault()
				toast.warning(__('This shortcut is disabled in Proctor Mode.'))
				return false
			}
		}
	}
}

let lastViolationTime = 0

const triggerProctorViolation = (reason) => {
	const now = Date.now()
	if (now - lastViolationTime < 1000) {
		return
	}
	lastViolationTime = now

	proctorWarnings.value++
	lastWarningReason.value = reason
	
	if (proctorWarnings.value >= maxProctorWarnings) {
		cleanupProctorListeners()
		showProctorWarningModal.value = false
		toast.error(__('Quiz automatically submitted due to multiple proctor violations.'))
		submitQuiz()
		if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement) {
			if (document.exitFullscreen) {
				document.exitFullscreen().catch(() => {})
			} else if (document.webkitExitFullscreen) {
				document.webkitExitFullscreen()
			} else if (document.mozCancelFullScreen) {
				document.mozCancelFullScreen()
			} else if (document.msExitFullscreen) {
				document.msExitFullscreen()
			}
		}
	} else {
		showProctorWarningModal.value = true
	}
}

let proctorListenersAttached = false

const setupProctorListeners = () => {
	if (!isProctorEnabled.value || proctorListenersAttached) return
	
	document.addEventListener('fullscreenchange', handleFullscreenChange)
	document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
	document.addEventListener('mozfullscreenchange', handleFullscreenChange)
	document.addEventListener('MSFullscreenChange', handleFullscreenChange)
	
	document.addEventListener('visibilitychange', handleVisibilityChange)
	window.addEventListener('blur', handleWindowBlur)
	
	document.addEventListener('copy', preventCheatInputs)
	document.addEventListener('cut', preventCheatInputs)
	document.addEventListener('paste', preventCheatInputs)
	document.addEventListener('contextmenu', preventCheatInputs)
	document.addEventListener('keydown', preventCheatInputs)
	
	proctorListenersAttached = true
}

const cleanupProctorListeners = () => {
	if (!proctorListenersAttached) return
	
	document.removeEventListener('fullscreenchange', handleFullscreenChange)
	document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
	document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
	document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
	
	document.removeEventListener('visibilitychange', handleVisibilityChange)
	window.removeEventListener('blur', handleWindowBlur)
	
	document.removeEventListener('copy', preventCheatInputs)
	document.removeEventListener('cut', preventCheatInputs)
	document.removeEventListener('paste', preventCheatInputs)
	document.removeEventListener('contextmenu', preventCheatInputs)
	document.removeEventListener('keydown', preventCheatInputs)
	
	proctorListenersAttached = false
}

onBeforeUnmount(() => {
	cleanupProctorListeners()
})

onMounted(() => {
	if (window.frameElement) {
		const resizeObserver = new ResizeObserver(() => {
			const height = document.documentElement.scrollHeight || document.body.scrollHeight
			window.frameElement.style.height = `${height}px`
		})
		resizeObserver.observe(document.body)
	}
})

const props = defineProps({
	quizName: {
		type: String,
		required: true,
	},
	inVideo: {
		type: Boolean,
		default: false,
	},
	enforcePass: {
		type: Boolean,
		default: false,
	},
	backToVideo: {
		type: Function,
		default: () => {},
	},
	isCheckpoint: {
		type: Boolean,
		default: false,
	},
})

const isPassed = computed(() => {
	const passingPercent = quiz.data?.passing_percentage || 0
	if (quizSubmission.data && Math.ceil(quizSubmission.data.percentage) >= passingPercent) {
		return true
	}
	if (attempts.data && attempts.data.length > 0) {
		return attempts.data.some(att => Math.ceil(att.percentage) >= passingPercent)
	}
	return false
})

const savedResponses = computed(() => {
	if (!quiz.data?.title) {
		return []
	}
	try {
		return JSON.parse(localStorage.getItem(quiz.data.title) || '[]')
	} catch {
		return []
	}
})

const getSavedAnswer = (questionName) => {
	const response = savedResponses.value.find((item) => item.question_name === questionName)
	return response?.answer || ''
}

const isLateAttempt = computed(() => {
	if (!quiz.data?.due_date) return false
	const dueTimeStr = quiz.data.due_time || '23:59:59'
	const dueDatetime = new Date(`${quiz.data.due_date}T${dueTimeStr}`)
	return new Date() > dueDatetime
})

const quiz = createResource({
	url: 'frappe.client.get',
	makeParams(values) {
		return {
			doctype: 'LMS Quiz',
			name: props.quizName,
		}
	},
	cache: ['quiz', props.quizName],
	auto: true,
	transform(data) {
		data.duration = parseInt(data.duration)
	},
	onSuccess(data) {
		populateQuestions()
		setupTimer()
	},
})

const populateQuestions = () => {
	let data = quiz.data
	if (data.shuffle_questions) {
		questions = shuffleArray(data.questions)
		if (data.limit_questions_to) {
			questions = questions.slice(0, data.limit_questions_to)
		}
	} else {
		questions = data.questions
	}
}

const setupTimer = () => {
	if (quiz.data.duration) {
		timer.value = quiz.data.duration * 60
	}
}

const startTimer = () => {
	timerInterval = setInterval(() => {
		timer.value--
		if (timer.value == 0) {
			clearInterval(timerInterval)
			submitQuiz()
		}
	}, 1000)
}

const formatTimer = (seconds) => {
	const hrs = Math.floor(seconds / 3600)
		.toString()
		.padStart(2, '0')
	const mins = Math.floor((seconds % 3600) / 60)
		.toString()
		.padStart(2, '0')
	const secs = (seconds % 60).toString().padStart(2, '0')
	return hrs != '00' ? `${hrs}:${mins}:${secs}` : `${mins}:${secs}`
}

const timerProgress = computed(() => {
	return (timer.value / (quiz.data.duration * 60)) * 100
})

const shuffleArray = (array) => {
	for (let i = array.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1))
		;[array[i], array[j]] = [array[j], array[i]]
	}
	return array
}

const attempts = createResource({
	url: 'frappe.client.get_list',
	makeParams(values) {
		return {
			doctype: 'LMS Quiz Submission',
			filters: {
				member: user.data?.name,
				quiz: quiz.data?.name,
			},
			fields: [
				'name',
				'creation',
				'score',
				'score_out_of',
				'percentage',
				'passing_percentage',
			],
			order_by: 'creation desc',
		}
	},
	transform(data) {
		data.forEach((submission, index) => {
			submission.creation = timeAgo(submission.creation)
			submission.idx = index + 1
		})
	},
})

watch(
	() => quiz.data,
	() => {
		if (quiz.data) {
			populateQuestions()
			if (isLoggedIn.value) {
				attempts.reload()
			}
		}
		if (quiz.data && quiz.data.max_attempts) {
			resetQuiz()
		}
	}
)

const quizSubmission = createResource({
	url: 'lms.lms.doctype.lms_quiz.lms_quiz.quiz_summary',
	makeParams(values) {
		return {
			quiz: quiz.data.name,
			results: localStorage.getItem(quiz.data.title),
		}
	},
})

const questionDetails = createResource({
	url: 'lms.lms.utils.get_question_details',
	makeParams(values) {
		return {
			question: currentQuestion.value,
		}
	},
})

watch(activeQuestion, (value) => {
	if (value > 0) {
		currentQuestion.value = quiz.data.questions[value - 1].question
		questionDetails.reload()
	}
})

watch(
	() => props.quizName,
	(newName) => {
		if (newName) {
			quiz.reload()
		}
	}
)

const startQuiz = () => {
	activeQuestion.value = 1
	localStorage.removeItem(quiz.data.title)
	if (quiz.data.duration) startTimer()
	if (isProctorEnabled.value) {
		proctorWarnings.value = 0
		enterFullscreen()
		setupProctorListeners()
	}
}

const markAnswer = (index) => {
	if (!questionDetails.data.multiple)
		selectedOptions.splice(0, selectedOptions.length, ...[0, 0, 0, 0])
	selectedOptions[index - 1] = selectedOptions[index - 1] ? 0 : 1
}

const getAnswers = () => {
	let answers = []
	const type = questionDetails.data.type

	if (type == 'Choices') {
		selectedOptions.forEach((value, index) => {
			if (selectedOptions[index])
				answers.push(questionDetails.data[`option_${index + 1}`])
		})
	} else {
		answers.push(possibleAnswer.value)
	}

	return answers
}

const checkAnswer = () => {
	let answers = getAnswers()
	if (!answers.length) {
		toast.warning(__('Please select an option'))
		return
	}

	createResource({
		url: 'lms.lms.doctype.lms_quiz.lms_quiz.check_answer',
		params: {
			question: currentQuestion.value,
			type: questionDetails.data.type,
			answers: JSON.stringify(answers),
		},
		auto: true,
		onSuccess(data) {
			let type = questionDetails.data.type
			if (type == 'Choices') {
				selectedOptions.forEach((option, index) => {
					if (option) {
						showAnswers[index] = option && data[index]
					} else if (data[index] == 2) {
						showAnswers[index] = 2
					} else {
						showAnswers[index] = undefined
					}
				})
			} else {
				showAnswers.push(data)
			}
			addToLocalStorage()
			if (!quiz.data.show_answers) {
				resetQuestion()
			}
		},
	})
}

const addToLocalStorage = () => {
	let quizData = JSON.parse(localStorage.getItem(quiz.data.title))
	let questionData = {
		question_name: currentQuestion.value,
		answer: getAnswers().join(),
		is_correct: showAnswers.filter((answer) => {
			return answer != undefined
		}),
	}

	if (quizData) {
		let existingQuestion = quizData.find(
			(q) => q.question_name == questionData.question_name
		)
		if (!existingQuestion) {
			quizData.push(questionData)
		}
	} else {
		quizData = [questionData]
	}
	localStorage.setItem(quiz.data.title, JSON.stringify(quizData))
}

const nextQuestion = () => {
	if (!quiz.data.show_answers && questionDetails.data?.type != 'Open Ended') {
		checkAnswer()
	} else {
		if (questionDetails.data?.type == 'Open Ended') addToLocalStorage()
		resetQuestion()
	}
}

const resetQuestion = () => {
	if (activeQuestion.value == quiz.data.questions.length) return
	activeQuestion.value = activeQuestion.value + 1
	selectedOptions.splice(0, selectedOptions.length, ...[0, 0, 0, 0])
	showAnswers.length = 0
	possibleAnswer.value = null
}

const submitQuiz = () => {
	if (!quiz.data.show_answers) {
		if (questionDetails.data.type == 'Open Ended') addToLocalStorage()
		else checkAnswer()
		setTimeout(() => {
			createSubmission()
		}, 500)
		return
	}
	createSubmission()
}

const createSubmission = () => {
	if (isProctorEnabled.value) {
		cleanupProctorListeners()
		if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement) {
			if (document.exitFullscreen) {
				document.exitFullscreen().catch(() => {})
			} else if (document.webkitExitFullscreen) {
				document.webkitExitFullscreen()
			} else if (document.mozCancelFullScreen) {
				document.mozCancelFullScreen()
			} else if (document.msExitFullscreen) {
				document.msExitFullscreen()
			}
		}
	}
	quizSubmission.submit(
		{},
		{
			onSuccess(data) {
				markLessonProgress()
				if (!props.inVideo) {
					window.dispatchEvent(new Event('lms-lesson-quiz-passed'))
					if (window.parent && window.parent !== window) {
						window.parent.dispatchEvent(new Event('lms-lesson-quiz-passed'))
					}
				}
				attempts.reload()
				if (quiz.data.duration) clearInterval(timerInterval)
			},
			onError(err) {
				const errorTitle = err?.message || ''
				if (errorTitle.includes('MaximumAttemptsExceededError')) {
					const errorMessage = err.messages?.[0] || err
					toast.error(__(errorMessage))
					setTimeout(() => {
						window.location.reload()
					}, 3000)
				}
			},
		}
	)
}

const resetQuiz = () => {
	if (isProctorEnabled.value) {
		cleanupProctorListeners()
		if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement) {
			if (document.exitFullscreen) {
				document.exitFullscreen().catch(() => {})
			} else if (document.webkitExitFullscreen) {
				document.webkitExitFullscreen()
			} else if (document.mozCancelFullScreen) {
				document.mozCancelFullScreen()
			} else if (document.msExitFullscreen) {
				document.msExitFullscreen()
			}
		}
	}
	activeQuestion.value = 0
	selectedOptions.splice(0, selectedOptions.length, ...[0, 0, 0, 0])
	showAnswers.length = 0
	quizSubmission.reset()
	populateQuestions()
	setupTimer()
}

const getInstructions = (question) => {
	if (question.type == 'Choices')
		if (question.multiple) return __('Choose all answers that apply')
		else return __('Choose one answer')
	else return __('Type your answer')
}

const markLessonProgress = () => {
	let pathname = window.location.pathname.split('/')
	if (!pathname.includes('courses'))
		pathname = window.parent.location.pathname.split('/')
	if (pathname[2] != 'courses') return
	let lessonIndex = pathname.pop().split('-')

	if (lessonIndex.length == 2) {
		call('lms.lms.api.mark_lesson_progress', {
			course: pathname[3],
			chapter_number: lessonIndex[0],
			lesson_number: lessonIndex[1],
		})
	}
}

const getSubmissionColumns = () => {
	return [
		{
			label: 'No.',
			key: 'idx',
		},
		{
			label: 'Date',
			key: 'creation',
		},
		{
			label: 'Score',
			key: 'score',
			align: 'center',
		},
		{
			label: 'Score out of',
			key: 'score_out_of',
			align: 'center',
		},
		{
			label: 'Percentage',
			key: 'percentage',
			align: 'center',
		},
	]
}
</script>
<style>
p {
	line-height: 1.5rem;
}
.proctor-no-select {
	user-select: none;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
}
</style>
