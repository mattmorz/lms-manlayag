<template>
	<div
		v-if="assignment.data"
		class="grid grid-cols-2 h-full"
		:class="{ 'border rounded-lg overflow-auto': !showTitle }"
	>
		<div
			class="border-r p-5 overflow-y-auto h-[calc(100vh-3.2rem)]"
			:class="{ 'h-full': !showTitle }"
		>
			<div v-if="showTitle" class="text-lg font-semibold mb-5 text-ink-gray-9">
				<div v-if="submissionName === 'new'">
					{{ __('Submission by') }} {{ user.data?.full_name }}
				</div>
				<div v-else>
					{{ __('Submission by') }} {{ submissionResource.doc?.member_name }}
				</div>
			</div>
			<div v-if="assignment.data.due_date" class="bg-surface-blue-2 text-ink-blue-2 p-3 rounded-md mb-4 text-sm leading-5">
				<div>
					<strong>{{ __('Due Date') }}:</strong> {{ assignment.data.due_date }} {{ assignment.data.due_time || '' }}
				</div>
				<div v-if="isLate" class="text-ink-red-3 font-semibold mt-1">
					{{ __('Warning: The deadline has passed. Submissions past the grace period will receive 0 marks.') }}
				</div>
			</div>
			<div class="text-sm text-ink-gray-7 font-medium mb-2">
				{{ __('Question') }}:
			</div>
			<div
				v-html="assignment.data.question"
				class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
			></div>
		</div>

		<div class="flex flex-col overflow-y-auto">
			<div class="p-5 space-y-5">
				<div class="flex items-center justify-between">
					<div class="font-semibold text-ink-gray-9">
						{{ __('Submission') }}
					</div>
					<div class="flex items-center space-x-2">
						<Badge v-if="isDirty" theme="orange">
							{{ __('Not Saved') }}
						</Badge>
						<Badge
							v-else-if="submissionResource.doc?.status"
							:theme="statusTheme"
							size="lg"
						>
							{{ submissionResource.doc?.status }}
						</Badge>
						<Button variant="solid" @click="submitAssignment()">
							{{ __('Save') }}
						</Button>
					</div>
				</div>
				<div
					v-if="
						submissionName != 'new' &&
						!['Pass', 'Fail'].includes(submissionResource.doc?.status) &&
						submissionResource.doc?.owner == user.data?.name
					"
					class="bg-surface-blue-2 text-ink-blue-2 p-3 rounded-md leading-5 text-sm"
				>
					{{ __("You've successfully submitted the assignment.") }}
					{{
						__(
							"Once the moderator grades your submission, you'll find the details here."
						)
					}}
					{{ __('Feel free to make edits to your submission if needed.') }}
				</div>
				<div v-if="showUploader()" class="border rounded-lg p-3">
					<div class="font-semibold mb-2">
						{{ __('Upload Assignment') }}
					</div>
					<div class="text-ink-gray-5 text-sm mt-1 mb-4">
						{{
							__('You can only upload {0} files').format(assignment.data.type)
						}}
					</div>
					<FileUploader
						v-if="!submissionResource.doc?.assignment_attachment"
						:fileTypes="getType()"
						:uploadArgs="{
							private: true,
						}"
						:validateFile="validateFile"
						@success="(file) => saveSubmission(file)"
					>
						<template #default="{ uploading, progress, openFileSelector }">
							<Button @click="openFileSelector" :loading="uploading">
								{{
									uploading
										? __('Uploading {0}%').format(progress)
										: __('Upload File')
								}}
							</Button>
						</template>
					</FileUploader>
					<div v-else>
						<div class="flex items-center text-ink-gray-7">
							<a
								:href="submissionResource.doc.assignment_attachment"
								target="_blank"
								class="cursor-pointer !no-underline text-sm leading-5"
							>
								<div class="flex items-center">
									<div class="border rounded-md p-2 mr-2">
										<FileText class="h-5 w-5 stroke-1.5" />
									</div>
									<span>
										{{
											submissionResource.doc.assignment_attachment
												.split('/')
												.pop()
										}}
									</span>
								</div>
							</a>
							<X
								v-if="canModifyAssignment"
								@click="removeSubmission()"
								class="bg-surface-gray-3 rounded-md cursor-pointer stroke-1.5 w-5 h-5 p-1 ml-4"
							/>
						</div>
					</div>
				</div>
				<div v-else-if="assignment.data.type == 'URL'">
					<div class="text-xs text-ink-gray-5 mb-1">
						{{ __('Enter a URL') }}
					</div>
					<FormControl
						v-model="answer"
						type="text"
						:readonly="!canModifyAssignment"
					/>
				</div>
				<div v-else>
					<div class="text-sm mb-2 text-ink-gray-7">
						{{ __('Write your answer here') }}
					</div>
					<TextEditor
						:content="answer"
						@change="(val) => (answer = val)"
						:editable="true"
						:fixedMenu="true"
						:uploadArgs="{
							private: true,
						}"
						editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
					/>
				</div>

				<!-- Peer Review Panel -->
				<div v-if="assignment.data?.enable_peer_review">
					<!-- Tasks for student reviewer -->
					<div v-if="assignedReviews.data?.length && submissionName !== 'new'" class="border rounded-lg p-4 bg-surface-gray-2 space-y-3 mt-4">
						<h4 class="font-bold text-ink-gray-9 text-sm">
							{{ __('Peer Review Tasks') }}
						</h4>
						<p class="text-xs text-ink-gray-6">
							{{ __('Evaluate the following peers to complete your assignment requirement.') }}
						</p>
						<div class="space-y-2">
							<div
								v-for="task in assignedReviews.data"
								:key="task.name"
								class="flex items-center justify-between p-3 rounded-lg bg-surface-white border border-outline-gray-2 hover:border-indigo-200 transition-colors"
							>
								<div>
									<span class="text-xs text-ink-gray-6">
										{{ __('Reviewee') }}:
									</span>
									<span class="text-xs font-semibold text-ink-gray-9 ml-1">
										{{ task.reviewee_name }}
									</span>
									<div class="text-[10px] text-ink-gray-5">
										{{ __('Due') }}: {{ task.due_date ? dayjs(task.due_date).format('MMMM D, YYYY') : __('No due date') }}
									</div>
								</div>
								<div>
									<Badge v-if="task.status === 'Completed'" theme="green">
										{{ __('Completed') }}
									</Badge>
									<Button
										v-else
										variant="solid"
										size="sm"
										class="rounded-md shadow-none"
										@click="openReviewModal(task)"
									>
										<template #prefix>
											<Edit class="size-4 stroke-1.5" />
										</template>
										{{ __('Evaluate') }}
									</Button>
								</div>
							</div>
						</div>
					</div>

					<!-- Received feedback -->
					<div v-if="receivedReviews.data?.length && submissionName !== 'new'" class="border rounded-lg p-4 space-y-4 mt-6 bg-surface-gray-1">
						<div class="flex items-center justify-between border-b pb-2">
							<h4 class="font-bold text-ink-gray-9 text-sm">
								{{ __('Peer Feedback Received') }}
							</h4>
							<div class="text-right">
								<span class="text-xs text-ink-gray-5">{{ __('Aggregated Score') }}:</span>
								<span class="text-sm font-black text-indigo-700 ml-1">
									{{ submissionResource.doc?.peer_review_score?.toFixed(1) || 0 }}%
								</span>
							</div>
						</div>
						<div class="space-y-4">
							<div
								v-for="(rev, rIdx) in receivedReviews.data"
								:key="rIdx"
								class="space-y-2 border-b pb-3 last:border-b-0 last:pb-0"
							>
								<div class="flex justify-between items-center text-xs">
									<span class="font-bold text-ink-gray-8">
										{{ rev.reviewer_name }}
									</span>
									<Badge theme="indigo">
										{{ __('Score') }}: {{ rev.score }}%
									</Badge>
								</div>

								<div class="grid grid-cols-2 gap-2 text-xs">
									<div v-if="rev.strengths" class="p-2 bg-green-50 rounded">
										<span class="font-semibold text-green-900">{{ __('Strengths') }}:</span>
										<p class="text-green-800 mt-1">{{ rev.strengths }}</p>
									</div>
									<div v-if="rev.areas_for_improvement" class="p-2 bg-amber-50 rounded">
										<span class="font-semibold text-amber-900">{{ __('Areas for Improvement') }}:</span>
										<p class="text-amber-800 mt-1">{{ rev.areas_for_improvement }}</p>
									</div>
								</div>

								<div v-if="rev.recommendations || rev.general_feedback" class="text-xs space-y-1">
									<div v-if="rev.recommendations">
										<span class="font-semibold text-ink-gray-6">{{ __('Recommendations') }}:</span>
										<p class="text-ink-gray-8 ml-1">{{ rev.recommendations }}</p>
									</div>
									<div v-if="rev.general_feedback">
										<span class="font-semibold text-ink-gray-6">{{ __('General Feedback') }}:</span>
										<p class="text-ink-gray-8 ml-1">{{ rev.general_feedback }}</p>
									</div>
								</div>

								<div v-if="rev.criteria_feedback?.length" class="text-xs mt-2 pl-2 border-l-2 border-indigo-200 space-y-1">
									<div v-for="cf in rev.criteria_feedback" :key="cf.criterion" class="flex justify-between items-start">
										<div>
											<span class="font-semibold text-ink-gray-7">{{ cf.criterion }}</span>:
											<span class="text-ink-gray-6 ml-1">{{ cf.comments || __('No comment') }}</span>
										</div>
										<span class="text-ink-gray-5 font-semibold">
											{{ cf.score }}
										</span>
									</div>
								</div>

								<div class="flex items-center space-x-2 mt-2 pt-2 border-t border-outline-gray-2" v-if="user.data?.is_moderator || user.data?.is_evaluator || user.data?.is_instructor">
									<Button
										variant="outline"
										size="xs"
										theme="red"
										@click="removeReview(rev.name)"
									>
										{{ __('Remove') }}
									</Button>
									<Button
										variant="outline"
										size="xs"
										@click="requestRevision(rev.review_assignment)"
									>
										{{ __('Request Revision') }}
									</Button>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div
					v-if="
						user.data?.name == submissionResource.doc?.owner &&
						submissionResource.doc?.comments
					"
					class="mt-8 p-3 border rounded-lg"
				>
					<div class="text-ink-gray-5 mb-4">
						{{ __('Comments by Evaluator') }}
					</div>
					<div
						class="leading-6 text-ink-gray-9"
						v-html="submissionResource.doc.comments"
					></div>
				</div>

				<!-- Peer Review Evaluation Modal -->
				<PeerReviewModal
					v-if="showReviewModal"
					v-model="showReviewModal"
					:assignmentName="activeReviewTask.assignment"
					:peerAssignmentName="activeReviewTask.name"
					@success="handleReviewSuccess"
				/>

				<!-- Grading -->
				<div v-if="canGradeSubmission" class="mt-8 space-y-4">
					<div class="font-semibold mb-2 text-ink-gray-9">
						{{ __('Grading') }}
					</div>
					<FormControl
						v-if="submissionResource.doc"
						v-model="submissionResource.doc.status"
						:label="__('Grade')"
						type="select"
						:options="submissionStatusOptions"
					/>
					<FormControl
						v-if="submissionResource.doc"
						v-model.number="submissionResource.doc.score"
						:label="__('Score (%)')"
						type="number"
						min="0"
						max="100"
						@input="isDirty = true"
					/>
					<div>
						<div class="text-sm text-ink-gray-5 mb-1">
							{{ __('Comments') }}
						</div>
						<TextEditor
							:content="comments"
							@change="
								(val) => {
									comments = val
									isDirty = true
								}
							"
							:editable="true"
							:fixedMenu="true"
							:uploadArgs="{
								private: true,
							}"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import {
	Badge,
	Button,
	call,
	createResource,
	createDocumentResource,
	FileUploader,
	FormControl,
	TextEditor,
	toast,
	dayjs,
} from 'frappe-ui'
import { computed, inject, onMounted, onBeforeUnmount, ref, watch, onUpdated } from 'vue'
import { FileText, X, Edit } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import PeerReviewModal from '@/components/Modals/PeerReviewModal.vue'

const answer = ref(null)
const comments = ref(null)
const router = useRouter()
const user = inject('$user')
const isDirty = ref(false)

const showReviewModal = ref(false)
const activeReviewTask = ref(null)

const assignedReviews = createResource({
	url: 'lms.lms.api.get_assigned_peer_reviews',
	auto: true,
})

const receivedReviews = createResource({
	url: 'lms.lms.api.get_peer_reviews_for_submission',
	makeParams() {
		return {
			submission_name: props.submissionName,
		}
	},
	auto: false,
})

watch(
	() => props.submissionName,
	(val) => {
		if (val && val !== 'new') {
			receivedReviews.reload()
		}
	},
	{ immediate: true }
)

const openReviewModal = (task) => {
	activeReviewTask.value = task
	showReviewModal.value = true
}

const handleReviewSuccess = () => {
	assignedReviews.reload()
	receivedReviews.reload()
	submissionResource.reload()
}

const props = defineProps({
	assignmentID: {
		type: String,
		required: true,
	},
	submissionName: {
		type: String,
		default: 'new',
	},
	showTitle: {
		type: Boolean,
		default: true,
	},
})

onMounted(() => {
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
		submitAssignment()
		e.preventDefault()
	}
}

onBeforeUnmount(() => {
	window.removeEventListener('keydown', keyboardShortcut)
})

const assignment = createResource({
	url: 'frappe.client.get',
	params: {
		doctype: 'LMS Assignment',
		name: props.assignmentID,
	},
	auto: true,
	onSuccess(data) {
		if (props.submissionName != 'new') {
			submissionResource.reload()
		}
	},
})

const newSubmission = createResource({
	url: 'frappe.client.insert',
	makeParams(values) {
		let doc = {
			doctype: 'LMS Assignment Submission',
			assignment: props.assignmentID,
			member: user.data?.name,
		}
		if (!showUploader()) {
			doc.answer = answer.value
		}
		return {
			doc: doc,
		}
	},
})

const submissionResource = createDocumentResource({
	doctype: 'LMS Assignment Submission',
	name: props.submissionName,
	onError(err) {
		toast.error(err.messages?.[0] || err)
	},
	auto: false,
	cache: [user.data?.name, props.assignmentID],
})

watch(submissionResource, () => {
	if (submissionResource.doc) {
		if (submissionResource.doc.answer) {
			answer.value = submissionResource.doc.answer
		}
		if (submissionResource.doc.comments) {
			comments.value = submissionResource.doc.comments
		}
		if (submissionResource.isDirty) {
			isDirty.value = true
		} else if (
			showUploader() &&
			!submissionResource.doc.assignment_attachment
		) {
			isDirty.value = true
		} else if (!showUploader() && !answer.value) {
			isDirty.value = true
		} else {
			isDirty.value = false
		}
	}
})

watch(
	() => submissionResource.doc,
	() => {
		if (
			props.submissionName == 'new' &&
			submissionResource.doc?.assignment_attachment
		) {
			isDirty.value = true
		}
	}
)

const submitAssignment = () => {
	if (props.submissionName != 'new') {
		let evaluator =
			submissionResource.doc && submissionResource.doc.owner != user.data?.name
				? user.data?.name
				: null

		if (assignment.data?.enable_peer_review && canGradeSubmission.value) {
			submissionResource.doc.peer_review_overridden = 1
			submissionResource.doc.peer_review_override_score = submissionResource.doc.score
		}

		submissionResource.setValue.submit(
			{
				...submissionResource.doc,
				evaluator: evaluator,
				comments: comments.value,
				answer: answer.value,
			},
			{
				onSuccess(data) {
					isDirty.value = false
					toast.success(__('Changes saved successfully'))
				},
			}
		)
	} else {
		addNewSubmission()
	}
}

const removeReview = async (reviewName) => {
	if (!confirm(__('Are you sure you want to remove this peer review?'))) return
	try {
		await call('lms.lms.api.remove_peer_review', { review_name: reviewName })
		toast.success(__('Peer review removed successfully'))
		receivedReviews.reload()
		submissionResource.reload()
	} catch (e) {
		toast.error(e.messages?.[0] || e.message || __('Failed to remove review'))
	}
}

const requestRevision = async (assignmentName) => {
	if (!confirm(__('Are you sure you want to request a revision for this peer review?'))) return
	try {
		await call('lms.lms.api.request_peer_review_revision', { review_assignment_name: assignmentName })
		toast.success(__('Revision requested successfully'))
		receivedReviews.reload()
		submissionResource.reload()
	} catch (e) {
		toast.error(e.messages?.[0] || e.message || __('Failed to request revision'))
	}
}

const addNewSubmission = () => {
	newSubmission.submit(
		{},
		{
			onSuccess(data) {
				toast.success(__('Assignment submitted successfully'))
				if (router.currentRoute.value.name == 'AssignmentSubmission') {
					router.push({
						name: 'AssignmentSubmission',
						params: {
							assignmentID: props.assignmentID,
							submissionName: data.name,
						},
						query: { fromLesson: router.currentRoute.value.query.fromLesson },
					})
				} else {
					markLessonProgress()
					router.go()
				}
				submissionResource.name = data.name
				submissionResource.reload()
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
			},
		}
	)
}

const saveSubmission = (file) => {
	isDirty.value = true
	submissionResource.doc.assignment_attachment = file.file_url
}

const markLessonProgress = () => {
	if (router.currentRoute.value.name == 'Lesson') {
		let courseName = router.currentRoute.value.params.courseName
		let chapterNumber = router.currentRoute.value.params.chapterNumber
		let lessonNumber = router.currentRoute.value.params.lessonNumber

		call('lms.lms.api.mark_lesson_progress', {
			course: courseName,
			chapter_number: chapterNumber,
			lesson_number: lessonNumber,
		})
	}
}

const getType = () => {
	const type = assignment.data?.type
	if (type == 'Image') {
		return ['image/*']
	} else if (type == 'Document') {
		return [
			'.doc',
			'.docx',
			'.xml',
			'application/msword',
			'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		]
	} else if (type == 'PDF') {
		return ['.pdf']
	}
}

const validateFile = (file) => {
	let type = assignment.data?.type
	let extension = file.name.split('.').pop().toLowerCase()
	if (type == 'Image' && !['jpg', 'jpeg', 'png'].includes(extension)) {
		return 'Only image file is allowed.'
	} else if (
		type == 'Document' &&
		!['doc', 'docx', 'xml'].includes(extension)
	) {
		return 'Only document file is allowed.'
	} else if (type == 'PDF' && !['pdf'].includes(extension)) {
		return 'Only PDF file is allowed.'
	}
}

const removeSubmission = () => {
	isDirty.value = true
	submissionResource.doc.assignment_attachment = ''
}

const canGradeSubmission = computed(() => {
	return (
		(user.data?.is_moderator ||
			user.data?.is_evaluator ||
			user.data?.is_instructor) &&
		props.submissionName != 'new' &&
		router.currentRoute.value.name == 'AssignmentSubmission'
	)
})

const canModifyAssignment = computed(() => {
	return (
		!submissionResource.doc ||
		(submissionResource.doc?.owner == user.data?.name &&
			submissionResource.doc?.status == 'Not Graded')
	)
})

const submissionStatusOptions = computed(() => {
	return [
		{ label: 'Not Graded', value: 'Not Graded' },
		{ label: 'Pass', value: 'Pass' },
		{ label: 'Fail', value: 'Fail' },
	]
})

const statusTheme = computed(() => {
	if (!submissionResource.doc) {
		return 'orange'
	} else if (submissionResource.doc.status == 'Pass') {
		return 'green'
	} else if (submissionResource.doc.status == 'Not Graded') {
		return 'blue'
	} else {
		return 'red'
	}
})

const showUploader = () => {
	return ['PDF', 'Image', 'Document'].includes(assignment.data?.type)
}

const isLate = computed(() => {
	if (!assignment.data?.due_date) return false
	const dueTimeStr = assignment.data.due_time || '23:59:59'
	const dueDatetime = new Date(`${assignment.data.due_date}T${dueTimeStr}`)
	return new Date() > dueDatetime
})
</script>
