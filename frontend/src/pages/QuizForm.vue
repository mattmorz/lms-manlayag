<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div v-if="!readOnlyMode" class="flex items-center space-x-2">
			<Badge v-if="quizDetails.isDirty" theme="orange">
				{{ __('Not Saved') }}
			</Badge>
			<router-link
				v-if="quizDetails.doc?.name"
				:to="{
					name: 'QuizPage',
					params: {
						quizID: quizDetails.doc.name,
					},
				}"
			>
				<Button>
					<template #prefix>
						<ListChecks class="size-4 stroke-1.5" />
					</template>
					{{ __('Test Quiz') }}
				</Button>
			</router-link>
			<router-link
				v-if="quizDetails.doc?.name"
				:to="{
					name: 'QuizSubmissionList',
					params: {
						quizID: quizDetails.doc.name,
					},
				}"
			>
				<Button>
					<template #prefix>
						<ClipboardList class="size-4 stroke-1.5" />
					</template>
					{{ __('Check Submissions') }}
				</Button>
			</router-link>
			<Button variant="solid" @click="saveQuiz()">
				{{ __('Save') }}
			</Button>
		</div>
	</header>
	<div v-if="quizDetails.doc" class="py-5">
		<div class="px-20 pb-5 space-y-5 border-b mb-5">
			<div class="text-lg text-ink-gray-9 font-semibold mb-4">
				{{ __('Details') }}
			</div>
			<div class="grid grid-cols-2 gap-5">
				<div class="space-y-5">
					<FormControl
						v-model="quizDetails.doc.title"
						:label="__('Title')"
						:required="true"
					/>
					<FormControl
						type="number"
						v-model="quizDetails.doc.max_attempts"
						:label="__('Maximum Attempts')"
					/>
					<FormControl
						type="number"
						v-model="quizDetails.doc.duration"
						:label="__('Duration (in minutes)')"
					/>
				</div>
				<div class="space-y-5">
					<FormControl
						v-model="quizDetails.doc.total_marks"
						:label="__('Total Marks')"
						disabled
					/>
					<FormControl
						v-model="quizDetails.doc.passing_percentage"
						:label="__('Passing Percentage')"
						:required="true"
					/>
				</div>
			</div>
		</div>

		<div class="px-20 pb-5 space-y-5 border-b mb-5">
			<div class="text-lg text-ink-gray-9 font-semibold mb-4">
				{{ __('Settings') }}
			</div>
			<div class="grid grid-cols-3 gap-5">
				<div class="flex flex-col space-y-10">
					<FormControl
						v-model="quizDetails.doc.show_answers"
						type="checkbox"
						:label="__('Show Answers')"
					/>
					<FormControl
						v-model="quizDetails.doc.show_submission_history"
						type="checkbox"
						:label="__('Show Submission History')"
					/>
				</div>
				<div class="flex flex-col space-y-5">
					<FormControl
						v-model="quizDetails.doc.shuffle_questions"
						type="checkbox"
						:label="__('Shuffle Questions')"
					/>
					<FormControl
						v-if="quizDetails.doc.shuffle_questions"
						v-model="quizDetails.doc.limit_questions_to"
						:label="__('Limit Questions To')"
					/>
				</div>
				<div class="flex flex-col space-y-5">
					<FormControl
						v-model="quizDetails.doc.enable_negative_marking"
						type="checkbox"
						:label="__('Enable Negative Marking')"
					/>
					<FormControl
						v-if="quizDetails.doc.enable_negative_marking"
						v-model="quizDetails.doc.marks_to_cut"
						:label="__('Marks to Deduct')"
					/>
				</div>
			</div>
		</div>

		<div class="px-20 pb-5 space-y-5 mb-5">
			<div class="flex items-center justify-between mb-4">
				<div class="text-lg font-semibold text-ink-gray-9">
					{{ __('Questions') }}
				</div>
				<div class="flex items-center space-x-2">
					<Dropdown
						v-if="!readOnlyMode"
						:options="quizActionOptions"
					>
						<template v-slot="{ open }">
							<Button variant="ghost" class="p-1.5">
								<FeatherIcon name="more-vertical" class="w-4 h-4 text-ink-gray-7" />
							</Button>
						</template>
					</Dropdown>
					<Button v-if="!readOnlyMode" @click="openQuestionModal()">
						<template #prefix>
							<Plus class="w-4 h-4" />
						</template>
						{{ __('New Question') }}
					</Button>
				</div>
			</div>
			<ListView
				v-if="questions.length"
				:columns="questionColumns"
				:rows="questions"
				row-key="name"
				:options="{
					showTooltip: false,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in questionColumns" />
				</ListHeader>
				<ListRows>
					<ListRow
						:row="row"
						v-slot="{ idx, column, item }"
						v-for="row in questions"
						@click="openQuestionModal(row)"
						class="cursor-pointer"
					>
						<ListRowItem :item="item">
							<div
								v-if="column.key == 'question_detail'"
								class="text-xs truncate h-4"
								v-html="item"
							></div>
							<div v-else class="text-xs">
								{{ item }}
							</div>
						</ListRowItem>
					</ListRow>
				</ListRows>
				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="openSelectedExportModal(selections, unselectAll)"
							>
								<template #prefix>
									<Download class="h-4 w-4 stroke-1.5" />
								</template>
								{{ __('Export Selected') }}
							</Button>
							<Button
								variant="ghost"
								@click="deleteQuestions(selections, unselectAll)"
							>
								<Trash2 class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
			<div v-else class="text-ink-gray-6 text-sm">
				{{ __('No questions added yet') }}
			</div>
		</div>
	</div>

	<Question
		v-model="showQuestionModal"
		:questionDetail="currentQuestion"
		v-model:quiz="quizDetails"
		:title="
			currentQuestion.question
				? __('Edit the question')
				: __('Add a new question')
		"
	/>

	<Dialog
		v-model="showImportModal"
		:options="{
			title: __('Import Quiz'),
			size: 'md',
			actions: [
				{
					label: __('Import'),
					variant: 'solid',
					onClick: (dialog) => handleImport(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<FormControl
					type="select"
					:options="[
						{ label: 'GIFT Format', value: 'GIFT' },
						{ label: 'AIKEN Format', value: 'AIKEN' },
					]"
					v-model="importFormat"
					:label="__('Format Type')"
				/>
				<div class="mt-4">
					<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">{{ __('Select File') }}</label>
					<input
						type="file"
						ref="importFileInput"
						accept=".txt,.gift,.aiken"
						class="w-full border rounded-md p-2 text-sm bg-surface-white"
					/>
				</div>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showExportModal"
		:options="{
			title: __('Export Quiz'),
			size: 'md',
			actions: [
				{
					label: __('Export'),
					variant: 'solid',
					onClick: (dialog) => handleExport(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<FormControl
					type="select"
					:options="[
						{ label: 'GIFT Format', value: 'GIFT' },
						{ label: 'AIKEN Format', value: 'AIKEN' },
					]"
					v-model="exportFormat"
					:label="__('Format Type')"
				/>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showBankImportModal"
		:options="{
			title: __('Import from Question Bank'),
			size: '2xl',
			actions: [
				{
					label: __('Import'),
					variant: 'solid',
					onClick: (dialog) => handleBankQuestionsImport(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<FormControl
					type="select"
					v-model="selectedBank"
					:options="availableBanks"
					:label="__('Select Question Bank')"
					:placeholder="__('Choose a Question Bank')"
				/>

				<div v-if="selectedBank" class="space-y-4 mt-4">
					<div v-if="loadingBankQuestions" class="flex justify-center items-center py-6">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
					</div>
					<div v-else-if="!bankQuestions.length" class="text-ink-gray-5 text-sm py-4">
						{{ __('No questions available in this bank.') }}
					</div>
					<div v-else class="space-y-4">
						<div class="flex justify-between items-center">
							<TabButtons :buttons="importModeTabs" v-model="importMode" class="w-fit" />
							<span class="text-xs text-ink-gray-5">
								{{ __('Available: {0} questions').format(bankQuestions.length) }}
							</span>
						</div>

						<div v-if="importMode === 'random'">
							<FormControl
								type="number"
								v-model="randomCount"
								:label="__('Number of Questions')"
								:min="1"
								:max="bankQuestions.length"
							/>
						</div>
						<div v-else-if="importMode === 'manual'">
							<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">
								{{ __('Select Questions ({0} selected)').format(selectedQuestionNames.length) }}
							</label>
							<div class="border border-outline-gray-2 rounded-lg max-h-[35vh] overflow-y-auto p-2 bg-surface-gray-2 space-y-2">
								<div
									v-for="q in bankQuestions"
									:key="q.name"
									class="flex items-start gap-3 p-2 hover:bg-surface-white rounded transition-colors duration-200"
								>
									<input
										type="checkbox"
										v-model="selectedQuestionNames"
										:value="q.name"
										class="mt-1 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-ink-gray-9"
									/>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-surface-white border border-outline-gray-3 text-ink-gray-7">
												{{ q.type }}
											</span>
											<span class="text-[10px] text-ink-gray-4">
												{{ q.name }}
											</span>
										</div>
										<div class="prose-sm text-ink-gray-9" v-html="q.question"></div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<!-- Quiz Save Warning Modal -->
	<Dialog
		v-model="showQuizSaveWarningModal"
		:options="{
			size: 'md',
			actions: [
				{
					label: __('Create New Version'),
					variant: 'solid',
					onClick: () => handleCreateNewQuizVersion()
				},
				{
					label: __('Update Current Version'),
					variant: 'outline',
					onClick: () => {
						showQuizSaveWarningModal = false
						submitQuiz()
					}
				}
			]
		}"
	>
		<template #body-title>
			<div class="flex items-center gap-2">
				<AlertTriangle class="h-6 w-6 text-amber-500 flex-shrink-0" />
				<h3 class="text-lg font-semibold text-amber-900">
					{{ __('Attempts Found Warning') }}
				</h3>
			</div>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-sm text-ink-gray-6">
					{{ __('This quiz already contains student attempts. Creating a new version is highly recommended to preserve student records and grades.') }}
				</p>
				<FormControl
					v-model="quizVersionChangeLog"
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
	createResource,
	call,
	Dropdown,
	FormControl,
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	ListSelectBanner,
	Button,
	usePageMeta,
	toast,
	createDocumentResource,
	Badge,
	Dialog,
	TabButtons,
	FeatherIcon,
} from 'frappe-ui'
import {
	computed,
	reactive,
	ref,
	watch,
	onMounted,
	inject,
	onBeforeUnmount,
	onUpdated,
} from 'vue'
import { sessionStore } from '../stores/session'
import { AlertTriangle, ClipboardList, ListChecks, Plus, Trash2, Upload, Download } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { escapeHTML } from '@/utils'

import Question from '@/components/Modals/Question.vue'

const { brand } = sessionStore()
const showImportModal = ref(false)
const showExportModal = ref(false)
const importFormat = ref('GIFT')
const exportFormat = ref('GIFT')
const importFileInput = ref(null)

const showQuestionModal = ref(false)
const currentQuestion = reactive({
	question: '',
	marks: 0,
	name: '',
})
const user = inject('$user')
const router = useRouter()
const readOnlyMode = window.read_only_mode

const showQuizSaveWarningModal = ref(false)
const quizVersionChangeLog = ref('')

// Question Banks State
const showBankImportModal = ref(false)
const availableBanks = ref([])
const selectedBank = ref('')
const bankQuestions = ref([])
const loadingBankQuestions = ref(false)
const importMode = ref('random')
const randomCount = ref(1)
const selectedQuestionNames = ref([])

const importModeTabs = computed(() => [
	{ label: __('Random Selection'), value: 'random' },
	{ label: __('Manual Selection'), value: 'manual' },
])

const quizActionOptions = computed(() => [
	{
		label: __('Import Quiz'),
		icon: 'upload',
		onClick() {
			showImportModal.value = true
		},
	},
	{
		label: __('Export Quiz'),
		icon: 'download',
		onClick() {
			openExportModal()
		},
	},
	{
		label: __('From Question Bank'),
		icon: 'database',
		onClick() {
			openBankImportModal()
		},
	},
])

const openBankImportModal = () => {
	availableBanks.value = []
	selectedBank.value = ''
	bankQuestions.value = []
	selectedQuestionNames.value = []
	randomCount.value = 1
	importMode.value = 'random'
	showBankImportModal.value = true

	call('lms.lms.api.get_question_banks')
		.then(res => {
			if (res && res.length) {
				availableBanks.value = res.map(b => ({
					label: `${b.question_bank} (${b.question_count} ${b.question_count === 1 ? 'question' : 'questions'})`,
					value: b.question_bank,
				}))
			} else {
				availableBanks.value = []
				toast.info(__('No question banks found. Please create one in Quizzes first.'))
			}
		})
		.catch(err => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}

watch(selectedBank, (newBank) => {
	if (newBank) {
		loadingBankQuestions.value = true
		bankQuestions.value = []
		selectedQuestionNames.value = []
		randomCount.value = 1
		call('lms.lms.api.get_bank_questions', { bank_label: newBank })
			.then(res => {
				bankQuestions.value = res || []
			})
			.catch(err => {
				toast.error(err.messages?.[0] || err.message || err)
			})
			.finally(() => {
				loadingBankQuestions.value = false
			})
	} else {
		bankQuestions.value = []
		selectedQuestionNames.value = []
	}
})

const handleBankQuestionsImport = (dialog) => {
	if (!selectedBank.value) {
		toast.error(__('Please select a question bank'))
		return
	}

	let qNames = []

	if (importMode.value === 'random') {
		const count = parseInt(randomCount.value, 10)
		if (isNaN(count) || count <= 0) {
			toast.error(__('Please enter a valid number of questions'))
			return
		}
		if (count > bankQuestions.value.length) {
			toast.error(__('Cannot select more questions than available ({0})').format(bankQuestions.value.length))
			return
		}

		// Pick count questions randomly from bankQuestions
		const tempQuestions = [...bankQuestions.value]
		const picked = []
		while (picked.length < count && tempQuestions.length > 0) {
			const idx = Math.floor(Math.random() * tempQuestions.length)
			picked.push(tempQuestions.splice(idx, 1)[0].name)
		}
		qNames = picked
	} else {
		if (selectedQuestionNames.value.length === 0) {
			toast.error(__('Please select at least one question'))
			return
		}
		qNames = selectedQuestionNames.value
	}

	call('lms.lms.api.add_questions_to_quiz', {
		quiz_name: props.quizID,
		question_names: JSON.stringify(qNames),
		marks: 1
	})
		.then(res => {
			if (res.added_count > 0) {
				toast.success(__('Successfully added {0} questions.').format(res.added_count))
				quizDetails.reload()
			} else {
				toast.info(__('No new questions were added (all selected questions already exist in the quiz).'))
			}
			dialog.close()
		})
		.catch(err => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}


const props = defineProps({
	quizID: {
		type: String,
		required: true,
	},
})

const questions = computed(() => {
	return quizDetails.doc?.questions || []
})

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		router.push({ name: 'Courses' })
	}
	quizDetails.reload()
	window.addEventListener('keydown', keyboardShortcut)
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

onUpdated(() => {
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

const keyboardShortcut = (e) => {
	if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
		submitQuiz()
		e.preventDefault()
	}
}

onBeforeUnmount(() => {
	window.removeEventListener('keydown', keyboardShortcut)
})

const quizDetails = createDocumentResource({
	doctype: 'LMS Quiz',
	name: props.quizID,
	auto: false,
})

const validateTitle = () => {
	quizDetails.doc.title = escapeHTML(quizDetails.doc.title.trim())
}

const saveQuiz = () => {
	if (!quizDetails.doc?.name) return
	if (props.quizID === 'new') {
		submitQuiz()
		return
	}
	
	call('lms.lms.api.check_content_before_save', {
		content_doctype: 'LMS Quiz',
		content_name: props.quizID
	}).then(res => {
		if (res && res.has_submissions) {
			showQuizSaveWarningModal.value = true
		} else {
			submitQuiz()
		}
	}).catch(() => {
		submitQuiz()
	})
}

const handleCreateNewQuizVersion = () => {
	const log = quizVersionChangeLog.value.trim()
	if (!log) {
		toast.error(__('Please enter a change log description'))
		return
	}
	showQuizSaveWarningModal.value = false
	
	validateTitle()
	
	call('lms.lms.api.create_new_content_version', {
		content_doctype: 'LMS Quiz',
		content_name: props.quizID,
		change_log: log,
		doc_data: JSON.stringify({
			...quizDetails.doc,
			total_marks: calculateTotalMarks()
		})
	}).then(res => {
		toast.success(__('New version created successfully'))
		quizVersionChangeLog.value = ''
		
		router.push({
			name: 'QuizForm',
			params: { quizID: res.new_name }
		}).then(() => {
			window.location.reload()
		})
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to create new version'))
	})
}

const submitQuiz = () => {
	validateTitle()

	quizDetails.setValue.submit(
		{
			...quizDetails.doc,
			total_marks: calculateTotalMarks(),
		},
		{
			onSuccess(data) {
				quizDetails.doc.total_marks = data.total_marks
				toast.success(__('Quiz updated successfully'))
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
			},
		}
	)
}

const calculateTotalMarks = () => {
	let totalMarks = 0
	if (
		quizDetails.doc?.limit_questions_to &&
		quizDetails.doc?.questions.length > 0
	)
		return (
			quizDetails.doc.questions[0].marks * quizDetails.doc.limit_questions_to
		)

	quizDetails.doc?.questions.forEach((question) => {
		totalMarks += question.marks
	})
	return totalMarks
}

const questionColumns = computed(() => {
	return [
		{
			label: __('ID'),
			key: 'question',
			width: '10rem',
		},
		{
			label: __('Question'),
			key: __('question_detail'),
			width: '40rem',
		},
		{
			label: __('Marks'),
			key: 'marks',
			width: '5rem',
		},
	]
})

const openQuestionModal = (question = null) => {
	if (question) {
		currentQuestion.question = question.question
		currentQuestion.marks = question.marks
		currentQuestion.name = question.name
	} else {
		currentQuestion.question = ''
		currentQuestion.marks = 0
		currentQuestion.name = ''
	}
	showQuestionModal.value = true
}

const deleteQuestionResource = createResource({
	url: 'lms.lms.api.delete_documents',
	makeParams(values) {
		return {
			doctype: 'LMS Quiz Question',
			documents: values.questions,
		}
	},
})

const deleteQuestions = (selections, unselectAll) => {
	deleteQuestionResource.submit(
		{
			questions: Array.from(selections),
		},
		{
			onSuccess() {
				toast.success(__('Questions deleted successfully'))
				quizDetails.reload()
				unselectAll()
			},
		}
	)
}

const importQuizResource = createResource({
	url: 'lms.lms.api.import_quiz',
})

const exportQuizResource = createResource({
	url: 'lms.lms.api.export_quiz',
})

const selectedQuestionsToExport = ref([])
const currentUnselectAll = ref(null)

const openExportModal = () => {
	selectedQuestionsToExport.value = []
	currentUnselectAll.value = null
	showExportModal.value = true
}

const openSelectedExportModal = (selections, unselectAll) => {
	selectedQuestionsToExport.value = Array.from(selections)
	currentUnselectAll.value = unselectAll
	showExportModal.value = true
}

const handleImport = (dialog) => {
	const file = importFileInput.value?.files?.[0]
	if (!file) {
		toast.error(__('Please select a file to import'))
		return
	}

	const reader = new FileReader()
	reader.onload = (e) => {
		const content = e.target.result
		importQuizResource.submit(
			{
				quiz: props.quizID,
				file_content: content,
				format_type: importFormat.value,
			},
			{
				onSuccess() {
					toast.success(__('Quiz imported successfully'))
					quizDetails.reload()
					dialog.close()
				},
				onError(err) {
					toast.error(err.messages?.[0] || err)
				},
			}
		)
	}
	reader.readAsText(file)
}

const handleExport = (dialog) => {
	if (!quizDetails.doc?.questions || quizDetails.doc.questions.length === 0) {
		toast.error(__('This quiz has no questions to export'))
		return
	}
	const params = {
		quiz: props.quizID,
		format_type: exportFormat.value,
	}
	if (selectedQuestionsToExport.value.length > 0) {
		params.questions = JSON.stringify(selectedQuestionsToExport.value)
	}

	exportQuizResource.submit(
		params,
		{
			onSuccess(content) {
				const exportData = content || exportQuizResource.data
				if (!exportData) {
					toast.error(__('No content received from server'))
					return
				}
				const blob = new Blob([exportData], { type: 'text/plain' })
				const url = URL.createObjectURL(blob)
				const downloadAnchor = document.createElement('a')
				downloadAnchor.href = url
				downloadAnchor.download = `${quizDetails.doc.title || props.quizID}_export.txt`
				document.body.appendChild(downloadAnchor)
				downloadAnchor.click()
				downloadAnchor.remove()
				URL.revokeObjectURL(url)
				toast.success(__('Quiz exported successfully'))
				
				if (currentUnselectAll.value) {
					currentUnselectAll.value()
					currentUnselectAll.value = null
				}
				dialog.close()
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
			},
		}
	)
}

const breadcrumbs = computed(() => {
	let crumbs = [
		{
			label: __('Quizzes'),
			route: {
				name: 'Quizzes',
			},
		},
	]

	crumbs.push({
		label: quizDetails.doc?.title,
		route: { name: 'QuizForm', params: { quizID: props.quizID } },
	})
	return crumbs
})

usePageMeta(() => {
	return {
		title: quizDetails.doc?.title,
		icon: brand.favicon,
	}
})
</script>
