<template>
	<Dialog v-model="show" :options="{ size: '4xl' }">
		<template #body-title>
			<div class="flex items-center space-x-2">
				<div class="text-xl font-semibold text-ink-gray-9">
					{{
						props.exerciseID === 'new'
							? __('Create Programming Exercise')
							: __('Edit Programming Exercise')
					}}
				</div>
				<Badge v-if="isDirty" theme="orange">
					{{ __('Not Saved') }}
				</Badge>
			</div>
		</template>
		<template #body-content>
			<div class="grid grid-cols-2 gap-10">
				<div class="space-y-4">
					<FormControl
						v-model="exercise.title"
						:label="__('Title')"
						:required="true"
						:disabled="readOnlyMode"
					/>
					<FormControl
						v-model="exercise.language"
						:label="__('Language')"
						type="select"
						:options="languageOptions"
						:required="true"
						:disabled="readOnlyMode"
					/>
					<ChildTable
						v-model="testCases.data"
						:label="__('Test Cases')"
						:columns="testCaseColumns"
						:required="true"
						:addable="!readOnlyMode"
						:deletable="!readOnlyMode"
						:editable="!readOnlyMode"
						:placeholder="__('Add Test Case')"
					/>
				</div>
				<div>
					<div>
						<div class="text-xs text-ink-gray-5 mb-2">
							{{ __('Problem Statement') }}
							<span class="text-ink-red-3">*</span>
						</div>
						<TextEditor
							:content="exercise.problem_statement"
							@change="(val: string) => (exercise.problem_statement = val)"
							:editable="!readOnlyMode"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem] max-h-[21rem] overflow-y-auto"
						/>
					</div>
				</div>
			</div>
		</template>
		<template #actions="{ close }">
			<div class="flex justify-end space-x-2 group">
				<Button
					v-if="exerciseID != 'new' && !readOnlyMode"
					@click="deleteExercise(close)"
					variant="outline"
					theme="red"
				>
					<template #prefix>
						<Trash2 class="size-4 stroke-1.5" />
					</template>
					{{ __('Delete') }}
				</Button>
				<router-link
					:to="{
						name: 'ProgrammingExerciseSubmission',
						params: {
							exerciseID: props.exerciseID,
							submissionID: 'new',
						},
					}"
				>
					<Button>
						<template #prefix>
							<Play class="size-4 stroke-1.5" />
						</template>
						{{ __('Test this Exercise') }}
					</Button>
				</router-link>
				<router-link
					v-if="exerciseID != 'new' && (!user.data?.roles?.includes('Course Creator') || exercise.owner === user.data.name || user.data?.is_moderator)"
					:to="{
						name: 'ProgrammingExerciseSubmissions',
						query: {
							exercise: props.exerciseID,
						},
					}"
				>
					<Button>
						<template #prefix>
							<ClipboardList class="size-4 stroke-1.5" />
						</template>
						{{ __('Check Submission') }}
					</Button>
				</router-link>
				<Button v-if="!readOnlyMode" variant="solid" @click="saveExercise(close)">
					{{ __('Save') }}
				</Button>
			</div>
		</template>
	</Dialog>

	<!-- Programming Exercise Save Warning Modal -->
	<Dialog
		v-model="showExerciseSaveWarningModal"
		:options="{
			size: 'md',
			actions: [
				{
					label: __('Create New Version'),
					variant: 'solid',
					onClick: () => handleCreateNewExerciseVersion(() => show = false)
				},
				{
					label: __('Update Current Version'),
					variant: 'outline',
					onClick: () => {
						showExerciseSaveWarningModal = false
						updateExercise(() => show = false)
					}
				}
			]
		}"
	>
		<template #body-title>
			<div class="flex items-center gap-2">
				<AlertTriangle class="h-6 w-6 text-amber-500 flex-shrink-0" />
				<h3 class="text-lg font-semibold text-amber-900">
					{{ __('Submissions Found Warning') }}
				</h3>
			</div>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-sm text-ink-gray-6">
					{{ __('This programming exercise already contains learner submissions or grading records. Creating a new version is highly recommended to preserve student records and grades.') }}
				</p>
				<FormControl
					v-model="exerciseVersionChangeLog"
					:label="__('Change Log Description')"
					type="textarea"
					placeholder="Describe the changes in this version..."
					:required="true"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch, onMounted, onUpdated, inject } from 'vue'
import { escapeHTML, cleanError } from '@/utils'
import {
	Badge,
	Button,
	createListResource,
	Dialog,
	FormControl,
	TextEditor,
	toast,
	call,
} from 'frappe-ui'
import {
	ProgrammingExercise,
	ProgrammingExercises,
	TestCase,
} from '@/types/programming-exercise'
import { AlertTriangle, ClipboardList, Play, Trash2 } from 'lucide-vue-next'
import ChildTable from '@/components/Controls/ChildTable.vue'

const show = defineModel()
const exercises = defineModel<ProgrammingExercises>('exercises')
const isDirty = ref(false)
const originalTestCaseCount = ref(0)
const showExerciseSaveWarningModal = ref(false)
const exerciseVersionChangeLog = ref('')

const exercise = ref<ProgrammingExercise>({
	title: '',
	language: 'Python',
	problem_statement: '',
	test_cases: [],
	owner: '',
})

const user = inject<any>('$user')
const readOnlyMode = computed(() => {
	if (props.exerciseID === 'new') return false
	if (
		user.data?.roles?.includes('Course Creator') &&
		exercise.value?.owner &&
		exercise.value.owner !== user.data.name
	) {
		return true
	}
	return false
})

const languageOptions = [
	{ label: 'Python', value: 'Python' },
	{ label: 'JavaScript', value: 'JavaScript' },
	{ label: 'C', value: 'C' },
	{ label: 'C++', value: 'C++' },
]

const props = withDefaults(
	defineProps<{
		exerciseID: string
	}>(),
	{
		exerciseID: 'new',
	}
)

watch(
	() => props.exerciseID,
	() => {
		setExerciseData()
		fetchTestCases()
	}
)

onMounted(() => {
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

onUpdated(() => {
	if (window.triggerMathJax) {
		window.triggerMathJax()
	}
})

const setExerciseData = () => {
	let isNew = true
	exercises.value?.data.forEach((ex: ProgrammingExercise) => {
		if (ex.name === props.exerciseID) {
			isNew = false
			exercise.value = { ...ex }
		}
	})

	if (isNew) {
		exercise.value = {
			title: '',
			language: 'Python',
			problem_statement: '',
			test_cases: [],
		}
	}
	isDirty.value = false
}

const testCases = createListResource({
	doctype: 'LMS Test Case',
	fields: ['input', 'expected_output', 'name'],
	cache: ['testCases', props.exerciseID],
	parent: 'LMS Programming Exercise',
	orderBy: 'idx',
	onSuccess(data: TestCase[]) {
		isDirty.value = false
		originalTestCaseCount.value = data.length
	},
	onError(err: any) {
		toast.error(__(err.messages?.[0] || err))
		console.error('Error loading testCases:', err)
	},
})

const fetchTestCases = () => {
	testCases.update({
		filters: {
			parent: props.exerciseID,
			parenttype: 'LMS Programming Exercise',
			parentfield: 'test_cases',
		},
	})
	testCases.reload()
	// originalTestCaseCount is set in onSuccess once the async reload completes
}

const validateTitle = () => {
	exercise.value.title = escapeHTML(exercise.value.title.trim())
}

watch(
	exercise,
	() => {
		isDirty.value = true
	},
	{ deep: true }
)

watch(testCases, () => {
	if (testCases.data.length !== originalTestCaseCount.value) {
		isDirty.value = true
	}
})

const updateTestCasesInExercise = () => {
	exercise.value.test_cases = testCases.data.map(
		(tc: TestCase, index: number) => ({
			input: tc.input,
			expected_output: tc.expected_output,
			idx: index + 1,
		})
	)
}

const saveExercise = (close: () => void) => {
	validateTitle()
	updateTestCasesInExercise()
	if (props.exerciseID == 'new') {
		createNewExercise(close)
	} else {
		call('lms.lms.api.check_content_before_save', {
			content_doctype: 'LMS Programming Exercise',
			content_name: props.exerciseID
		}).then(res => {
			if (res && res.has_submissions) {
				showExerciseSaveWarningModal.value = true
			} else {
				updateExercise(close)
			}
		}).catch(() => {
			updateExercise(close)
		})
	}
}

const handleCreateNewExerciseVersion = (close: () => void) => {
	const log = exerciseVersionChangeLog.value.trim()
	if (!log) {
		toast.error(__('Please enter a change log description'))
		return
	}
	showExerciseSaveWarningModal.value = false
	
	call('lms.lms.api.create_new_content_version', {
		content_doctype: 'LMS Programming Exercise',
		content_name: props.exerciseID,
		change_log: log,
		doc_data: JSON.stringify(exercise.value)
	}).then(res => {
		toast.success(__('New version created successfully'))
		exerciseVersionChangeLog.value = ''
		close()
		exercises.value?.reload()
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to create new version'))
	})
}

const createNewExercise = (close: () => void) => {
	exercises.value?.insert.submit(
		{
			...exercise.value,
		},
		{
			onSuccess() {
				close()
				isDirty.value = false
				exercises.value?.reload()
				toast.success(__('Programming Exercise created successfully'))
			},
			onError(err: any) {
				const errorMsg = err.messages?.[0] || err.message || String(err)
				toast.error(cleanError(errorMsg))
			},
		}
	)
}

const updateExercise = (close: () => void) => {
	exercises.value?.setValue.submit(
		{
			name: props.exerciseID,
			...exercise.value,
		},
		{
			onSuccess() {
				close()
				isDirty.value = false
				exercises.value?.reload()
				toast.success(__('Programming Exercise updated successfully'))
			},
			onError(err: any) {
				const errorMsg = err.messages?.[0] || err.message || String(err)
				toast.error(cleanError(errorMsg))
			},
		}
	)
}

const testCaseColumns = computed(() => {
	return ['Input', 'Expected Output']
})

const deleteExercise = (close: () => void) => {
	if (props.exerciseID == 'new') return
	if (
		user.data?.roles?.includes('Course Creator') &&
		exercise.value?.owner &&
		exercise.value.owner !== user.data.name
	) {
		toast.error(__('You can only delete programming exercises created by you.'))
		return
	}
	exercises.value?.delete.submit(props.exerciseID, {
		onSuccess() {
			toast.success(__('Programming Exercise deleted successfully'))
			close()
		},
		onError(err: any) {
			const errorMsg = err.messages?.[0] || err.message || String(err)
			toast.error(cleanError(errorMsg))
		},
	})
}
</script>
