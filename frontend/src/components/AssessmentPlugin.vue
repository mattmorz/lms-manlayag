<template>
	<Dialog
		v-model="show"
		:options="{
			title:
				type == 'quiz'
					? __('Add a quiz to your lesson')
					: __('Add an assignment to your lesson'),
			size: 'xl',
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
						{{ __('Grading & Deadline (Required)') }}
					</div>
					<div class="grid grid-cols-3 gap-4">
						<FormControl
							v-if="gradingCategoryOptions.length"
							v-model="grading_category"
							type="select"
							:options="[{ label: __('Select Category'), value: '' }, ...gradingCategoryOptions]"
							:label="__('Grading Category')"
							:required="true"
						/>
						<FormControl
							v-else
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
					<Link
						v-if="type == 'quiz'"
						v-model="quiz"
						doctype="LMS Quiz"
						:label="__('Select a quiz')"
						placeholder=" "
						:onCreate="(value, close) => redirectToForm()"
					/>
					<div v-else class="space-y-4">
						<Link
							v-if="filterAssignmentsByCourse"
							v-model="assignment"
							doctype="LMS Assignment"
							:filters="{
								course: route.params.courseName,
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
import { Link } from 'frappe-ui/frappe'
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
	onAddition: {
		type: Function,
		required: true,
	},
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
			name: route.params.courseName,
		}
	},
	auto: true,
})

const categoryCounts = createResource({
	url: 'lms.lms.api.get_category_counts',
	makeParams() {
		return {
			course: route.params.courseName,
		}
	},
	auto: true,
})

const courseDoc = computed(() => courseResource.data)

const gradingCategoryOptions = computed(() => {
	if (!courseDoc.value || !courseDoc.value.enable_grading_policy || !courseDoc.value.grading_categories) {
		return []
	}
	const counts = categoryCounts.data || {}
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
	if (courseDoc.value?.enable_grading_policy) {
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
		grading_category: grading_category.value,
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
