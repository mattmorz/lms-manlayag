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
				:rows="quizzes.data"
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
						v-for="row in quizzes.data"
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
					class="cursor-pointer bg-white border border-outline-gray-2 rounded-xl p-5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 flex items-center justify-between gap-4"
				>
					<div class="flex items-center gap-4 min-w-0">
						<div class="bg-surface-gray-2 p-3 rounded-lg text-ink-gray-7">
							<FeatherIcon name="database" class="w-6 h-6 stroke-1.5" />
						</div>
						<div class="min-w-0">
							<div class="font-semibold text-ink-gray-9 text-base truncate">
								{{ bank.question_bank }}
							</div>
							<div class="text-sm text-ink-gray-5 mt-0.5">
								{{ bank.question_count }} {{ bank.question_count === 1 ? __('Question') : __('Questions') }}
							</div>
						</div>
					</div>
					<div class="flex items-center gap-2">
						<Button
							v-if="!readOnlyMode"
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
			<div v-else class="flex flex-col items-center justify-center py-20 bg-surface-gray-2 rounded-xl border border-dashed border-outline-gray-3">
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
						<div class="prose-sm text-ink-gray-9 leading-relaxed" v-html="q.question"></div>
					</div>
					<Button
						v-if="!readOnlyMode"
						variant="ghost"
						class="text-red-600 hover:bg-red-50 hover:text-red-800 p-1 rounded mt-1 align-self-start"
						@click="confirmDeleteQuestion(q.name, idx)"
					>
						<FeatherIcon name="trash-2" class="w-4 h-4 text-red-500" />
					</Button>
				</div>
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
	toast,
	usePageMeta,
} from 'frappe-ui'
import { useRouter, useRoute } from 'vue-router'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { escapeHTML } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import EmptyState from '@/components/EmptyState.vue'

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

const showViewBankQuestionsDialog = ref(false)
const selectedBank = ref('')
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
	} else if (!user.data?.is_moderator) {
		quizFilters.value['owner'] = user.data?.name
	}
	if (route.query.new === 'true') {
		showForm.value = true
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
	],
	auto: true,
	cache: ['quizzes', user.data?.name],
	orderBy: 'modified desc',
	transform(data) {
		return data.map((quiz) => {
			return {
				...quiz,
				modified: dayjs(quiz.modified).fromNow(),
			}
		})
	},
})

const questionBanks = createResource({
	url: 'lms.lms.api.get_question_banks',
	cache: ['question_banks', user.data?.name],
	auto: true,
})

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
		})
			.then((res) => {
				toast.success(__('Question bank imported successfully: {0} questions added.').format(res.count))
				questionBanks.reload()
				dialog.close()
				bankLabel.value = ''
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
	Array.from(selections).forEach(async (quizName) => {
		await quizzes.delete.submit(quizName)
	})
	unselectAll()
	toast.success(__('Quizzes deleted successfully'))
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

