<template>
	<div class="">
		<div class="grid md:grid-cols-[75%,25%] h-screen">
			<div class="border-r">
				<header
					class="sticky top-0 z-10 flex flex-col md:flex-row md:items-center justify-between border-b overflow-hidden bg-surface-white px-3 py-2.5 sm:px-5"
				>
					<Breadcrumbs class="text-ellipsis" :items="breadcrumbs" />
					<Button
						variant="solid"
						@click="saveLesson({ showSuccessMessage: true })"
						class="mt-3 md:mt-0"
					>
						{{ __('Save') }}
					</Button>
				</header>
				<div class="py-5">
					<div class="w-5/6 mx-auto">
						<FormControl
							v-model="lesson.title"
							label="Title"
							class="mb-4"
							:required="true"
						/>

						<div class="grid grid-cols-3 gap-6">
							<!-- Left Column -->
							<div class="col-span-1">
								<FormControl
									v-model="lesson.include_in_preview"
									type="checkbox"
									label="Include in Preview"
								/>
							</div>

							<!-- Right Column -->
							<div class="col-span-2">
								<FormControl
									v-model="lesson.require_quiz_pass"
									type="checkbox"
									:label="__('Require Quiz Pass')"
								/>

								<MultiSelect
									v-if="lesson.require_quiz_pass"
									v-model="requiredQuizzes"
									doctype="LMS Quiz"
									:label="__('Quizzes to Pass')"
									:required="true"
									class="mt-3"
								/>
							</div>
						</div>

						<div class="grid grid-cols-3 gap-6 mt-4 pt-4 border-t border-dashed">
							<!-- Left Column (Exclusion) -->
							<div class="col-span-1">
								<FormControl
									v-model="lesson.exclude_from_course"
									type="checkbox"
									:label="__('Exclude from Course')"
								/>
							</div>

							<!-- Right Column (Scheduling) -->
							<div class="col-span-2">
								<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">{{ __('Scheduled Release') }}</label>
								<div class="grid grid-cols-2 gap-4">
									<FormControl
										type="date"
										v-model="lesson.release_date"
										:label="__('Release Date')"
									/>
									<FormControl
										type="time"
										v-model="lesson.release_time"
										:label="__('Release Time')"
									/>
								</div>
							</div>
						</div>
					</div>
					<div class="border-t mt-4">
						<div class="w-5/6 mx-auto pt-4">
							<div
								class="flex justify-between cursor-pointer"
								@click="
									() => {
										openInstructorEditor = !openInstructorEditor
									}
								"
							>
								<label class="block font-medium text-ink-gray-5 mb-1">
									{{ __('Instructor Notes') }}
								</label>
								<ChevronRight
									class="stroke-2 h-5 w-5 text-ink-gray-5"
									:class="{
										'rotate-90 transform duration-200': openInstructorEditor,
										'duration-200': !openInstructorEditor,
									}"
								/>
							</div>
							<div
								v-show="openInstructorEditor"
								id="instructor-notes"
								class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal py-3"
							></div>
						</div>
					</div>
					<div class="border-t mt-4">
						<div class="w-5/6 mx-auto pt-4">
							<label class="block font-medium text-ink-gray-5 mb-1">
								{{ __('Content') }}
							</label>
							<div
								id="content"
								class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal py-3"
							></div>
						</div>
					</div>
				</div>
			</div>
			<div class="">
				<div class="sticky top-0 p-5">
					<LessonHelp />
				</div>
			</div>
		</div>
	</div>

	<!-- Lesson Save Warning Modal -->
	<Dialog
		v-model="showLessonSaveWarningModal"
		:options="{
			size: 'md',
			actions: [
				{
					label: __('Create New Version'),
					variant: 'solid',
					onClick: () => handleCreateNewLessonVersion()
				},
				{
					label: __('Update Current Version'),
					variant: 'outline',
					onClick: () => {
						showLessonSaveWarningModal = false
						editCurrentLesson()
					}
				}
			]
		}"
	>
		<template #body-title>
			<div class="flex items-center gap-2">
				<AlertTriangle class="h-6 w-6 text-amber-500 flex-shrink-0" />
				<h3 class="text-lg font-semibold text-amber-900">
					{{ __('Shared Content Warning') }}
				</h3>
			</div>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-sm text-ink-gray-6">
					{{ __('This lesson is currently used in {0} courses. Modifying it directly will affect all linked courses. Creating a new version is highly recommended.', [sharedCoursesCount]) }}
				</p>
				<FormControl
					v-model="lessonVersionChangeLog"
					:label="__('Change Log Description')"
					type="textarea"
					placeholder="Describe the changes in this version..."
					:required="true"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Breadcrumbs,
	Button,
	call,
	createResource,
	FormControl,
	usePageMeta,
	toast,
} from 'frappe-ui'
import {
	computed,
	reactive,
	onMounted,
	inject,
	ref,
	onBeforeUnmount,
	onUpdated,
} from 'vue'
import { sessionStore } from '../stores/session'
import EditorJS from '@editorjs/editorjs'
import LessonHelp from '@/components/LessonHelp.vue'
import MultiSelect from '@/components/Controls/MultiSelect.vue'
import { AlertTriangle, ChevronRight } from 'lucide-vue-next'
import { getEditorTools, enablePlyr } from '@/utils'
import { useOnboarding, useTelemetry } from 'frappe-ui/frappe'
import { useRoute } from 'vue-router'

const { brand } = sessionStore()
const editor = ref(null)
const instructorEditor = ref(null)
const user = inject('$user')
const route = useRoute()
const openInstructorEditor = ref(false)
const requiredQuizzes = ref([])
const { capture } = useTelemetry()
const { updateOnboardingStep } = useOnboarding('learning')
const showLessonSaveWarningModal = ref(false)
const sharedCoursesCount = ref(0)
const lessonVersionChangeLog = ref('')
let autoSaveInterval
let showSuccessMessage = false

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

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		window.location.href = '/login'
	}
	capture('lesson_form_opened')
	window.addEventListener('keydown', keyboardShortcut)
	enablePlyr()
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

onUpdated(() => {
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

const renderEditor = (holder, toolOptions = { allowAssessments: true }) => {
	return new EditorJS({
		holder: holder,
		tools: getEditorTools(toolOptions),
		defaultBlock: 'markdown',
		onChange: async (api, event) => {
			enablePlyr()
		},
		onReady: () => {
			if (window.triggerMathJax) {
				window.triggerMathJax()
			}
		}
	})
}

const getAssessmentBlockTypes = (content) => {
	if (!content) {
		return new Set()
	}

	try {
		const parsedContent = JSON.parse(content)
		const blockTypes = new Set()
		for (const block of parsedContent.blocks || []) {
			if (['quiz', 'assignment', 'program'].includes(block.type)) {
				blockTypes.add(block.type)
			}
		}
		return blockTypes
	} catch {
		return new Set()
	}
}

const getEditorToolOptions = (lessonData) => {
	const contentBlockTypes = getAssessmentBlockTypes(lessonData?.content)
	const instructorBlockTypes = getAssessmentBlockTypes(
		lessonData?.instructor_content
	)
	const hasAssessmentBlocks =
		contentBlockTypes.size > 0 || instructorBlockTypes.size > 0

	if (route.query.mode === 'assessment' || hasAssessmentBlocks) {
		return {
			allowAssessments: true,
			allowQuiz: true,
			allowAssignment: true,
			allowProgram: true,
		}
	}

	if (route.query.mode === 'lesson') {
		return {
			allowAssessments: true,
			allowQuiz: true,
			allowAssignment: false,
			allowProgram: false,
		}
	}

	if (!lessonData) {
		return {
			allowAssessments: false,
			allowQuiz: false,
			allowAssignment: false,
			allowProgram: false,
		}
	}

	return {
		allowAssessments: true,
		allowQuiz: true,
		allowAssignment: false,
		allowProgram: false,
	}
}

const initEditors = (toolOptions) => {
	if (!editor.value) {
		editor.value = renderEditor('content', toolOptions)
	}

	if (!instructorEditor.value) {
		instructorEditor.value = renderEditor('instructor-notes', toolOptions)
	}
}

const lesson = reactive({
	title: '',
	include_in_preview: false,
	body: '',
	instructor_notes: '',
	content: '',
	quiz_id: '',
	require_quiz_pass: false,
	exclude_from_course: false,
	release_date: '',
	release_time: '',
})

const lessonDetails = createResource({
	url: 'lms.lms.utils.get_lesson_creation_details',
	params: {
		course: props.courseName,
		chapter: props.chapterNumber,
		lesson: props.lessonNumber,
	},
	auto: true,
	onSuccess(data) {
		initEditors(getEditorToolOptions(data.lesson))
		if (data.lesson) {
			window.current_lesson_name = data.lesson.name
			Object.keys(data.lesson).forEach((key) => {
				lesson[key] = data.lesson[key]
			})
			lesson.include_in_preview = data?.lesson?.include_in_preview
				? true
				: false
			lesson.require_quiz_pass = data?.lesson?.require_quiz_pass ? true : false
			lesson.exclude_from_course = data?.lesson?.exclude_from_course ? true : false
			lesson.release_date = data?.lesson?.release_date || ''
			lesson.release_time = data?.lesson?.release_time || ''
			requiredQuizzes.value = getRequiredQuizzes(data?.lesson?.quiz_id)
			addLessonContent(data)
			addInstructorNotes(data)
			enableAutoSave()
		}
	},
})

const addLessonContent = (data) => {
	editor.value.isReady.then(() => {
		if (data.lesson.content) {
			editor.value.render(JSON.parse(data.lesson.content))
		} else if (data.lesson.body) {
			let blocks = convertToJSON(data.lesson)
			editor.value.render({
				blocks: blocks,
			})
		}
	})
}

const addInstructorNotes = (data) => {
	instructorEditor.value.isReady.then(() => {
		if (data.lesson.instructor_content) {
			instructorEditor.value.render(JSON.parse(data.lesson.instructor_content))
		} else if (data.lesson.instructor_notes) {
			let blocks = convertToJSON(data.lesson)
			instructorEditor.value.render({
				blocks: blocks,
			})
		}
	})
}

const enableAutoSave = () => {
	autoSaveInterval = setInterval(() => {
		saveLesson({ showSuccessMessage: false })
	}, 10000)
}

const keyboardShortcut = (e) => {
	if (
		e.key === 's' &&
		(e.ctrlKey || e.metaKey) &&
		!e.target.classList.contains('ProseMirror')
	) {
		saveLesson({ showSuccessMessage: true })
		e.preventDefault()
	}
}

onBeforeUnmount(() => {
	clearInterval(autoSaveInterval)
	window.removeEventListener('keydown', keyboardShortcut)
})

const newLessonResource = createResource({
	url: 'frappe.client.insert',
	makeParams(values) {
		return {
			doc: {
				doctype: 'Course Lesson',
				course: props.courseName,
				chapter: lessonDetails.data?.chapter.name,
				...lesson,
			},
		}
	},
})

const editLesson = createResource({
	url: 'frappe.client.set_value',
	makeParams(values) {
		return {
			doctype: 'Course Lesson',
			name: values.lesson,
			fieldname: lesson,
		}
	},
})

const lessonReference = createResource({
	url: 'frappe.client.insert',
	makeParams(values) {
		return {
			doc: {
				doctype: 'Lesson Reference',
				parent: lessonDetails.data?.chapter.name,
				parenttype: 'Course Chapter',
				parentfield: 'lessons',
				lesson: values.lesson,
				idx: props.lessonNumber,
			},
		}
	},
})

const convertToJSON = (lessonData) => {
	let blocks = []
	if (lessonData.youtube) {
		let youtubeID = lessonData.youtube.split('/').pop()
		blocks.push({
			type: 'embed',
			data: {
				service: 'youtube',
				embed: `https://www.youtube.com/embed/${youtubeID}`,
			},
		})
	}
	lessonData.body.split('\n').forEach((block) => {
		if (block.includes('{{ YouTubeVideo')) {
			let youtubeID = block.match(/\(["']([^"']+?)["']\)/)[1]
			if (!youtubeID.includes('https://'))
				youtubeID = `https://www.youtube.com/embed/${youtubeID}`
			blocks.push({
				type: 'embed',
				data: {
					service: 'youtube',
					embed: youtubeID,
				},
			})
		} else if (block.includes('{{ Quiz')) {
			let quiz = block.match(/\(["']([^"']+?)["']\)/)[1]
			blocks.push({
				type: 'quiz',
				data: {
					quiz: quiz,
				},
			})
		} else if (block.includes('{{ Video')) {
			let video = block.match(/\(["']([^"']+?)["']\)/)[1]
			blocks.push({
				type: 'upload',
				data: {
					file_url: video,
					file_type: video.split('.').pop(),
				},
			})
		} else if (block.includes('{{ Audio')) {
			let audio = block.match(/\(["']([^"']+?)["']\)/)[1]
			blocks.push({
				type: 'upload',
				data: {
					file_url: audio,
					file_type: audio.split('.').pop(),
				},
			})
		} else if (block.includes('{{ PDF')) {
			let pdf = block.match(/\(["']([^"']+?)["']\)/)[1]
			blocks.push({
				type: 'upload',
				data: {
					file_url: pdf,
					file_type: 'pdf',
				},
			})
		} else if (block.includes('{{ Embed')) {
			let embed = block.match(/\(["']([^"']+?)["']\)/)[1]
			blocks.push({
				type: 'embed',
				data: {
					service: embed.split('|||')[0],
					embed: embed.split('|||')[1],
				},
			})
		} else if (block.includes('![]')) {
			let image = block.match(/\((.*?)\)/)[1]
			blocks.push({
				type: 'upload',
				data: {
					file_url: image,
					file_type: 'image',
				},
			})
		} else if (block.includes('#')) {
			let level = (block.match(/#/g) || []).length
			blocks.push({
				type: 'header',
				data: {
					text: block.replace(/#/g, '').trim(),
					level: level,
				},
			})
		} else {
			blocks.push({
				type: 'paragraph',
				data: {
					text: block,
				},
			})
		}
	})

	if (lessonData.quizId) {
		blocks.push({
			type: 'quiz',
			data: {
				quiz: lessonData.quizId,
			},
		})
	}

	return blocks
}

const saveLesson = (e) => {
	showSuccessMessage = false
	if (typeof e != 'undefined' && e.showSuccessMessage) {
		showSuccessMessage = true
	}
	updateQuizGateFields()
	editor.value.save().then((outputData) => {
		outputData = removeEmptyBlocks(outputData)
		lesson.content = JSON.stringify(outputData)
		instructorEditor.value.save().then((outputData) => {
			outputData = removeEmptyBlocks(outputData)
			lesson.instructor_content = JSON.stringify(outputData)
			if (lessonDetails.data?.lesson) {
				checkAndSaveLesson()
			} else {
				createNewLesson()
			}
		})
	})
}

const checkAndSaveLesson = () => {
	call('lms.lms.api.check_content_before_save', {
		content_doctype: 'Course Lesson',
		content_name: lessonDetails.data.lesson.name
	}).then(res => {
		if (res && res.is_shared) {
			sharedCoursesCount.value = res.usage_count
			showLessonSaveWarningModal.value = true
		} else {
			editCurrentLesson()
		}
	}).catch(() => {
		editCurrentLesson()
	})
}

const handleCreateNewLessonVersion = () => {
	const log = lessonVersionChangeLog.value.trim()
	if (!log) {
		toast.error(__('Please enter a change log description'))
		return
	}
	showLessonSaveWarningModal.value = false
	
	call('lms.lms.api.create_new_content_version', {
		content_doctype: 'Course Lesson',
		content_name: lessonDetails.data.lesson.name,
		change_log: log,
		doc_data: JSON.stringify(lesson),
		course: props.courseName,
		chapter: lessonDetails.data.chapter.name
	}).then(res => {
		toast.success(__('New version created and linked successfully'))
		lessonVersionChangeLog.value = ''
		lessonDetails.reload()
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to create new version'))
	})
}

const removeEmptyBlocks = (outputData) => {
	let blocks = outputData.blocks.filter((block) => {
		return Object.keys(block.data).length > 0 || block.type == 'paragraph'
	})
	outputData.blocks = blocks
	return outputData
}

const createNewLesson = () => {
	newLessonResource.submit(
		{},
		{
			validate() {
				return validateLesson()
			},
			onSuccess(data) {
				lessonReference.submit(
					{ lesson: data.name },
					{
						onSuccess() {
							if (user.data?.is_system_manager)
								updateOnboardingStep('create_first_lesson')

							capture('lesson_created')
							toast.success(
								route.query.mode === 'assessment'
									? __('Activity created successfully')
									: __('Lesson created successfully')
							)
							lessonDetails.reload()
						},
					}
				)
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
			},
		}
	)
}

const editCurrentLesson = () => {
	editLesson.submit(
		{
			lesson: lessonDetails.data.lesson.name,
		},
		{
			validate() {
				return validateLesson()
			},
			onSuccess() {
				showSuccessMessage
					? toast.success(
							route.query.mode === 'assessment'
								? __('Activity updated successfully')
								: __('Lesson updated successfully')
					  )
					: ''
			},
			onError(err) {
				toast.error(err.message)
			},
		}
	)
}

const validateLesson = () => {
	if (!lesson.title) {
		return 'Title is required'
	}
	if (!lesson.content) {
		return 'Content is required'
	}
	if (lesson.require_quiz_pass && !requiredQuizzes.value.length) {
		return 'Select at least one quiz to require before the next lesson'
	}
}

const getRequiredQuizzes = (quizId) => {
	if (!quizId) return []
	return quizId
		.split(',')
		.map((quiz) => quiz.trim())
		.filter(Boolean)
}

const updateQuizGateFields = () => {
	lesson.quiz_id = requiredQuizzes.value.join(', ')
}

const breadcrumbs = computed(() => {
	let crumbs = [
		{
			label: __('Courses'),
			route: { name: 'Courses' },
		},
		{
			label: lessonDetails.data?.course_title,
			route: {
				name: 'CourseDetail',
				params: { courseName: props.courseName },
				hash: '#settings',
			},
		},
	]

	if (lessonDetails?.data?.lesson) {
		crumbs.push({
			label: lessonDetails.data.lesson.title,
			route: {
				name: 'Lesson',
				params: {
					courseName: props.courseName,
					chapterNumber: props.chapterNumber,
					lessonNumber: props.lessonNumber,
				},
			},
		})
	}
	crumbs.push({
		label: lessonDetails?.data?.lesson
			? (route.query.mode === 'assessment' ? __('Edit Activity') : __('Edit Lesson'))
			: (route.query.mode === 'assessment' ? __('Create Activity') : __('Create Lesson')),
		route: {
			name: 'LessonForm',
			params: {
				courseName: props.courseName,
				chapterNumber: props.chapterNumber,
				lessonNumber: props.lessonNumber,
			},
		},
	})
	return crumbs
})

usePageMeta(() => {
	return {
		title: lessonDetails?.data?.lesson
			? lessonDetails.data.lesson.title
			: (route.query.mode === 'assessment' ? __('New Activity') : __('New Lesson')),
		icon: brand.favicon,
	}
})
</script>
<style>
.embed-tool__caption,
.cdx-simple-image__caption {
	display: none;
}

.ce-block__content {
	max-width: none;
}

.codex-editor--narrow .ce-toolbar__actions {
	right: 100%;
}

.ce-toolbar__content {
	max-width: none;
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

.prose :where(pre):not(:where([class~='not-prose'], [class~='not-prose'] *)) {
	overflow-x: unset;
}

iframe {
	border: none !important;
}

.tc-table {
	border-left: 1px solid #e8e8eb;
}

.ce-toolbox__button[data-tool='markdown'] {
	display: none !important;
}

.ce-popover-item[data-item-name='markdown'] {
	display: none !important;
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

.ce-popover__container {
	border-radius: 12px;
	padding: 8px;
}

.codex-editor--narrow .ce-toolbox .ce-popover,
.codex-editor--narrow .ce-toolbar__actions .ce-popover {
	right: unset;
	left: initial;
}

.ce-popover {
	border-radius: 12px;
}

.cdx-search-field {
	border: none;
}

.cdx-search-field__input {
	font-weight: 400;
	font-size: 13px;
}

.cdx-search-field__input::before {
	font-weight: 400;
}

.cdx-search-field__input:focus {
	--tw-ring-color: theme('colors.gray.100');
}

.ce-popover-item__title {
	font-size: 13px;
	font-weight: 400;
}

.ce-popover-item__icon svg {
	width: 15px;
	height: 15px;
}

.ce-popover--opened > .ce-popover__container {
	max-height: unset;
}

.cdx-search-field__icon svg {
	width: 15px;
	height: 15px;
}

.cdx-search-field__icon {
	margin-right: 5px;
}

.cdx-block.embed-tool {
	position: relative;
	display: inline-block;
	width: 100%;
}

:root {
	--plyr-range-fill-background: white;
	--plyr-video-control-background-hover: transparent;
}
</style>
