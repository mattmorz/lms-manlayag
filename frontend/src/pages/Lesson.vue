<template>
	<div v-if="lesson.data" class="flex flex-col h-screen">
		<header
			class="sticky top-0 z-20 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<div class="flex items-center gap-2">
				<Breadcrumbs class="h-7" :items="breadcrumbs" />
				<LockKeyholeIcon v-if="lesson.data?.locked" class="w-4 h-4 text-orange-600" />
			</div>
			<div class="flex items-center space-x-2">
				<Tooltip v-if="canGoZen()" :text="__('Zen Mode')">
					<Button @click="goFullScreen()">
						<template #icon>
							<Focus class="w-4 h-4 stroke-2" />
						</template>
					</Button>
				</Tooltip>
				<Button v-if="isAdmin" @click="showVideoStats()">
					<template #icon>
						<TrendingUp class="size-4 stroke-1.5" />
					</template>
				</Button>
				<CertificationLinks :courseName="courseName" />
				<Button v-if="lesson.data.prev" @click="switchLesson('prev')">
					<template #prefix>
						<ChevronLeft class="w-4 h-4 stroke-1" />
					</template>
					<span>
						{{ __('Previous') }}
					</span>
				</Button>

				<router-link
					v-if="allowEdit()"
					:to="{
						name: 'LessonForm',
						params: {
							courseName: courseName,
							chapterNumber: props.chapterNumber,
							lessonNumber: props.lessonNumber,
						},
					}"
				>
					<Button>
						{{ __('Edit') }}
					</Button>
				</router-link>

				<Button
					v-if="lesson.data.next"
					:disabled="!canProceedToNext()"
					@click="switchLesson('next')"
				>
					<template #suffix>
						<ChevronRight class="w-4 h-4 stroke-1" />
					</template>
					<span>
						{{
							canProceedToNext()
								? __('Next')
								: __('Complete Lesson First')
						}}
					</span>
				</Button>

				<router-link
					v-else
					:to="{
						name: 'CourseDetail',
						params: { courseName: courseName },
					}"
				>
					<Button>
						{{ __('Back to Course') }}
					</Button>
				</router-link>
			</div>
		</header>
		<div class="grid md:grid-cols-[70%,30%] flex-1 overflow-hidden">
			<div v-if="lesson.data?.locked" class="border-r overflow-y-auto flex flex-col items-center justify-center">
				<div class="shadow rounded-md w-3/4 text-center p-4">
					<div class="flex items-center justify-center mt-4 space-x-2">
						<LockKeyholeIcon class="size-4 stroke-2 text-ink-gray-5" />
						<div class="text-lg font-semibold text-ink-gray-7">
							{{ __('Lesson Locked') }}
						</div>
					</div>
					<div class="mt-1 mb-4 text-ink-gray-7">
						{{ lesson.data.message }}
					</div>

					<div class="flex gap-2 justify-center">
						<Button
							v-if="lesson.data.prev"
							@click="switchLesson('prev')"
						>
							{{ __('Go Back to Previous Lesson') }}
						</Button>

						<router-link
							v-else
							:to="{
								name: 'CourseDetail',
								params: { courseName: courseName },
							}"
						>
							<Button>
								{{ __('Back to Course') }}
							</Button>
						</router-link>
					</div>
				</div>
			</div>
			<div v-else-if="lesson.data.no_preview" class="border-r overflow-y-auto flex flex-col items-center justify-center">
				<div class="shadow rounded-md w-3/4 text-center p-4">
					<div class="flex items-center justify-center mt-4 space-x-2">
						<LockKeyholeIcon class="size-4 stroke-2 text-ink-gray-5" />
						<div class="text-lg font-semibold text-ink-gray-7">
							{{ __('This lesson is locked') }}
						</div>
					</div>
					<div class="mt-1 mb-4 text-ink-gray-7">
						{{
							__(
								'This lesson is not available for preview. Please enroll in the course to access it.'
							)
						}}
					</div>
					<Button
						v-if="user.data && !lesson.data.disable_self_learning"
						@click="enrollStudent()"
						variant="solid"
					>
						{{ __('Start Learning') }}
					</Button>
					<Badge
						theme="blue"
						size="lg"
						v-else-if="lesson.data.disable_self_learning"
						class="mt-2"
					>
						{{ __('Contact the Administrator to enroll for this course.') }}
					</Badge>
					<Button v-else @click="redirectToLogin()">
						<template #prefix>
							<LogIn class="w-4 h-4 stroke-1" />
						</template>
						{{ __('Login') }}
					</Button>
				</div>
			</div>
			<div
				v-else
				ref="lessonContainer"
				class="bg-surface-white overflow-y-auto"
				:class="{
					'overflow-y-auto': zenModeEnabled,
				}"
			>
				<div
					class="border-r pt-5 pb-10"
					:class="{
						'w-full md:w-3/5 mx-auto border-none !pt-10': zenModeEnabled,
					}"
				>
					<div class="px-5">
						<div
							class="flex flex-col space-y-3 md:space-y-0 md:flex-row md:items-center justify-between"
						>
							<div class="flex flex-col">
								<div class="text-3xl font-semibold text-ink-gray-9">
									{{ lesson.data.title }}
								</div>

								<div
									v-if="zenModeEnabled"
									class="relative flex items-center space-x-2 text-sm mt-1 text-ink-gray-7 group w-fit mt-2"
								>
									<span>
										{{ lesson.data.chapter_title }} -
										{{ lesson.data.course_title }}
									</span>
									<Info class="size-3" />
									<div
										class="hidden group-hover:block rounded bg-gray-900 px-2 py-1 text-xs text-white shadow-xl absolute left-0 top-full mt-2"
									>
										{{ Math.ceil(lesson.data.membership.progress) }}%
										{{ __('completed') }}
									</div>
								</div>
							</div>

							<div
								v-if="zenModeEnabled"
								class="flex items-center space-x-2 mt-2 md:mt-0"
							>
								<Button @click="showDiscussionsInZenMode()">
									<template #icon>
										<MessageCircleQuestion class="w-4 h-4 stroke-1.5" />
									</template>
								</Button>
								<Button v-if="lesson.data.prev" @click="switchLesson('prev')">
									<template #prefix>
										<ChevronLeft class="w-4 h-4 stroke-1" />
									</template>
									<span>
										{{ __('Previous') }}
									</span>
								</Button>

								<router-link
									v-if="allowEdit()"
									:to="{
										name: 'LessonForm',
										params: {
											courseName: courseName,
											chapterNumber: props.chapterNumber,
											lessonNumber: props.lessonNumber,
										},
									}"
								>
									<Button>
										{{ __('Edit') }}
									</Button>
								</router-link>
								<Button
									v-if="lesson.data.next"
									:disabled="!canProceedToNext()"
									@click="switchLesson('next')"
								>
									<template #suffix>
										<ChevronRight class="w-4 h-4 stroke-1" />
									</template>
									<span>
										{{ __('Next') }}
									</span>
								</Button>

								<router-link
									v-else
									:to="{
										name: 'CourseDetail',
										params: { courseName: courseName },
									}"
								>
									<Button>
										{{ __('Back to Course') }}
									</Button>
								</router-link>
							</div>
						</div>

						<div v-if="!zenModeEnabled" class="flex items-center mt-4 md:mt-2">
							<span
								class="h-6 mr-1"
								:class="{
									'avatar-group overlap': lesson.data.instructors?.length > 1,
								}"
							>
								<UserAvatar
									v-for="instructor in lesson.data.instructors"
									:user="instructor"
								/>
							</span>
							<CourseInstructors
								v-if="lesson.data?.instructors"
								:instructors="lesson.data.instructors"
							/>
						</div>

						<div class="mt-4 flex justify-end">
							<Button
								variant="ghost"
								class="text-sm text-ink-gray-7 hover:text-ink-gray-9"
								@click="toggleCodeHighlightTheme"
							>
								{{
									codeHighlightTheme === 'light'
										? __('Code Theme: Light')
										: __('Code Theme: Dark')
								}}
							</Button>
						</div>

						<div
							v-if="
								lesson.data.instructor_content &&
								JSON.parse(lesson.data.instructor_content)?.blocks?.length >
									1 &&
								allowInstructorContent()
							"
							:class="['bg-surface-gray-2 p-3 rounded-md mt-6', codeHighlightThemeClass]"
						>
							<div class="text-ink-gray-5 font-medium">
								{{ __('Instructor Notes') }}
							</div>
							<div
								id="instructor-content"
								class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
							></div>
						</div>
						<div
							v-else-if="lesson.data.instructor_notes"
							:class="[
								'ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8',
								codeHighlightThemeClass,
							]"
						>
							<LessonContent
								:content="lesson.data.instructor_notes"
								:highlightTheme="codeHighlightTheme"
							/>
						</div>
						<div
							v-if="lesson.data.content"
							@mouseup="toggleInlineMenu"
							:class="[
								'ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8',
								codeHighlightThemeClass,
							]"
						>
							<div id="editor"></div>
						</div>
						<div
							v-else
							:class="[
								'ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8',
								codeHighlightThemeClass,
							]"
						>
							<LessonContent
								v-if="lesson.data?.body"
								:content="lesson.data.body"
								:youtube="lesson.data.youtube"
								:quizId="lesson.data.quiz_id"
								:highlightTheme="codeHighlightTheme"
							/>
						</div>

						<div v-if="hasLessonTranscript" class="mt-6">
							<div class="flex items-center space-x-2">
								<Button
									variant="ghost"
									class="inline-flex items-center !gap-1 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
									@click="showLessonTranscript = !showLessonTranscript"
								>
									<template #prefix>
										<FileText class="w-4 h-4 stroke-1.5 !mr-0" />
									</template>
									<span>{{ showLessonTranscript ? __('Hide Transcript') : __('Show Transcript') }}</span>
								</Button>

								<Button
									v-if="isCourseCreator"
									variant="ghost"
									class="inline-flex items-center !gap-1 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
									@click="triggerTranscriptUpload"
								>
									<template #prefix>
										<Upload class="w-4 h-4 stroke-1.5 !mr-0" />
									</template>
									<span>{{ __('Upload Transcript') }}</span>
								</Button>

								<Button
									v-if="isCourseCreator && lessonWordsList.length > 0"
									variant="ghost"
									class="inline-flex items-center !gap-1 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
									@click="openEditTranscriptModal"
								>
									<template #prefix>
										<Edit class="w-4 h-4 stroke-1.5 !mr-0" />
									</template>
									<span>{{ __('Edit Transcript') }}</span>
								</Button>

								<input
									ref="transcriptFileInput"
									type="file"
									accept=".vtt,.srt,.json"
									class="hidden"
									@change="handleTranscriptFile"
								/>
							</div>
							
							<div 
								v-show="showLessonTranscript" 
								class="mt-2 border border-outline-gray-2 rounded-md bg-surface-gray-2 p-4 transition-all duration-300"
							>
								<div 
									v-if="lessonTranscriptResource.loading" 
									class="flex items-center justify-center py-6 text-sm text-ink-gray-5"
								>
									<LoadingIndicator class="w-5 h-5 mr-2" />
									<span>{{ __('Loading transcript...') }}</span>
								</div>
								<div 
									v-else-if="lessonTranscriptResource.error" 
									class="text-sm text-red-500 py-2 text-center"
								>
									{{ __('Could not load transcript for this video.') }}
								</div>
								<div 
									v-else-if="lessonWordsList.length === 0" 
									class="text-sm text-ink-gray-5 py-2 text-center"
								>
									{{ __('No transcript available.') }}
								</div>
								<div 
									v-else
									ref="lessonTranscriptContainer"
									class="relative overflow-y-auto max-h-48 scrollbar-thin scroll-smooth text-base leading-relaxed pr-2"
								>
									<span 
										v-for="(word, index) in lessonWordsList" 
										:key="index"
										:id="'lesson-word-' + index"
										class="inline-block mr-1 cursor-pointer transition-colors duration-150 rounded px-0.5 select-none"
										:class="index === activeLessonWordIndex ? 'bg-yellow-200/80 text-ink-gray-9 font-bold dark:bg-yellow-900/50 dark:text-yellow-100' : 'text-ink-gray-7 hover:bg-gray-100 dark:hover:bg-gray-800'"
										@click="seekToLessonWord(word.start)"
									>
										{{ word.text }}
									</span>
								</div>
							</div>
						</div>
					</div>
					<div
						v-if="lesson.data"
						class="mt-10 pb-20 pt-5 border-t px-5"
						ref="discussionsContainer"
					>
						<TabButtons
							v-if="tabs.length > 1"
							:buttons="tabs"
							v-model="currentTab"
							class="w-fit mb-10"
						/>
						<Notes
							v-if="currentTab === 'Notes'"
							:lesson="lesson.data?.name"
							v-model:notes="notes"
							@updateNotes="updateNotes"
						/>
						<Discussions
							v-else-if="allowDiscussions"
							:title="'Questions'"
							:doctype="'Course Lesson'"
							:docname="lesson.data.name"
							:key="lesson.data.name"
							:emptyStateText="
								__('Ask a question to get help from the community.')
							"
						/>
					</div>
				</div>
			</div>
			<div class="sticky top-0 overflow-y-auto">
				<div class="bg-surface-menu-bar py-5 px-2 border-b">
					<div class="text-lg font-semibold text-ink-gray-9">
						{{ lesson.data.course_title }}
					</div>
					<div
						v-if="user && lesson.data.membership"
						class="text-sm mt-4 mb-2 text-ink-gray-5"
					>
						{{ Math.ceil(lessonProgress) }}% {{ __('completed') }}
					</div>

					<ProgressBar
						v-if="user && lesson.data.membership"
						:progress="lessonProgress"
					/>
				</div>
				<CourseOutline
					:courseName="courseName"
					:key="`${chapterNumber}-${lesson.data?.name}`"
					:getProgress="lesson.data.membership ? true : false"
					:lessonProgress="lessonProgress"
				/>
			</div>
		</div>
	</div>
	<InlineLessonMenu
		v-if="lesson.data?.name"
		v-model="showInlineMenu"
		:lesson="lesson.data?.name"
		v-model:notes="notes"
		@updateNotes="updateNotes"
	/>
	<VideoStatistics
		v-if="isAdmin"
		v-model="showStatsDialog"
		:lessonName="lesson.data?.name"
		:lessonTitle="lesson.data?.title"
	/>
	<Dialog
		v-model="showEditTranscriptModal"
		:options="{
			title: __('Edit Transcript'),
			size: 'xl',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: () => saveEditedTranscript(),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
				<div 
					v-for="(segment, index) in editableSegments" 
					:key="index"
					class="flex items-center space-x-3 border-b pb-2 last:border-0"
				>
					<span class="text-xs text-ink-gray-5 w-16 shrink-0 font-mono">
						{{ formatSeconds(segment.start) }}
					</span>
					<input
						v-model="segment.start"
						type="number"
						step="0.1"
						class="w-16 border rounded px-1.5 py-0.5 text-xs text-center font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
						title="Start Time (seconds)"
					/>
					<textarea
						v-model="segment.text"
						rows="2"
						class="flex-1 border rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-500"
					/>
					<Button
						variant="ghost"
						class="text-red-500 hover:text-red-700 p-1"
						@click="removeSegment(index)"
					>
						<template #icon>
							<Trash2 class="size-4" />
						</template>
					</Button>
				</div>
				<div class="pt-2">
					<Button
						variant="outline"
						class="w-full flex justify-center items-center py-2"
						@click="addSegment"
					>
						<template #prefix>
							<Plus class="size-4" />
						</template>
						{{ __('Add Segment') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Badge,
	Breadcrumbs,
	Button,
	call,
	createListResource,
	createResource,
	Dialog,
	LoadingIndicator,
	TabButtons,
	Tooltip,
	usePageMeta,
	toast,
} from 'frappe-ui'
import {
	computed,
	watch,
	inject,
	ref,
	onMounted,
	onBeforeUnmount,
	nextTick,
} from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
	ChevronLeft,
	ChevronRight,
	FileText,
	LockKeyholeIcon,
	LogIn,
	Focus,
	Info,
	MessageCircleQuestion,
	TrendingUp,
	Upload,
	Edit,
	Trash2,
	Plus,
} from 'lucide-vue-next'
import { getEditorTools, enablePlyr, highlightText } from '@/utils'
import { sessionStore } from '@/stores/session'
import { useSidebar } from '@/stores/sidebar'
import EditorJS from '@editorjs/editorjs'
import LessonContent from '@/components/LessonContent.vue'
import CourseInstructors from '@/components/CourseInstructors.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import Discussions from '@/components/Discussions.vue'
import CertificationLinks from '@/components/CertificationLinks.vue'
import VideoStatistics from '@/components/Modals/VideoStatistics.vue'
import CourseOutline from '@/components/CourseOutline.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import Notes from '@/components/Notes/Notes.vue'
import InlineLessonMenu from '@/components/Notes/InlineLessonMenu.vue'
import { getLmsRoute } from '@/utils/basePath'

const user = inject('$user')
const socket = inject('$socket')
const router = useRouter()
const route = useRoute()
const allowDiscussions = ref(false)
const editor = ref(null)
const instructorEditor = ref(null)
const lessonProgress = ref(0)
const lessonContainer = ref(null)
const zenModeEnabled = ref(false)
const showStatsDialog = ref(false)
const hasQuiz = ref(false)
const discussionsContainer = ref(null)
const timer = ref(0)
const { brand } = sessionStore()
const sidebarStore = useSidebar()
const plyrSources = ref([])
const showInlineMenu = ref(false)
const currentTab = ref('Notes')
const CODE_HIGHLIGHT_THEME_KEY = 'lms-code-highlight-theme'
const codeHighlightTheme = ref(
	localStorage.getItem(CODE_HIGHLIGHT_THEME_KEY) === 'light' ? 'light' : 'dark'
)
const codeHighlightThemeClass = computed(() =>
	codeHighlightTheme.value === 'light'
		? 'highlight-theme-light'
		: 'highlight-theme-dark'
)

const toggleCodeHighlightTheme = () => {
	codeHighlightTheme.value =
		codeHighlightTheme.value === 'light' ? 'dark' : 'light'
	localStorage.setItem(CODE_HIGHLIGHT_THEME_KEY, codeHighlightTheme.value)
}
let timerInterval



const tabs = ref([
	{
		label: __('Notes'),
		value: 'Notes',
	},
])

const props = defineProps({
	courseName: {
		type: String,
		required: true,
	},
	chapterNumber: {
		type: String,
		required: true,
	},
	lessonNumber: {
		type: String,
		required: true,
	},
})

const reloadLessonData = () => {
	if (lessonQuizIds.value.length > 0) {
		quizSubmissions.reload()
	}
}

onMounted(() => {
	startTimer()
	sidebarStore.isSidebarCollapsed = true
	document.addEventListener('fullscreenchange', attachFullscreenEvent)
	window.addEventListener('lms-lesson-quiz-passed', reloadLessonData)
	socket.on('update_lesson_progress', (data) => {
		if (data.course === props.courseName) {
			lessonProgress.value = data.progress
		}
	})
})

const attachFullscreenEvent = () => {
	if (document.fullscreenElement) {
		zenModeEnabled.value = true
		allowDiscussions.value = false
	} else {
		zenModeEnabled.value = false
		if (!hasQuiz.value) {
			allowDiscussions.value = true
		}
	}
}

onBeforeUnmount(() => {
	document.removeEventListener('fullscreenchange', attachFullscreenEvent)
	window.removeEventListener('lms-lesson-quiz-passed', reloadLessonData)
	sidebarStore.isSidebarCollapsed = false
	trackVideoWatchDuration()
})

const lesson = createResource({
	url: 'lms.lms.utils.get_lesson',
	makeParams(values) {
		return {
			course: props.courseName,
			chapter: values ? values.chapter : props.chapterNumber,
			lesson: values ? values.lesson : props.lessonNumber,
		}
	},
	auto: true,
})

const getLessonQuizIds = (lessonData) => {
	const ids = new Set()
	if (!lessonData) return []

	if (lessonData.quiz_id) {
		lessonData.quiz_id.split(',').forEach((quiz) => {
			if (quiz && quiz.trim()) {
				ids.add(quiz.trim())
			}
		})
	}

	if (lessonData.content) {
		try {
			const content = JSON.parse(lessonData.content)
			content.blocks?.forEach((block) => {
				if (block.type === 'quiz' && block.data?.quiz) {
					ids.add(block.data.quiz)
				}
			})
		} catch (error) {
			// Ignore malformed editor content
		}
	}

	if (lessonData.body) {
		const quizRegex = /\{\{\s*Quiz\(["']([^"']+)["']\)\s*\}\}/g
		let match
		while ((match = quizRegex.exec(lessonData.body))) {
			ids.add(match[1])
		}
	}

	return Array.from(ids)
}

const lessonQuizIds = computed(() => getLessonQuizIds(lesson.data))
const lessonHasEmbeddedQuiz = computed(() => lessonQuizIds.value.length > 0)
const lessonHasVideoQuiz = computed(() => lesson.data?.icon === 'icon-youtube' && lessonQuizIds.value.length > 0)
const canBypassCheckpointGates = computed(() => {
	return (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
})

const quizSubmissions = createResource({
	url: 'frappe.client.get_list',
	makeParams() {
		return {
			doctype: 'LMS Quiz Submission',
			filters: {
				member: user.data?.name,
				quiz: ['in', lessonQuizIds.value],
			},
			fields: ['quiz', 'percentage', 'passing_percentage'],
		}
	},
	auto: false,
	onSuccess() {
		if (lesson.data?.content) {
			renderLessonContent(lesson.data.content)
		}
	},
})

const passedLessonQuizIds = computed(() => {
	const submissions = quizSubmissions.data || []
	const passed = new Set()
	submissions.forEach((submission) => {
		const passingPercentage = submission.passing_percentage || 0
		if (Math.ceil(submission.percentage) >= passingPercentage) {
			passed.add(submission.quiz)
		}
	})
	return passed
})

const hasPassedAllLessonQuizzes = computed(() => {
	return lessonQuizIds.value.length > 0 && lessonQuizIds.value.every((quizId) => passedLessonQuizIds.value.has(quizId))
})

const passedLessonQuizSignature = computed(() => {
	return Array.from(passedLessonQuizIds.value).sort().join(',')
})

const getVisibleLessonContent = (content) => {
	if (!content || canBypassCheckpointGates.value) {
		return content
	}

	try {
		const parsedContent = JSON.parse(content)
		const visibleBlocks = []
		let isLockedAfterCheckpoint = false

		for (const block of parsedContent.blocks || []) {
			if (isLockedAfterCheckpoint) {
				break
			}

			visibleBlocks.push(block)

			if (
				block.type === 'quiz' &&
				block.data?.quiz &&
				block.data?.checkpoint_quiz &&
				!passedLessonQuizIds.value.has(block.data.quiz)
			) {
				isLockedAfterCheckpoint = true
			}
		}

		if (isLockedAfterCheckpoint) {
			visibleBlocks.push({
				type: 'paragraph',
				data: {
					text: __('Complete the checkpoint quiz above to unlock the next section.'),
				},
			})
		}

		return JSON.stringify({
			...parsedContent,
			blocks: visibleBlocks,
		})
	} catch (error) {
		return content
	}
}

watch(
	() => [lessonQuizIds.value, user.data?.name],
	() => {
		if (lessonQuizIds.value.length > 0 && user.data?.name) {
			quizSubmissions.reload()
		} else {
			quizSubmissions.reset()
		}
	},
	{ immediate: true }
)

const lessonLocked = computed(() => {
    return lesson.data?.locked
})

const showLessonTranscript = ref(false)
const lessonTranscriptContainer = ref(null)
const currentVideoTime = ref(0)
const activePlayer = ref(null)
const transcriptFileInput = ref(null)

const triggerTranscriptUpload = () => {
	transcriptFileInput.value?.click()
}

const uploadTranscriptResource = createResource({
	url: 'lms.lms.api.upload_video_transcript',
	onSuccess(data) {
		toast.success(__('Transcript saved successfully.'))
		lessonTranscriptResource.reload()
		showLessonTranscript.value = true
		showEditTranscriptModal.value = false
		if (transcriptFileInput.value) {
			transcriptFileInput.value.value = ''
		}
	},
	onError(err) {
		toast.error(err.messages?.[0] || err || __('Failed to upload transcript.'))
		if (transcriptFileInput.value) {
			transcriptFileInput.value.value = ''
		}
	}
})

const showEditTranscriptModal = ref(false)
const editableSegments = ref([])

const formatSeconds = (time) => {
	const minutes = Math.floor(time / 60)
	const seconds = Math.floor(time % 60)
	return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`
}

const openEditTranscriptModal = () => {
	editableSegments.value = JSON.parse(JSON.stringify(lessonTranscriptResource.data || []))
	showEditTranscriptModal.value = true
}

const removeSegment = (index) => {
	editableSegments.value.splice(index, 1)
}

const addSegment = () => {
	let lastStart = 0
	if (editableSegments.value.length > 0) {
		const lastSeg = editableSegments.value[editableSegments.value.length - 1]
		lastStart = parseFloat(lastSeg.start) + 5
	}
	editableSegments.value.push({
		text: '',
		start: lastStart,
		duration: 5
	})
}

const saveEditedTranscript = () => {
	const sorted = [...editableSegments.value].sort((a, b) => parseFloat(a.start) - parseFloat(b.start))
	sorted.forEach(s => {
		s.start = parseFloat(s.start) || 0
		s.duration = parseFloat(s.duration) || 0
	})

	uploadTranscriptResource.submit({
		lesson_name: lesson.data.name,
		video_id: lessonVideoId.value,
		file_content: JSON.stringify(sorted),
		file_name: 'transcript.json',
	})
}

const handleTranscriptFile = (event) => {
	const file = event.target.files?.[0]
	if (!file) return

	const reader = new FileReader()
	reader.onload = (e) => {
		const content = e.target.result
		uploadTranscriptResource.submit({
			lesson_name: lesson.data.name,
			video_id: lessonVideoId.value,
			file_content: content,
			file_name: file.name,
		})
	}
	reader.readAsText(file)
}

const hasLessonTranscript = computed(() => {
	return !!lesson.data?.youtube
})

const lessonVideoService = computed(() => {
	const url = lesson.data?.youtube || ''
	if (url.includes('vimeo.com') || url.includes('player.vimeo.com')) {
		return 'vimeo'
	}
	return 'youtube'
})

const lessonVideoId = computed(() => {
	const embedUrl = lesson.data?.youtube
	const service = lessonVideoService.value
	if (!embedUrl) return ''
	const s = String(embedUrl).trim()
	if (service === 'youtube') {
		try {
			const urlObj = new URL(s)
			if (urlObj.hostname.includes('youtube.com')) {
				return urlObj.searchParams.get('v') || urlObj.pathname.split('/').pop()
			} else if (urlObj.hostname.includes('youtu.be')) {
				return urlObj.pathname.split('/').pop()
			}
		} catch (e) {}
		const match = s.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=))([\w-]{11})/)
		return match ? match[1] : s
	} else if (service === 'vimeo') {
		const match = s.match(/(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)/)
		return match ? match[1] : s
	}
	return s
})

const lessonTranscriptResource = createResource({
	url: 'lms.lms.api.get_video_transcript',
	makeParams() {
		return {
			video_id: lessonVideoId.value,
			service: lessonVideoService.value
		}
	},
	auto: false
})

const lessonWordsList = computed(() => {
	if (!lessonTranscriptResource.data) return []
	const words = []
	lessonTranscriptResource.data.forEach((segment) => {
		const segmentText = segment.text || ''
		const segmentWords = segmentText.trim().split(/\s+/)
		if (segmentWords.length === 0 || (segmentWords.length === 1 && segmentWords[0] === '')) return
		
		const wordDuration = segment.duration / segmentWords.length
		segmentWords.forEach((wordText, index) => {
			words.push({
				text: wordText,
				start: segment.start + (index * wordDuration),
				duration: wordDuration
			})
		})
	})
	return words
})

const activeLessonWordIndex = computed(() => {
	const time = currentVideoTime.value
	let activeIndex = -1
	for (let i = 0; i < lessonWordsList.value.length; i++) {
		const word = lessonWordsList.value[i]
		if (word.start <= time) {
			activeIndex = i
		} else {
			break
		}
	}
	return activeIndex
})

const seekToLessonWord = (start) => {
	const player = activePlayer.value || (plyrSources.value && plyrSources.value[0])
	if (player) {
		player.currentTime = start
		player.play()
	}
}

watch(
	() => [lessonVideoId.value, lessonVideoService.value],
	([vid, svc]) => {
		if (vid && svc && lesson.data?.youtube) {
			lessonTranscriptResource.reload()
		}
	},
	{ immediate: true }
)

watch(activeLessonWordIndex, (newIndex) => {
	if (newIndex === -1 || !lessonTranscriptContainer.value) return
	const container = lessonTranscriptContainer.value
	const activeWordEl = container.querySelector(`#lesson-word-${newIndex}`)
	if (activeWordEl) {
		const containerRect = container.getBoundingClientRect()
		const elRect = activeWordEl.getBoundingClientRect()
		
		const relativeTop = elRect.top - containerRect.top
		const scrollTarget = container.scrollTop + relativeTop - (containerRect.height / 2) + (elRect.height / 2)
		
		container.scrollTo({
			top: scrollTarget,
			behavior: 'smooth'
		})
	}
})

const setupLesson = (data) => {
	if (Object.keys(data).length === 0) {
		router.push({
			name: 'CourseDetail',
			params: { courseName: props.courseName },
		})
		return
	}
	if (data.is_scorm_package) {
		router.push({
			name: 'SCORMChapter',
			params: {
				courseName: props.courseName,
				chapterName: data.chapter_name,
			},
		})
	}
	lessonProgress.value = data.membership?.progress
	if (data.content) {
		renderLessonContent(data.content)
	}
	if (
		data.instructor_content &&
		JSON.parse(data.instructor_content)?.blocks?.length > 1
	)
		instructorEditor.value = renderEditor(
			'instructor-content',
			data.instructor_content
		)
	editor.value?.isReady.then(() => {
		checkIfDiscussionsAllowed()
	})
	checkQuiz()
}

const checkQuiz = () => {
	if (!editor.value && lesson.body) {
		const quizRegex = /\{\{ Quiz\(".*"\) \}\}/
		hasQuiz.value = quizRegex.test(lesson.body)
		if (!hasQuiz.value && !zenModeEnabled) {
			allowDiscussions.value = true
		} else {
			allowDiscussions.value = false
		}
	}
}

const renderEditor = (holder, content) => {
	if (document.getElementById(holder))
		document.getElementById(holder).innerHTML = ''
	return new EditorJS({
		holder: holder,
		tools: getEditorTools(),
		data: JSON.parse(content),
		readOnly: true,
		defaultBlock: 'embed',
	})
}

const destroyEditor = (instance) => {
	if (instance?.destroy) {
		instance.destroy()
	}
}

let lastRenderedContent = null

const renderLessonContent = (content) => {
	const visibleContent = getVisibleLessonContent(content)
	if (visibleContent === lastRenderedContent) {
		return
	}
	lastRenderedContent = visibleContent
	destroyEditor(editor.value)
	editor.value = renderEditor('editor', visibleContent)
}

watch(
	[passedLessonQuizSignature, () => lesson.data?.content],
	() => {
		if (lesson.data?.content) {
			renderLessonContent(lesson.data.content)
		}
	}
)

const markProgress = () => {
	if (user.data && lesson.data && !lesson.data.progress) {
		progress.submit(
			{},
			{
				onError(err) {
					console.error(err)
				},
			}
		)
	}
}

const progress = createResource({
	url: 'lms.lms.doctype.course_lesson.course_lesson.save_progress',
	makeParams() {
		return {
			lesson: lesson.data.name,
			course: props.courseName,
		}
	},
	onSuccess(data) {
		lessonProgress.value = data
		if (lesson.data) {
			lesson.data.progress = data
		}
	},
})

const notes = createListResource({
	doctype: 'LMS Lesson Note',
	filters: {
		lesson: lesson.data?.name,
		member: user.data?.name,
	},
	fields: ['name', 'color', 'highlighted_text', 'note'],
	cache: ['notes', lesson.data?.name, user.data?.name],
	onSuccess(data) {
		data.forEach((note) => {
			setTimeout(() => {
				highlightText(note)
			}, 500)
		})
	},
})

const breadcrumbs = computed(() => {
	let crumbs = [{ label: __('Courses'), route: { name: 'Courses' } }]
	crumbs.push({
		label: lesson?.data?.course_title,
		route: { name: 'CourseDetail', params: { courseName: props.courseName } },
	})
	crumbs.push({
		label: lesson?.data?.title,
		route: {
			name: 'Lesson',
			params: {
				courseName: props.courseName,
				chapterNumber: props.chapterNumber,
				lessonNumber: props.lessonNumber,
			},
		},
	})
	return crumbs
})

const switchLesson = (direction) => {
    if (
        direction === 'next' &&
        !canProceedToNext()
    ) {
        toast.error(
            __('Please complete this lesson before proceeding.')
        )
        return
    }

    trackVideoWatchDuration()

    let lessonIndex =
        direction === 'prev'
            ? lesson.data.prev.split('.')
            : lesson.data.next.split('.')

    router.push({
        name: 'Lesson',
        params: {
            courseName: props.courseName,
            chapterNumber: lessonIndex[0],
            lessonNumber: lessonIndex[1],
        },
    })
}

const hasWatchedRequiredVideo = () => {
	if (lesson.data?.icon !== 'icon-youtube') return false

	const videos = Array.from(document.querySelectorAll('video'))
	if (videos.length > 0) {
		return videos.every((vid) => vid.duration && vid.currentTime >= 0.9 * vid.duration)
	}

	if (plyrSources.value && plyrSources.value.length > 0) {
		return plyrSources.value.every((source) => source.duration && source.currentTime >= 0.9 * source.duration)
	}

	return false
}

const canProceedToNext = () => {
	if (!lesson.data?.next) return true

	if (lesson.data?.enable_sequential_lessons === 0 || lesson.data?.enable_sequential_lessons === false) {
		return true
	}

	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	) {
		return true
	}

	if (lesson.data?.progress) return true

	const watchedEnough = hasWatchedRequiredVideo()

	if (lesson.data?.icon === 'icon-youtube') {
		if (lessonHasVideoQuiz.value) {
			return hasPassedAllLessonQuizzes.value && watchedEnough
		}
		return watchedEnough
	}

	if (lessonHasEmbeddedQuiz.value) {
		return hasPassedAllLessonQuizzes.value
	}

	return false
}

watch(
	[() => route.params.chapterNumber, () => route.params.lessonNumber],
	async (
		[newChapterNumber, newLessonNumber],
		[oldChapterNumber, oldLessonNumber]
	) => {
		if (newChapterNumber || newLessonNumber) {
			plyrSources.value = []
			await nextTick()
			resetLessonState(newChapterNumber, newLessonNumber)
			updateNotes()
			checkIfDiscussionsAllowed()
			checkQuiz()
		}
	}
)

const resetLessonState = (newChapterNumber, newLessonNumber) => {
	editor.value = null
	instructorEditor.value = null
	allowDiscussions.value = false
	lesson.submit({
		chapter: newChapterNumber,
		lesson: newLessonNumber,
	})
	clearInterval(timerInterval)
	timer.value = 0
}

const trackVideoWatchDuration = () => {
	if (!lesson.data.membership) return
	let videoDetails = getVideoDetails()
	videoDetails = videoDetails.concat(getPlyrSourceDetails())
	call('lms.lms.api.track_video_watch_duration', {
		lesson: lesson.data.name,
		videos: videoDetails,
	})
}

const getVideoDetails = () => {
	let details = []
	const videos = document.querySelectorAll('video')
	if (videos.length > 0) {
		videos.forEach((video) => {
			if (video.duration && video.currentTime >= 0.9 * video.duration) markProgress()
			details.push({
				source: video.src,
				watch_time: video.currentTime,
				duration: video.duration,
			})
		})
	}
	return details
}

const getPlyrSourceDetails = () => {
	let details = []
	plyrSources.value.forEach((source) => {
		if (source.duration && source.currentTime >= 0.9 * source.duration) markProgress()
		let src = cleanYouTubeUrl(source.source)
		details.push({
			source: src,
			watch_time: source.currentTime,
			duration: source.duration,
		})
	})
	return details
}

const cleanYouTubeUrl = (url) => {
	if (!url) return url
	const urlObj = new URL(url)
	urlObj.searchParams.delete('t')
	return urlObj.toString()
}

watch(
	() => lesson.data,
	async (data) => {
		setupLesson(data)
		startTimer()
		getPlyrSource()
		updateNotes()
		if (data.icon == 'icon-youtube') clearInterval(timerInterval)
	}
)

const getPlyrSource = async () => {
	await nextTick()
	if (plyrSources.value.length == 0) {
		plyrSources.value = await enablePlyr()
	}
	updateVideoWatchDuration()

	const lastSavedTimes = {}

	// Register real-time timeupdate and pause listeners
	plyrSources.value.forEach((plyrSource) => {
		const sourceUrl = cleanYouTubeUrl(plyrSource.source)

		plyrSource.on('pause', () => {
			trackVideoWatchDuration()
		})

		plyrSource.on('timeupdate', () => {
			currentVideoTime.value = plyrSource.currentTime
			activePlayer.value = plyrSource

			if (plyrSource.duration && plyrSource.currentTime >= 0.9 * plyrSource.duration) {
				markProgress()
			}

			const lastSaved = lastSavedTimes[sourceUrl] || 0
			if (Math.abs(plyrSource.currentTime - lastSaved) >= 5) {
				lastSavedTimes[sourceUrl] = plyrSource.currentTime
				trackVideoWatchDuration()
			}
		})
	})

	const videos = document.querySelectorAll('video')
	videos.forEach((video) => {
		video.addEventListener('pause', () => {
			trackVideoWatchDuration()
		})

		video.addEventListener('timeupdate', () => {
			currentVideoTime.value = video.currentTime

			if (video.duration && video.currentTime >= 0.9 * video.duration) {
				markProgress()
			}

			const lastSaved = lastSavedTimes[video.src] || 0
			if (Math.abs(video.currentTime - lastSaved) >= 5) {
				lastSavedTimes[video.src] = video.currentTime
				trackVideoWatchDuration()
			}
		})
	})
}

const updateVideoWatchDuration = () => {
	if (lesson.data.videos && lesson.data.videos.length > 0) {
		lesson.data.videos.forEach((video) => {
			if (video.source.includes('youtube') || video.source.includes('vimeo')) {
				updatePlyrVideoTime(video)
			} else {
				updateVideoTime(video)
			}
		})
	}
}

const updatePlyrVideoTime = (video) => {
	plyrSources.value.forEach((plyrSource) => {
		let lastWatchedTime = 0
		let isSeeking = false

		plyrSource.on('ready', () => {
			if (plyrSource.source === video.source) {
				plyrSource.embed.seekTo(video.watch_time, true)
				plyrSource.play()
				plyrSource.pause()
			}
		})
	})
}

const updateVideoTime = (video) => {
	const videos = document.querySelectorAll('video')
	if (videos.length > 0) {
		videos.forEach((vid) => {
			if (vid.src === video.source) {
				let watch_time = video.watch_time < vid.duration ? video.watch_time : 0
				if (vid.readyState >= 1) {
					vid.currentTime = watch_time
				} else {
					vid.addEventListener('loadedmetadata', () => {
						vid.currentTime = watch_time
					})
				}
			}
		})
	}
}

const startTimer = () => {
	if (!lesson.data?.membership) return
	if (lesson.data?.icon === 'icon-youtube') return
	timerInterval = setInterval(() => {
		timer.value++
		if (timer.value == 30) {
			clearInterval(timerInterval)
			markProgress()
		}
	}, 1000)
}

onBeforeUnmount(() => {
	clearInterval(timerInterval)
})

const checkIfDiscussionsAllowed = () => {
	hasQuiz.value = false
	if (lesson.data?.content) {
		JSON.parse(lesson.data.content)?.blocks?.forEach((block) => {
			if (block.type === 'quiz') {
				hasQuiz.value = true
			}
		})
	}

	if (
		!hasQuiz.value &&
		!zenModeEnabled.value &&
		(lesson.data?.membership ||
			user.data?.is_moderator ||
			user.data?.is_instructor)
	) {
		allowDiscussions.value = true
	} else {
		allowDiscussions.value = false
	}
}

const isAdmin = computed(() => {
	let isInstructor = lesson.data?.instructors?.includes(user.data?.name)
	return user.data?.is_moderator || isInstructor
})

const isCourseCreator = computed(() => {
	return (
		user.data?.is_course_creator ||
		user.data?.course_creator ||
		(Array.isArray(user.data?.roles) && user.data.roles.includes('Course Creator'))
	)
})

const allowEdit = () => {
	if (window.read_only_mode) return false
	return isAdmin.value
}

const allowInstructorContent = () => {
	if (window.read_only_mode) return false
	return isAdmin.value
}

const enrollment = createResource({
	url: 'frappe.client.insert',
	makeParams() {
		return {
			doc: {
				doctype: 'LMS Enrollment',
				course: props.courseName,
				member: user.data?.name,
			},
		}
	},
})

const enrollStudent = () => {
	enrollment.submit(
		{},
		{
			onSuccess() {
				window.location.reload()
			},
			onError(err) {
				toast.error(__(err.messages?.[0] || err))
				console.error(err)
			},
		}
	)
}

const toggleInlineMenu = async () => {
	showInlineMenu.value = false
	await nextTick()
	let selection = window.getSelection()
	if (selection.toString()) {
		showInlineMenu.value = true
	}
}

const showVideoStats = () => {
	showStatsDialog.value = true
}

const canGoZen = () => {
	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
		return true
	if (lesson.data?.membership) return true
	return false
}

const goFullScreen = () => {
	if (lessonContainer.value.requestFullscreen) {
		lessonContainer.value.requestFullscreen()
	} else if (lessonContainer.value.mozRequestFullScreen) {
		lessonContainer.value.mozRequestFullScreen()
	} else if (lessonContainer.value.webkitRequestFullscreen) {
		lessonContainer.value.webkitRequestFullscreen()
	} else if (lessonContainer.value.msRequestFullscreen) {
		lessonContainer.value.msRequestFullscreen()
	}
}

const showDiscussionsInZenMode = () => {
	if (allowDiscussions.value) {
		allowDiscussions.value = false
	} else {
		allowDiscussions.value = true
		currentTab.value = 'Community'
		scrollDiscussionsIntoView()
	}
}

const scrollDiscussionsIntoView = () => {
	nextTick(() => {
		discussionsContainer.value?.scrollIntoView({
			behavior: 'smooth',
			block: 'center',
			inline: 'nearest',
		})
	})
}

const updateNotes = () => {
	if (!user.data) return
	notes.update({
		filters: {
			lesson: lesson.data?.name,
			member: user.data?.name,
		},
	})
	notes.reload()
}

watch(allowDiscussions, () => {
	if (allowDiscussions.value) {
		tabs.value = [
			{
				label: __('Notes'),
				value: 'Notes',
			},
			{
				label: __('Community'),
				value: 'Community',
			},
		]
	} else {
		tabs.value = [
			{
				label: __('Notes'),
				value: 'Notes',
			},
		]
	}
})

const redirectToLogin = () => {
	window.location.href = `/login?redirect-to=${getLmsRoute(
		`courses/${props.courseName}`
	)}`
}

usePageMeta(() => {
	return {
		title: lesson?.data?.title,
		icon: brand.favicon,
	}
})
</script>
<style>
.avatar-group {
	display: inline-flex;
	align-items: center;
}

.avatar-group .avatar {
	transition: margin 0.1s ease-in-out;
}

.lesson-content p {
	margin-bottom: 1rem;
	line-height: 1.7;
}

.lesson-content li {
	line-height: 1.7;
}

.lesson-content ol {
	list-style: auto;
	margin: revert;
	padding: 1rem;
}

.lesson-content ul {
	list-style: auto;
	padding: 1rem;
	margin: revert;
}

.lesson-content img {
	border: 1px solid theme('colors.gray.200');
	border-radius: 0.5rem;
}

.lesson-content code {
	display: block;
	overflow-x: auto;
	padding: 1rem 1.25rem;
	background: #011627;
	color: #d6deeb;
	border-radius: 0.5rem;
	margin: 1rem 0;
}

.lesson-content a {
	color: theme('colors.gray.900');
	text-decoration: underline;
	font-weight: 500;
}

.embed-tool__caption,
.cdx-simple-image__caption {
	display: none;
}

.ce-block__content {
	max-width: unset;
}

.codex-editor__redactor {
	padding-bottom: 0px !important;
}

.codeBoxHolder {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
}

.codeBoxControls {
	display: flex;
	align-items: center;
	gap: 8px;
}

.codeBoxTextArea {
	width: 100%;
	min-height: 30px;
	padding: 10px;
	border-radius: 2px 2px 2px 0;
	border: none !important;
	outline: none !important;
	font: 14px monospace;
}

.codeBoxSelectDiv {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
	position: relative;
}

.codeBoxSelectInput {
	border-radius: 0 0 20px 2px;
	padding: 2px 26px;
	padding-top: 0;
	padding-right: 0;
	text-align: left;
	cursor: pointer;
	border: none !important;
	outline: none !important;
}

.codeBoxSelectDropIcon {
	position: absolute !important;
	left: 10px !important;
	bottom: 0 !important;
	width: unset !important;
	height: unset !important;
	font-size: 16px !important;
}

.codeBoxSelectPreview {
	display: none;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
	border-radius: 2px;
	box-shadow: 0 3px 15px -3px rgba(13, 20, 33, 0.13);
	position: absolute;
	top: 100%;
	margin: 5px 0;
	max-height: 30vh;
	overflow-x: hidden;
	overflow-y: auto;
	z-index: 10000;
}

.codeBoxSelectItem {
	width: 100%;
	padding: 5px 20px;
	margin: 0;
	cursor: pointer;
}

.codeBoxSelectItem:hover {
	opacity: 0.7;
}

.codeBoxSelectedItem {
	background-color: lightblue !important;
}

.codeBoxShow {
	display: flex !important;
}

.codeBoxThemeToggle {
	border: none;
	outline: none;
	border-radius: 999px;
	padding: 2px 10px;
	font-size: 12px;
	cursor: pointer;
	background: #e5e7eb;
	color: #111827;
}

.dark {
	color: #abb2bf;
	background-color: #282c34;
}

.light {
	color: #383a42;
	background-color: #fafafa;
}

.codeBoxTextArea {
	line-height: 1.7;
}

.highlight-theme-dark pre code.hljs {
	background-color: #282c34 !important;
	color: #abb2bf !important;
}

.highlight-theme-light pre code.hljs {
	background-color: #fafafa !important;
	color: #383a42 !important;
	border: 1px solid #e5e7eb;
}

.tc-table {
	border-left: 1px solid #e8e8eb;
}

.plyr__volume input[type='range'] {
	display: none;
}

.plyr__control--overlaid {
	background: radial-gradient(
		circle,
		rgba(0, 0, 0, 0.4) 0%,
		rgba(0, 0, 0, 0.5) 50%
	);
}

.plyr__control:hover {
	background: none;
}

.plyr--video {
	border: 1px solid theme('colors.gray.200');
	border-radius: 8px;
}

:root {
	--plyr-range-fill-background: white;
	--plyr-video-control-background-hover: transparent;
}
</style>


