<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
	</header>
	<div class="md:w-3/4 md:mx-auto py-5 mx-5">
		<div class="flex justify-between items-center gap-5 mb-5 w-full">
			<div class="flex items-center gap-5 flex-1 max-w-xl">
				<Link
					doctype="LMS Assignment"
					v-model="assignmentID"
					:placeholder="__('Select Assignment')"
					class="flex-1"
				/>
				<Link
					doctype="User"
					v-model="member"
					:placeholder="__('Select Student')"
					class="flex-1"
				/>
			</div>
			<FormControl
				v-model="status"
				type="select"
				:options="statusOptions"
				:placeholder="__('Select Status')"
				class="w-100"
			/>
		</div>
		<!-- Tabs Navigation -->
		<div class="flex border-b border-outline-gray-2 mb-5" v-if="assignmentID && isPeerReviewEnabled">
			<button
				class="py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors duration-150"
				:class="activeTab === 'submissions' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-ink-gray-5 hover:text-ink-gray-7'"
				@click="activeTab = 'submissions'"
			>
				{{ __('Submissions') }}
			</button>
			<button
				class="py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors duration-150"
				:class="activeTab === 'peer-review' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-ink-gray-5 hover:text-ink-gray-7'"
				@click="activeTab = 'peer-review'"
			>
				{{ __('Peer Review Dashboard') }}
			</button>
		</div>

		<!-- Submissions Tab -->
		<div v-show="activeTab === 'submissions'">
			<template v-if="submissions.loading || submissions.data?.length">
				<ListView
					:columns="submissionColumns"
					:rows="submissions.data"
					rowKey="name"
					:options="{
						selectable: false,
					}"
				>
					<ListHeader
						class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
					>
						<ListHeaderItem :item="item" v-for="item in submissionColumns">
							<template #prefix="{ item }">
								<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
							</template>
						</ListHeaderItem>
					</ListHeader>
					<ListRows>
						<router-link
							v-for="row in submissions.data"
							:to="{
								name: 'AssignmentSubmission',
								params: {
									assignmentID: row.assignment,
									submissionName: row.name,
								},
							}"
						>
							<ListRow :row="row">
								<template #default="{ column, item }">
									<ListRowItem :item="row[column.key]" :align="column.align">
										<div v-if="column.key == 'status'">
											<Badge :theme="getStatusTheme(row[column.key])">
												{{ row[column.key] }}
											</Badge>
										</div>
										<div v-else>
											{{ row[column.key] }}
										</div>
									</ListRowItem>
								</template>
							</ListRow>
						</router-link>
					</ListRows>
				</ListView>
				<div
					v-if="submissions.data && submissions.hasNextPage"
					class="flex justify-center my-5"
				>
					<Button @click="submissions.next()">
						{{ __('Load More') }}
					</Button>
				</div>
			</template>
			<div
				v-else
				class="text-center p-5 text-ink-gray-5 mt-52 w-3/4 md:w-1/2 mx-auto space-y-2"
			>
				<Pencil class="size-8 mx-auto stroke-1 text-ink-gray-4" />
				<div class="text-xl font-medium">
					{{ __('No submissions') }}
				</div>
				<div class="leading-5">
					{{ __('There are no submissions for this assignment.') }}
				</div>
			</div>
		</div>

		<!-- Peer Review Tab -->
		<div v-if="activeTab === 'peer-review' && assignmentID">
			<PeerReviewDashboard :assignmentID="assignmentID" />
		</div>
	</div>
</template>
<script setup>
import {
	Badge,
	Breadcrumbs,
	createListResource,
	FormControl,
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	usePageMeta,
	call,
	FeatherIcon,
	Button,
	createResource,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Pencil } from 'lucide-vue-next'
import { sessionStore } from '../stores/session'
import Link from '@/components/Controls/Link.vue'
import PeerReviewDashboard from '@/components/PeerReviewDashboard.vue'

const activeTab = ref('submissions')
const isPeerReviewEnabled = ref(false)

const user = inject('$user')
const dayjs = inject('$dayjs')
const { brand } = sessionStore()
const router = useRouter()
const assignmentID = ref('')
const member = ref('')
const status = ref('')

const assignmentResource = createResource({
	url: 'frappe.client.get',
	makeParams(values) {
		return {
			doctype: 'LMS Assignment',
			name: values.name,
		}
	},
	onSuccess(assignmentDoc) {
		if (
			user.data?.roles?.includes('Course Creator') &&
			assignmentDoc.owner !== user.data.name &&
			!user.data?.is_moderator
		) {
			router.push({ name: 'Courses' })
		}
	}
})

onMounted(() => {
	if (!user.data?.is_instructor && !user.data?.is_moderator) {
		router.push({ name: 'Courses' })
	}
	assignmentID.value = router.currentRoute.value.query.assignmentID
	member.value = router.currentRoute.value.query.member
	status.value = router.currentRoute.value.query.status
	if (assignmentID.value) {
		assignmentResource.submit({ name: assignmentID.value })
	}
	reloadSubmissions()
})

const getAssignmentFilters = () => {
	let filters = {}
	if (assignmentID.value) {
		filters.assignment = assignmentID.value
	}
	if (member.value) {
		filters.member = member.value
	}
	if (status.value) {
		filters.status = status.value
	}
	return filters
}

const submissions = createListResource({
	doctype: 'LMS Assignment Submission',
	fields: [
		'name',
		'assignment',
		'assignment_title',
		'member_name',
		'creation',
		'status',
	],
	orderBy: 'creation desc',
	transform(data) {
		return data.map((row) => {
			return {
				...row,
				creation: dayjs(row.creation).fromNow(),
			}
		})
	},
})

watch([assignmentID, member, status], () => {
	router.push({
		query: {
			assignmentID: assignmentID.value,
			member: member.value,
			status: status.value,
		},
	})
	reloadSubmissions()
})

const reloadSubmissions = () => {
	submissions.update({
		filters: getAssignmentFilters(),
	})
	submissions.reload()
}

const submissionColumns = computed(() => {
	return [
		{
			label: __('Member'),
			key: 'member_name',
			width: 1,
			icon: 'user',
		},
		{
			label: __('Assignment'),
			key: 'assignment_title',
			width: 2,
			icon: 'file-text',
		},
		{
			label: __('Submitted'),
			key: 'creation',
			width: 1,
			align: 'left',
			icon: 'calendar',
		},
		{
			label: __('Status'),
			key: 'status',
			width: 1,
			align: 'center',
			icon: 'check-circle',
		},
	]
})

const statusOptions = computed(() => {
	return [
		{ label: '', value: '' },
		{ label: 'Pass', value: 'Pass' },
		{ label: 'Fail', value: 'Fail' },
		{ label: 'Not Graded', value: 'Not Graded' },
	]
})

const getStatusTheme = (status) => {
	if (status === 'Pass') {
		return 'green'
	} else if (status === 'Not Graded') {
		return 'blue'
	} else {
		return 'red'
	}
}

const breadcrumbs = computed(() => {
	return [
		{
			label: 'Assignment Submissions',
		},
	]
})

usePageMeta(() => {
	return {
		title: __('Assignment Submissions'),
		icon: brand.favicon,
	}
})

watch(assignmentID, async (newVal) => {
	if (newVal) {
		try {
			const res = await call('frappe.client.get_value', {
				doctype: 'LMS Assignment',
				fieldname: ['enable_peer_review'],
				filters: { name: newVal }
			})
			isPeerReviewEnabled.value = res && res.enable_peer_review ? true : false
		} catch (e) {
			isPeerReviewEnabled.value = false
		}
	} else {
		isPeerReviewEnabled.value = false
		activeTab.value = 'submissions'
	}
}, { immediate: true })
</script>
