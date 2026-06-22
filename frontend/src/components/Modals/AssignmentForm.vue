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

	<!-- Assignment Save Warning Modal -->
	<Dialog
		v-model="showAssignmentSaveWarningModal"
		:options="{
			size: 'md',
			actions: [
				{
					label: __('Create New Version'),
					variant: 'solid',
					onClick: () => handleCreateNewAssignmentVersion()
				},
				{
					label: __('Update Current Version'),
					variant: 'outline',
					onClick: () => {
						showAssignmentSaveWarningModal = false
						updateAssignment()
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
					{{ __('This assignment already contains student submissions. Creating a new version is highly recommended to preserve student records and grades.') }}
				</p>
				<FormControl
					v-model="assignmentVersionChangeLog"
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
import { Button, Dialog, FormControl, TextEditor, toast, createResource, call } from 'frappe-ui'
import { computed, reactive, watch, ref } from 'vue'
import { escapeHTML, sanitizeHTML } from '@/utils'
import { Link } from 'frappe-ui/frappe'
import { AlertTriangle } from 'lucide-vue-next'

const show = defineModel()
const assignments = defineModel<Assignments>('assignments')

interface Assignment {
	title: string
	type: string
	question: string
	course?: string
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
})

const props = defineProps({
	assignmentID: {
		type: String,
		default: 'new',
	},
})

const showAssignmentSaveWarningModal = ref(false)
const assignmentVersionChangeLog = ref('')

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
		call('lms.lms.api.check_content_before_save', {
			content_doctype: 'LMS Assignment',
			content_name: props.assignmentID
		}).then(res => {
			if (res && res.has_submissions) {
				showAssignmentSaveWarningModal.value = true
			} else {
				updateAssignment()
			}
		}).catch(() => {
			updateAssignment()
		})
	}
}

const handleCreateNewAssignmentVersion = () => {
	const log = assignmentVersionChangeLog.value.trim()
	if (!log) {
		toast.error(__('Please enter a change log description'))
		return
	}
	showAssignmentSaveWarningModal.value = false
	
	call('lms.lms.api.create_new_content_version', {
		content_doctype: 'LMS Assignment',
		content_name: props.assignmentID,
		change_log: log,
		doc_data: JSON.stringify(assignment)
	}).then(res => {
		toast.success(__('New version created successfully'))
		assignmentVersionChangeLog.value = ''
		show.value = false
		assignments.value?.reload()
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to create new version'))
	})
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
