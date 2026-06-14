<template>
	<Dialog
		v-model="show"
		:options="{
			title:
				type == 'quiz'
					? __('Add a quiz to your lesson')
					: __('Add an assignment to your lesson'),
			size: 'xl',
			position: 'top',
			paddingTop: '3rem',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: () => {
						addAssessment()
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div v-if="courseDoc?.enable_grading_policy" class="space-y-4 pb-4 border-b border-outline-gray-modals">
					<div class="text-sm font-semibold text-ink-gray-9 mb-2">
						{{ __('Grading & Deadline') }}
					</div>
					<FormControl
						v-if="type == 'quiz'"
						v-model="include_in_grading"
						type="checkbox"
						:label="__('Include in grading')"
					/>
					<div class="grid grid-cols-1 gap-y-4 md:grid-cols-[1.2fr_1fr_1fr] md:gap-x-8">
						<FormControl
							v-if="gradingCategoryOptions.length && (type != 'quiz' || include_in_grading)"
							v-model="grading_category"
							type="select"
							:options="[{ label: __('Select Category'), value: '' }, ...gradingCategoryOptions]"
							:label="__('Grading Category')"
							:required="type != 'quiz' || include_in_grading"
						/>
						<FormControl
							v-else-if="type != 'quiz' || include_in_grading"
							v-model="grading_category"
							type="text"
							:label="__('Grading Category')"
							:placeholder="__('e.g. Homework, Quiz')"
						/>
						<FormControl
							v-model="due_date"
							type="date"
							:label="__('Due Date')"
						/>
						<FormControl
							v-model="due_time"
							type="time"
							:label="__('Due Time')"
						/>
					</div>
				</div>

				<div>
					<div v-if="type == 'quiz'" class="space-y-4">
						<Link
							v-model="quiz"
							doctype="LMS Quiz"
							:filters="quizFilters"
							:label="__('Select a quiz')"
							placeholder=" "
							:onCreate="(value, close) => redirectToForm()"
						/>
						<FormControl
							v-if="allowCheckpointQuiz"
							type="checkbox"
							:label="__('Checkpoint quiz')"
							v-model="checkpoint_quiz"
							class="mt-3"
						/>
					</div>
					<div v-else-if="type == 'assignment'" class="space-y-4">
						<Link
							v-if="filterAssignmentsByCourse"
							v-model="assignment"
							doctype="LMS Assignment"
							:filters="{
								course: courseName,
							}"
							placeholder=" "
							:label="__('Select an Assignment')"
							:onCreate="(value, close) => redirectToForm()"
						/>
						<Link
							v-else
							v-model="assignment"
							doctype="LMS Assignment"
							placeholder=" "
							:label="__('Select an Assignment')"
							:onCreate="(value, close) => redirectToForm()"
						/>
						<FormControl
							type="checkbox"
							:label="__('Filter assignments by course')"
							v-model="filterAssignmentsByCourse"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, createResource, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Link from '@/components/Controls/Link.vue'
import { getLmsRoute } from '@/utils/basePath'

const show = ref(false)
const quiz = ref(null)
const assignment = ref(null)
const grading_category = ref('')
const due_date = ref('')
const due_time = ref('')
const filterAssignmentsByCourse = ref(false)
const route = useRoute()

const props = defineProps({
	type: {
		type: String,
		required: true,
	},
	creationMode: {
		type: String,
		default: 'lesson',
	},
	onAddition: {
		type: Function,
		required: true,
	},
	courseName: {
		type: String,
		default: '',
	},
	currentAssessments: {
		type: Array,
		default: () => [],
	},
	allowCheckpointQuiz: {
		type: Boolean,
		default: true,
	},
})

const include_in_grading = ref(props.creationMode === 'lesson' ? false : true)
const checkpoint_quiz = ref(props.creationMode === 'lesson' && props.allowCheckpointQuiz)

const courseName = computed(() => {
	return props.courseName || route?.params?.courseName || ''
})

onMounted(async () => {
	await nextTick()
	show.value = true
})

const courseResource = createResource({
	url: 'frappe.client.get',
	makeParams() {
		return {
			doctype: 'LMS Course',
			name: courseName.value,
		}
	},
	auto: true,
})

const categoryCounts = createResource({
	url: 'lms.lms.api.get_category_counts',
	makeParams() {
		return {
			course: courseName.value,
			current_lesson: window.current_lesson_name || '',
		}
	},
	auto: true,
})

const usedQuizzesResource = createResource({
	url: 'lms.lms.api.get_used_quizzes',
	makeParams() {
		return {
			course: courseName.value,
		}
	},
	auto: true,
})

const quizFilters = computed(() => {
	const used = usedQuizzesResource.data || []
	if (used.length) {
		return {
			name: ['not in', used],
		}
	}
	return {}
})

const courseDoc = computed(() => courseResource.data)

const gradingCategoryOptions = computed(() => {
	if (!courseDoc.value || !courseDoc.value.enable_grading_policy || !courseDoc.value.grading_categories) {
		return []
	}
	const counts = { ...(categoryCounts.data || {}) }
	for (const item of props.currentAssessments) {
		if (item.category) {
			counts[item.category] = (counts[item.category] || 0) + 1
		}
	}
	return courseDoc.value.grading_categories.map((cat) => {
		const currentCount = counts[cat.category_name] || 0
		const limit = cat.number_of_assessments || 0
		const isFull = limit > 0 && currentCount >= limit

		return {
			label: isFull
				? `${cat.category_name} (${__('Full - {0}/{1}').format(currentCount, limit)})`
				: limit > 0
					? `${cat.category_name} (${currentCount}/${limit})`
					: cat.category_name,
			value: cat.category_name,
			disabled: isFull,
		}
	})
})

const addAssessment = () => {
	const selectedItem = props.type == 'quiz' ? quiz.value : assignment.value
	if (!selectedItem) {
		toast.error(props.type == 'quiz' ? __('Please select a quiz') : __('Please select an assignment'))
		return
	}
	if (courseDoc.value?.enable_grading_policy && (props.type != 'quiz' || include_in_grading.value)) {
		if (!grading_category.value) {
			toast.error(__('Please select a Grading Category first.'))
			return
		}
		const optionObj = gradingCategoryOptions.value.find(o => o.value === grading_category.value)
		if (optionObj && optionObj.disabled) {
			toast.error(__('The selected category has reached its assessment limit.'))
			return
		}
	}
	props.onAddition({
		item: selectedItem,
		grading_category: (props.type == 'quiz' && !include_in_grading.value) ? '' : grading_category.value,
		include_in_grading: props.type == 'quiz' ? include_in_grading.value : true,
		checkpoint_quiz: props.type == 'quiz' ? checkpoint_quiz.value : false,
		due_date: due_date.value,
		due_time: due_time.value,
	})
	show.value = false
}

const redirectToForm = () => {
	if (props.type == 'quiz') {
		window.open(getLmsRoute('quizzes?new=true'), '_blank')
	} else {
		window.open(getLmsRoute('assignments?new=true'), '_blank')
	}
}
</script>

<style scoped>
:deep([data-dialog='Add a quiz to your lesson'] .dialog-content),
:deep([data-dialog='Add an assignment to your lesson'] .dialog-content) {
	overflow: visible;
}
</style>
