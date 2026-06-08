<template>
	<Dialog
		v-model="show"
		:options="{
			size: 'lg',
		}"
	>
		<template #body>
			<div class="p-5 text-base">
				<div class="text-lg text-ink-gray-9 font-semibold mb-5">
					{{
						assignmentID === 'new'
							? __('Create an Assignment')
							: __('Edit Assignment')
					}}
				</div>
				<div class="space-y-4 max-h-[75vh] overflow-y-auto">
					<FormControl
						v-model="assignment.title"
						:label="__('Title')"
						:required="true"
					/>
					<FormControl
						v-model="assignment.type"
						type="select"
						:options="assignmentOptions"
						:label="__('Submission Type')"
						:required="true"
					/>
					<Link
						v-model="assignment.course"
						:label="__('Course')"
						doctype="LMS Course"
						placeholder=" "
					/>
					<div class="grid grid-cols-2 gap-4">
						<FormControl
							v-if="gradingCategoryOptions.length"
							v-model="assignment.grading_category"
							type="select"
							:options="[{ label: __('Select Category'), value: '' }, ...gradingCategoryOptions]"
							:label="__('Grading Category')"
						/>
						<FormControl
							v-else
							v-model="assignment.grading_category"
							type="text"
							:label="__('Grading Category')"
							:placeholder="__('e.g. Homework, Quiz')"
						/>
					</div>
					<div class="grid grid-cols-2 gap-4">
						<FormControl
							v-model="assignment.due_date"
							type="date"
							:label="__('Due Date')"
						/>
						<FormControl
							v-model="assignment.due_time"
							type="time"
							:label="__('Due Time')"
						/>
					</div>
					<div>
						<div class="text-xs text-ink-gray-5 mb-2">
							{{ __('Question') }}
							<span class="text-ink-red-3">*</span>
						</div>
						<TextEditor
							:content="assignment.question"
							@change="(val) => (assignment.question = val)"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem] max-h-[18rem] overflow-y-auto"
						/>
					</div>
				</div>

				<div class="flex justify-end space-x-2 mt-5">
					<router-link
						:to="{
							name: 'AssignmentSubmissionList',
							query: {
								assignmentID: assignmentID,
							},
						}"
					>
						<Button v-if="assignmentID !== 'new'" variant="subtle">
							{{ __('Check Submissions') }}
						</Button>
					</router-link>
					<Button variant="solid" @click="saveAssignment">
						{{ __('Save') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { Button, Dialog, FormControl, TextEditor, toast, createResource } from 'frappe-ui'
import { computed, reactive, watch } from 'vue'
import { escapeHTML, sanitizeHTML } from '@/utils'
import { Link } from 'frappe-ui/frappe'

const show = defineModel()
const assignments = defineModel<Assignments>('assignments')

interface Assignment {
	title: string
	type: string
	question: string
	course?: string
	grading_category?: string
	due_date?: string
	due_time?: string
}

interface Assignments {
	data: Assignment[]
	get: (params: { doctype: string; name: string }) => Promise<Assignment>
	insert: {
		submit: (params: Assignment, options: { onSuccess: () => void }) => void
	}
}

const assignment = reactive({
	title: '',
	type: '',
	question: '',
	course: '',
	grading_category: '',
	due_date: '',
	due_time: '',
})

const props = defineProps({
	assignmentID: {
		type: String,
		default: 'new',
	},
})

const courseResource = createResource({
	url: 'frappe.client.get',
	makeParams() {
		return {
			doctype: 'LMS Course',
			name: assignment.course,
		}
	},
	auto: false,
})

watch(
	() => assignment.course,
	(val) => {
		if (val) {
			courseResource.submit()
		}
	},
	{ immediate: true }
)

const gradingCategoryOptions = computed(() => {
	const courseDoc = courseResource.data
	if (!courseDoc || !courseDoc.enable_grading_policy || !courseDoc.grading_categories) {
		return []
	}
	return courseDoc.grading_categories.map((cat) => ({
		label: cat.category_name,
		value: cat.category_name,
	}))
})

watch(
	() => props.assignmentID,
	(val) => {
		if (val !== 'new') {
			assignments.value?.data.forEach((row) => {
				if (row.name === val) {
					assignment.title = row.title
					assignment.type = row.type
					assignment.question = row.question
					assignment.course = row.course || ''
					assignment.grading_category = row.grading_category || ''
					assignment.due_date = row.due_date || ''
					assignment.due_time = row.due_time || ''
				}
			})
		}
	},
	{ flush: 'post' }
)

watch(show, (newVal) => {
	if (newVal && props.assignmentID === 'new') {
		assignment.title = ''
		assignment.type = ''
		assignment.question = ''
		assignment.grading_category = ''
		assignment.due_date = ''
		assignment.due_time = ''
	}
})

const validateFields = () => {
	assignment.title = escapeHTML(assignment.title.trim())
	assignment.question = sanitizeHTML(assignment.question)
}

const saveAssignment = () => {
	validateFields()
	if (props.assignmentID == 'new') {
		createAssignment()
	} else {
		updateAssignment()
	}
}

const createAssignment = () => {
	assignments.value.insert.submit(
		{
			...assignment,
		},
		{
			onSuccess() {
				show.value = false
				toast.success(__('Assignment created successfully'))
			},
		}
	)
}

const updateAssignment = () => {
	assignments.value.setValue.submit(
		{
			...assignment,
			name: props.assignmentID,
		},
		{
			onSuccess() {
				show.value = false
				toast.success(__('Assignment updated successfully'))
			},
		}
	)
}

const assignmentOptions = computed(() => {
	return [
		{ label: 'PDF', value: 'PDF' },
		{ label: 'Image', value: 'Image' },
		{ label: 'Document', value: 'Document' },
		{ label: 'Text', value: 'Text' },
		{ label: 'URL', value: 'URL' },
	]
})
</script>
