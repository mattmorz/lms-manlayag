<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<Button v-if="!readOnlyMode && currentTab === 'quizzes'" variant="solid" @click="showForm = true">
			<template #prefix>
				<Plus class="w-4 h-4" />
			</template>
			{{ __('Create') }}
		</Button>
		<Button v-else-if="!readOnlyMode && currentTab === 'banks'" variant="solid" @click="showImportModal = true">
			<template #prefix>
				<FeatherIcon name="upload" class="w-4 h-4" />
			</template>
			{{ __('Import Bank') }}
		</Button>
	</header>
	<div class="py-5 mx-5">
		<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
			<TabButtons :buttons="quizTabs" v-model="currentTab" class="w-fit" />
			<FormControl v-model="search" type="text" placeholder="Search" class="w-full sm:w-64">
				<template #prefix>
					<FeatherIcon name="search" class="size-4 text-ink-gray-5" />
				</template>
			</FormControl>
		</div>

		<div v-if="currentTab === 'quizzes'">
			<ListView
				v-if="quizzes.data?.length"
				:columns="quizColumns"
				:rows="transformedQuizzes"
				row-key="name"
				:options="{ showTooltip: false, selectable: true }"
			>
				<ListHeader
					class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in quizColumns">
						<template #prefix="{ item }">
							<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<router-link
						v-for="row in transformedQuizzes"
						:to="{
							name: 'QuizForm',
							params: {
								quizID: row.name,
							},
						}"
					>
						<ListRow :row="row">
							<template #default="{ column, item }">
								<ListRowItem :item="row[column.key]" :align="column.align">
									<div v-if="column.key == 'show_answers'">
										<FormControl
											type="checkbox"
											v-model="row[column.key]"
											:disabled="true"
										/>
									</div>
									<div v-else-if="column.key == 'used_in'" class="flex flex-wrap gap-1.5 max-w-xs">
										<Badge
											v-for="course in row[column.key].slice(0, 2)"
											:key="course"
											theme="gray"
										>
											{{ course }}
										</Badge>
										<Badge
											v-if="row[column.key].length > 2"
											theme="gray"
											:title="row[column.key].slice(2).join(', ')"
										>
											+{{ row[column.key].length - 2 }}
										</Badge>
										<span v-if="!row[column.key]?.length" class="text-ink-gray-4 text-xs font-normal">
											{{ __('Not Used') }}
										</span>
									</div>
									<div
										v-else-if="column.key == 'modified'"
										class="text-xs text-ink-gray-5"
									>
										{{ row[column.key] }}
									</div>
									<div v-else>
										{{ row[column.key] }}
									</div>
								</ListRowItem>
							</template>
						</ListRow>
					</router-link>
				</ListRows>
				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="deleteQuiz(selections, unselectAll)"
							>
								<FeatherIcon name="trash-2" class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
			<EmptyState v-else type="Quizzes" />
			<div v-if="quizzes.hasNextPage" class="flex justify-center my-5">
				<Button @click="quizzes.next()">
					{{ __('Load More') }}
				</Button>
			</div>
		</div>

		<div v-else-if="currentTab === 'banks'">
			<div v-if="filteredBanks.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				<div
					v-for="bank in filteredBanks"
					:key="bank.question_bank"
					@click="openBankQuestions(bank.question_bank)"
					class="cursor-pointer bg-white border border-outline-gray-2 rounded-xl p-5 hover:bg-surface-gray-2 transition-all duration-200 flex items-center justify-between gap-4"
				>
					<div class="flex items-center gap-4 min-w-0">
						<div class="bg-surface-gray-2 p-3 rounded-lg text-ink-gray-7">
							<FeatherIcon name="database" class="w-6 h-6 stroke-1.5" />
						</div>
						<div class="min-w-0">
							<div class="font-semibold text-ink-gray-9 text-base truncate">
								{{ bank.question_bank }}
							</div>
							<div class="text-sm text-ink-gray-5 mt-0.5 flex items-center gap-1.5 flex-wrap">
								<span>
									{{ bank.question_count }} {{ bank.question_count === 1 ? __('Question') : __('Questions') }}
								</span>
								<span v-if="bank.shared_count !== undefined" class="text-ink-gray-4">
									•
								</span>
								<span v-if="bank.shared_count !== undefined">
									{{ bank.shared_count === -1 ? __('Private') : bank.shared_count === 0 ? __('Shared with all') : bank.shared_count === 1 ? __('Shared with 1 instructor') : __('Shared with {0} instructors').format(bank.shared_count) }}
								</span>
							</div>
						</div>
					</div>
					<div class="flex items-center gap-2">
						<Button
							v-if="!readOnlyMode && canManageBankCard(bank)"
							variant="ghost"
							class="text-ink-gray-6 hover:bg-surface-gray-2 p-1 rounded"
							@click.stop="openShareModal(bank)"
						>
							<FeatherIcon name="share-2" class="w-4 h-4 text-ink-gray-5" />
						</Button>
						<Button
							v-if="!readOnlyMode && canManageBankCard(bank)"
							variant="ghost"
							class="text-red-600 hover:bg-red-50 hover:text-red-800 p-1 rounded"
							@click.stop="confirmDeleteBank(bank.question_bank)"
						>
							<FeatherIcon name="trash-2" class="w-4 h-4 text-red-500" />
						</Button>
						<FeatherIcon name="chevron-right" class="w-5 h-5 text-ink-gray-4" />
					</div>
				</div>
			</div>
			<div v-else class="flex flex-col items-center justify-center py-20 bg-white rounded-xl">
				<FeatherIcon name="database" class="w-12 h-12 text-ink-gray-3 mb-3" />
				<div class="text-ink-gray-7 font-medium text-lg mb-1">{{ __('No Question Banks') }}</div>
				<div class="text-ink-gray-5 text-sm text-center max-w-sm px-4">
					{{ __('Import Aiken or GIFT files to create your first question bank and start building quizzes faster.') }}
				</div>
				<Button
					v-if="!readOnlyMode"
					variant="solid"
					class="mt-4"
					@click="showImportModal = true"
				>
					<template #prefix>
						<Plus class="w-4 h-4" />
					</template>
					{{ __('Import Bank') }}
				</Button>
			</div>
		</div>
	</div>
	<Dialog
		v-model="showForm"
		:options="{
			title: __('Create a Quiz'),
			size: 'sm',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick({ close }) {
						insertQuiz(close)
					},
				},
			],
		}"
	>
		<template #body-content>
			<FormControl
				v-model="title"
				:label="__('Title')"
				type="text"
				@keydown.enter="insertQuiz(() => (showForm = false))"
			/>
		</template>
	</Dialog>

	<Dialog
		v-model="showImportModal"
		:options="{
			title: __('Import Question Bank'),
			size: 'md',
			actions: [
				{
					label: __('Import'),
					variant: 'solid',
					onClick: (dialog) => handleBankImport(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<FormControl
					v-model="bankLabel"
					:label="__('Bank Label')"
					type="text"
					:required="true"
					placeholder="e.g. Science 101"
				/>
				<FormControl
					type="select"
					:options="[
						{ label: 'GIFT Format', value: 'GIFT' },
						{ label: 'AIKEN Format', value: 'AIKEN' },
					]"
					v-model="importFormat"
					:label="__('Format Type')"
				/>
				<FormControl
					v-model="isShared"
					type="checkbox"
					:label="__('Share with others')"
				/>
				<MultiSelect
					v-if="isShared"
					v-model="sharedWith"
					doctype="User"
					searchUrl="lms.lms.api.get_lms_staff_users"
					:label="__('Instructors to share with')"
				/>
				<div class="mt-4">
					<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">{{ __('Select File') }}</label>
					<input
						type="file"
						ref="bankFileInput"
						accept=".txt,.gift,.aiken"
						class="w-full border rounded-md p-2 text-sm bg-surface-white"
					/>
				</div>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showViewBankQuestionsDialog"
		:options="{
			title: selectedBank ? __('Question Bank: {0}').format(selectedBank) : __('Question Bank'),
			size: '3xl',
		}"
	>
		<template #body-content>
			<div class="flex justify-between items-center mb-4 border-b pb-3">
				<div class="text-xs text-ink-gray-5 font-medium">
					{{ bankQuestions.length }} {{ bankQuestions.length === 1 ? __('Question') : __('Questions') }}
				</div>
				<Button
					v-if="canManageBank"
					variant="solid"
					size="sm"
					@click="openAddBankQuestion()"
				>
					<template #prefix>
						<Plus class="w-3.5 h-3.5" />
					</template>
					{{ __('Add Question') }}
				</Button>
			</div>
			<div v-if="loadingBankQuestions" class="flex justify-center items-center py-10">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
			</div>
			<div v-else-if="!bankQuestions.length" class="text-center py-8 text-ink-gray-5">
				{{ __('No questions found in this question bank.') }}
			</div>
			<div v-else class="max-h-[60vh] overflow-y-auto space-y-4 pr-2">
				<div
					v-for="(q, idx) in bankQuestions"
					:key="q.name"
					class="p-4 border border-outline-gray-2 rounded-lg bg-surface-gray-2 flex items-start justify-between gap-3"
				>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-xs font-semibold px-2 py-0.5 rounded bg-surface-white border border-outline-gray-3 text-ink-gray-7">
								{{ q.type }}
							</span>
							<span class="text-xs text-ink-gray-4">
								{{ q.name }}
							</span>
						</div>
						<div class="prose-sm text-ink-gray-9 leading-relaxed" v-html="formatQuizText(q.question)"></div>
					</div>
					<div v-if="canManageBank" class="flex items-center gap-1 mt-1 shrink-0">
						<Button
							variant="ghost"
							class="text-ink-gray-7 hover:bg-surface-gray-3 p-1 rounded"
							@click="openEditBankQuestion(q.name)"
						>
							<FeatherIcon name="edit-2" class="w-4 h-4 text-ink-gray-6" />
						</Button>
						<Button
							variant="ghost"
							class="text-red-600 hover:bg-red-50 hover:text-red-800 p-1 rounded"
							@click="confirmDeleteQuestion(q.name, idx)"
						>
							<FeatherIcon name="trash-2" class="w-4 h-4 text-red-500" />
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showEditBankQuestionDialog"
		:options="{
			title: editingBankQuestion ? __('Edit Question') : __('Add Question to Bank'),
			size: '4xl',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: (dialog) => handleSaveBankQuestion(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div v-if="loadingQuestionForm" class="flex justify-center items-center py-10">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
			</div>
			<div v-else class="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
				<div>
					<label class="block text-xs font-medium text-ink-gray-5 mb-1">
						{{ __('Question') }}
					</label>
					<TextEditor
						:content="editingBankQuestionForm.question"
						@change="(val) => (editingBankQuestionForm.question = val)"
						:fixedMenu="true"
						editorClass="prose-sm max-w-none border border-outline-gray-2 bg-surface-white rounded-md py-1.5 px-3 min-h-[6rem]"
					/>
				</div>

				<FormControl
					:label="__('Question Type')"
					v-model="editingBankQuestionForm.type"
					type="select"
					:options="['Choices', 'User Input', 'Open Ended']"
				/>

				<div v-if="editingBankQuestionForm.type === 'Choices'" class="space-y-4 pt-2">
					<div class="text-sm font-semibold text-ink-gray-9 border-b pb-1">
						{{ __('Options & Answers') }}
					</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div v-for="n in 4" :key="n" class="p-3 border border-outline-gray-2 rounded-lg bg-surface-white space-y-2">
							<FormControl
								:label="__('Option {0}').format(n)"
								v-model="editingBankQuestionForm[`option_${n}`]"
								:required="n <= 2"
							/>
							<FormControl
								:label="__('Explanation')"
								v-model="editingBankQuestionForm[`explanation_${n}`]"
							/>
							<FormControl
								:label="__('Is Correct')"
								v-model="editingBankQuestionForm[`is_correct_${n}`]"
								type="checkbox"
							/>
						</div>
					</div>
				</div>

				<div v-else-if="editingBankQuestionForm.type === 'User Input'" class="space-y-4 pt-2">
					<div class="text-sm font-semibold text-ink-gray-9 border-b pb-1">
						{{ __('Possible Accepted Answers') }}
					</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div v-for="n in 4" :key="n">
							<FormControl
								:label="__('Possibility {0}').format(n)"
								v-model="editingBankQuestionForm[`possibility_${n}`]"
								:required="n === 1"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showShareModal"
		:options="{
			title: bankToShare ? __('Share Question Bank: {0}').format(bankToShare.question_bank) : __('Share Question Bank'),
			size: 'md',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: (dialog) => handleSaveShare(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<FormControl
					v-model="shareIsShared"
					type="checkbox"
					:label="__('Share with others')"
				/>
				<MultiSelect
					v-if="shareIsShared"
					v-model="shareInstructors"
					doctype="User"
					searchUrl="lms.lms.api.get_lms_staff_users"
					:label="__('Instructors to share with')"
				/>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showConfirmDeleteBankDialog"
		:options="{
			title: __('Delete Question Bank'),
			size: 'sm',
			actions: [
				{
					label: __('Delete'),
					variant: 'solid',
					theme: 'red',
					onClick: (dialog) => handleDeleteBank(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<p class="text-sm text-ink-gray-7">
				{{ __('Are you sure you want to delete the entire question bank "{0}" and all its questions?').format(bankToDelete) }}
			</p>
		</template>
	</Dialog>

	<Dialog
		v-model="showConfirmDeleteQuestionDialog"
		:options="{
			title: __('Delete Question'),
			size: 'sm',
			actions: [
				{
					label: __('Delete'),
					variant: 'solid',
					theme: 'red',
					onClick: (dialog) => handleDeleteQuestion(dialog),
				},
			],
		}"
	>
		<template #body-content>
			<p class="text-sm text-ink-gray-7">
				{{ __('Are you sure you want to delete this question?') }}
			</p>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Badge,
	Breadcrumbs,
	Button,
	createListResource,
	createResource,
	call,
	Dialog,
	FeatherIcon,
	FormControl,
	ListView,
	ListRows,
	ListRow,
	ListRowItem,
	ListHeader,
	ListHeaderItem,
	ListSelectBanner,
	TabButtons,
	TextEditor,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { useRouter, useRoute } from 'vue-router'
import { computed, inject, onMounted, ref, watch, onUpdated } from 'vue'
import { Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { escapeHTML, cleanError, formatQuizText } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import EmptyState from '@/components/EmptyState.vue'
import MultiSelect from '@/components/Controls/MultiSelect.vue'

const { brand } = sessionStore()
const { capture } = useTelemetry()
const user = inject('$user')
const dayjs = inject('$dayjs')
const router = useRouter()
const route = useRoute()
const search = ref('')
const readOnlyMode = window.read_only_mode
const quizFilters = ref({})
const showForm = ref(false)
const title = ref('')

const currentTab = ref('quizzes')
const quizTabs = computed(() => [
	{ label: __('Quizzes'), value: 'quizzes' },
	{ label: __('Question Banks'), value: 'banks' },
])

const showImportModal = ref(false)
const bankLabel = ref('')
const importFormat = ref('GIFT')
const bankFileInput = ref(null)
const isShared = ref(false)
const sharedWith = ref([])

const showShareModal = ref(false)
const bankToShare = ref(null)
const shareIsShared = ref(false)
const shareInstructors = ref([])

const showViewBankQuestionsDialog = ref(false)
const selectedBank = ref('')
const selectedBankOwner = ref('')
const bankQuestions = ref([])
const loadingBankQuestions = ref(false)

const showConfirmDeleteBankDialog = ref(false)
const bankToDelete = ref('')
const showConfirmDeleteQuestionDialog = ref(false)
const questionToDelete = ref('')
const questionToDeleteIndex = ref(-1)

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		router.push({ name: 'Courses' })
	}
	if (route.query.new === 'true') {
		showForm.value = true
	}
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

onUpdated(() => {
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

watch(search, () => {
	if (currentTab.value === 'quizzes') {
		quizFilters.value['title'] = ['like', `%${search.value}%`]
		quizzes.update({
			filters: quizFilters.value,
		})
		quizzes.reload()
	}
})

const quizzes = createListResource({
	doctype: 'LMS Quiz',
	filters: quizFilters,
	fields: [
		'name',
		'title',
		'passing_percentage',
		'total_marks',
		'show_answers',
		'max_attempts',
		'modified',
		'owner',
	],
	auto: true,
	cache: ['quizzes', user.data?.name],
	orderBy: 'modified desc',
	pageLength: 10,
	transform(data) {
		return data.map((quiz) => {
			return {
				...quiz,
				modified: dayjs(quiz.modified).fromNow(),
			}
		})
	},
})

const usageInfo = createResource({
	url: 'lms.lms.api.get_content_usage_info',
	params: { content_doctype: 'LMS Quiz' },
	auto: true,
})

const transformedQuizzes = computed(() => {
	if (!quizzes.data) return []
	return quizzes.data.map((quiz) => {
		const info = usageInfo.data?.[quiz.name] || {}
		return {
			...quiz,
			created_by: info.created_by || '',
			used_in: info.courses || [],
		}
	})
})

const questionBanks = createResource({
	url: 'lms.lms.api.get_question_banks',
	cache: ['question_banks', user.data?.name],
	auto: true,
})

const canManageBankCard = (bank) => {
	if (readOnlyMode) return false
	const u = user.data
	if (!u) return false
	if (u.is_system_manager || u.is_moderator || u.name === 'Administrator') return true
	return bank.owner === u.name
}

const selectedBankDoc = computed(() => {
	if (!selectedBank.value || !questionBanks.data) return null
	return questionBanks.data.find(b => b.question_bank === selectedBank.value)
})

const canManageBank = computed(() => {
	if (!selectedBank.value || readOnlyMode) return false
	const u = user.data
	if (!u) return false
	if (u.is_system_manager || u.is_moderator || u.name === 'Administrator') return true
	const b = selectedBankDoc.value
	if (!b) return selectedBankOwner.value === u.name
	if (b.owner === u.name) return true
	if (b.is_shared) {
		if (!b.shared_with) return true
		const shared = b.shared_with.split(',').map(s => s.trim().toLowerCase())
		return shared.includes(u.name.toLowerCase())
	}
	return false
})

const showEditBankQuestionDialog = ref(false)
const editingBankQuestion = ref(null)
const loadingQuestionForm = ref(false)
const editingBankQuestionForm = ref({
	name: '',
	question_bank: '',
	question: '',
	type: 'Choices',
	option_1: '',
	is_correct_1: false,
	explanation_1: '',
	option_2: '',
	is_correct_2: false,
	explanation_2: '',
	option_3: '',
	is_correct_3: false,
	explanation_3: '',
	option_4: '',
	is_correct_4: false,
	explanation_4: '',
	possibility_1: '',
	possibility_2: '',
	possibility_3: '',
	possibility_4: '',
})

const openAddBankQuestion = () => {
	editingBankQuestion.value = null
	editingBankQuestionForm.value = {
		name: '',
		question_bank: selectedBank.value,
		question: '',
		type: 'Choices',
		option_1: '',
		is_correct_1: false,
		explanation_1: '',
		option_2: '',
		is_correct_2: false,
		explanation_2: '',
		option_3: '',
		is_correct_3: false,
		explanation_3: '',
		option_4: '',
		is_correct_4: false,
		explanation_4: '',
		possibility_1: '',
		possibility_2: '',
		possibility_3: '',
		possibility_4: '',
	}
	showEditBankQuestionDialog.value = true
}

const openEditBankQuestion = (qName) => {
	editingBankQuestion.value = qName
	loadingQuestionForm.value = true
	showEditBankQuestionDialog.value = true
	call('lms.lms.api.get_bank_question_details', { question_name: qName })
		.then((data) => {
			if (data) {
				editingBankQuestionForm.value = {
					name: data.name || '',
					question_bank: data.question_bank || selectedBank.value,
					question: data.question || '',
					type: data.type || 'Choices',
					option_1: data.option_1 || '',
					is_correct_1: data.is_correct_1 ? true : false,
					explanation_1: data.explanation_1 || '',
					option_2: data.option_2 || '',
					is_correct_2: data.is_correct_2 ? true : false,
					explanation_2: data.explanation_2 || '',
					option_3: data.option_3 || '',
					is_correct_3: data.is_correct_3 ? true : false,
					explanation_3: data.explanation_3 || '',
					option_4: data.option_4 || '',
					is_correct_4: data.is_correct_4 ? true : false,
					explanation_4: data.explanation_4 || '',
					possibility_1: data.possibility_1 || '',
					possibility_2: data.possibility_2 || '',
					possibility_3: data.possibility_3 || '',
					possibility_4: data.possibility_4 || '',
				}
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
			showEditBankQuestionDialog.value = false
		})
		.finally(() => {
			loadingQuestionForm.value = false
		})
}

const handleSaveBankQuestion = (dialog) => {
	if (!editingBankQuestionForm.value.question || !editingBankQuestionForm.value.question.trim()) {
		toast.error(__('Question text is required'))
		return
	}
	call('lms.lms.api.save_bank_question', {
		question_data: editingBankQuestionForm.value,
	})
		.then(() => {
			toast.success(
				editingBankQuestion.value
					? __('Question updated successfully')
					: __('Question added successfully')
			)
			showEditBankQuestionDialog.value = false
			openBankQuestions(selectedBank.value)
			questionBanks.reload()
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}

const filteredBanks = computed(() => {
	if (!questionBanks.data) return []
	const q = search.value.toLowerCase().trim()
	if (!q) return questionBanks.data
	return questionBanks.data.filter(b => b.question_bank && b.question_bank.toLowerCase().includes(q))
})

const handleBankImport = (dialog) => {
	const label = bankLabel.value.trim()
	if (!label) {
		toast.error(__('Please enter a bank label'))
		return
	}
	const file = bankFileInput.value?.files?.[0]
	if (!file) {
		toast.error(__('Please select a file to import'))
		return
	}

	const reader = new FileReader()
	reader.onload = (e) => {
		const content = e.target.result
		call('lms.lms.api.import_question_bank', {
			file_content: content,
			format_type: importFormat.value,
			bank_label: label,
			is_shared: isShared.value ? 1 : 0,
			shared_with: isShared.value && sharedWith.value ? sharedWith.value.join(',') : '',
		})
			.then((res) => {
				toast.success(__('Question bank imported successfully: {0} questions added.').format(res.count))
				questionBanks.reload()
				dialog.close()
				bankLabel.value = ''
				isShared.value = false
				sharedWith.value = []
				if (bankFileInput.value) {
					bankFileInput.value.value = ''
				}
			})
			.catch((err) => {
				toast.error(err.messages?.[0] || err.message || err)
			})
	}
	reader.readAsText(file)
}

const openBankQuestions = (bankLabel) => {
	selectedBank.value = bankLabel
	const bank = questionBanks.data?.find(b => b.question_bank === bankLabel)
	selectedBankOwner.value = bank ? bank.owner : ''
	showViewBankQuestionsDialog.value = true
	loadingBankQuestions.value = true
	bankQuestions.value = []
	call('lms.lms.api.get_bank_questions', { bank_label: bankLabel })
		.then((r) => {
			bankQuestions.value = r || []
		})
		.finally(() => {
			loadingBankQuestions.value = false
		})
}

const openShareModal = (bank) => {
	bankToShare.value = bank
	shareIsShared.value = (bank.is_shared === 1)
	shareInstructors.value = bank.shared_with ? bank.shared_with.split(',').map(u => u.trim()) : []
	showShareModal.value = true
}

const handleSaveShare = (dialog) => {
	call('lms.lms.api.update_question_bank_sharing', {
		bank_label: bankToShare.value.question_bank,
		is_shared: shareIsShared.value ? 1 : 0,
		shared_with: shareIsShared.value && shareInstructors.value ? shareInstructors.value.join(',') : '',
	})
		.then(() => {
			toast.success(__('Sharing settings updated successfully'))
			questionBanks.reload()
			dialog.close()
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}

watch(currentTab, (newTab) => {
	if (newTab === 'banks') {
		questionBanks.reload()
	}
})

const confirmDeleteBank = (bankLabel) => {
	bankToDelete.value = bankLabel
	showConfirmDeleteBankDialog.value = true
}

const handleDeleteBank = (dialog) => {
	call('lms.lms.api.delete_question_bank', { bank_label: bankToDelete.value })
		.then(() => {
			toast.success(__('Question bank "{0}" deleted successfully').format(bankToDelete.value))
			questionBanks.reload()
			dialog.close()
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}

const confirmDeleteQuestion = (qName, idx) => {
	questionToDelete.value = qName
	questionToDeleteIndex.value = idx
	showConfirmDeleteQuestionDialog.value = true
}

const handleDeleteQuestion = (dialog) => {
	call('lms.lms.api.delete_bank_question', { question_name: questionToDelete.value })
		.then(() => {
			toast.success(__('Question deleted successfully'))
			if (questionToDeleteIndex.value !== -1) {
				bankQuestions.value.splice(questionToDeleteIndex.value, 1)
			}
			questionBanks.reload()
			dialog.close()
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || err)
		})
}

const validateTitle = () => {
	title.value = escapeHTML(title.value.trim())
}

const insertQuiz = (close) => {
	validateTitle()
	quizzes.insert.submit(
		{
			title: title.value,
		},
		{
			onSuccess(data) {
				toast.success(__('Quiz created successfully'))
				close()
				title.value = ''
				capture('quiz_created')
				router.push({
					name: 'QuizForm',
					params: {
						quizID: data.name,
					},
				})
			},
			onError(error) {
				toast.error(__('Error creating quiz: {0}', error.message))
			},
		}
	)
}

const deleteQuiz = (selections, unselectAll) => {
	if (user.data?.roles?.includes('Course Creator')) {
		const nonOwned = Array.from(selections).filter((name) => {
			const quiz = quizzes.data?.find((q) => q.name === name)
			return quiz && quiz.owner !== user.data.name
		})
		if (nonOwned.length > 0) {
			toast.error(__('You can only delete quizzes created by you.'))
			return
		}
	}
	const promises = Array.from(selections).map((quizName) => {
		return quizzes.delete.submit(quizName)
	})
	Promise.all(promises)
		.then(() => {
			toast.success(__('Quizzes deleted successfully'))
			unselectAll()
		})
		.catch((err) => {
			const errorMsg = err.messages?.[0] || err.message || String(err)
			toast.error(cleanError(errorMsg))
			unselectAll()
		})
}

const quizColumns = computed(() => {
	return [
		{
			label: __('Title'),
			key: 'title',
			width: 2,
			icon: 'file-text',
		},
		{
			label: __('Total Marks'),
			key: 'total_marks',
			width: 1,
			align: 'center',
			icon: 'hash',
		},
		{
			label: __('Passing Percentage'),
			key: 'passing_percentage',
			width: 1,
			align: 'center',
			icon: 'percent',
		},
		{
			label: __('Max Attempts'),
			key: 'max_attempts',
			width: 1,
			align: 'center',
			icon: 'repeat',
		},
		{
			label: __('Show Answers'),
			key: 'show_answers',
			width: 1,
			align: 'center',
			icon: 'eye',
		},
		{
			label: __('Created By'),
			key: 'created_by',
			width: 1.5,
			align: 'left',
			icon: 'user',
		},
		{
			label: __('Used In'),
			key: 'used_in',
			width: 2,
			align: 'left',
			icon: 'book',
		},
		{
			label: __('Modified'),
			key: 'modified',
			width: 1,
			align: 'center',
			icon: 'clock',
		},
	]
})

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Quizzes'),
			route: {
				name: 'Quizzes',
			},
		},
	]
})

usePageMeta(() => {
	return {
		title: __('Quizzes'),
		icon: brand.favicon,
	}
})
</script>

