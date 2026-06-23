<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div class="space-x-2 flex items-center">
			<router-link
				:to="{
					name: 'AssignmentSubmissionList',
				}"
			>
				<Button>
					<template #prefix>
						<ClipboardList class="size-4 stroke-1.5" />
					</template>
					{{ __('Check All Submissions') }}
				</Button>
			</router-link>
			<Button
				v-if="!readOnlyMode"
				variant="solid"
				@click="
					() => {
						if (currentTab === 'assignments') {
							assignmentID = 'new'
							showAssignmentForm = true
						} else {
							rubricID = 'new'
							showRubricForm = true
						}
					}
				"
			>
				<template #prefix>
					<Plus class="w-4 h-4" />
				</template>
				{{ __('Create') }}
			</Button>
		</div>
	</header>

	<div class="py-5 mx-5">
		<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
			<TabButtons :buttons="assignmentTabs" v-model="currentTab" class="w-fit" />
			<div
				v-if="(currentTab === 'assignments' && (assignments.data?.length || assignmentCount > 0)) || (currentTab === 'rubrics')"
				class="flex items-center gap-5 justify-end ml-auto"
			>
				<FormControl
					v-model="titleFilter"
					:placeholder="__('Search by title')"
					class="w-64"
				/>
				<FormControl
					v-if="currentTab === 'assignments'"
					v-model="typeFilter"
					type="select"
					:options="assignmentTypes"
					:placeholder="__('Type')"
					class="w-100"
				/>
			</div>
		</div>

		<div v-if="currentTab === 'assignments'">
			<ListView
				v-if="assignments.data?.length"
				:columns="assignmentColumns"
				:rows="assignments.data"
				row-key="name"
				:options="{
					showTooltip: false,
					selectable: !readOnlyMode,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in assignmentColumns">
						<template #prefix="{ item }">
							<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow
						v-for="row in assignments.data"
						:key="row.name"
						:row="row"
						class="hover:bg-surface-gray-1"
						@click="
							() => {
								if (readOnlyMode) return
								assignmentID = row.name
								showAssignmentForm = true
							}
						"
					>
						<template #default="{ column }">
							<ListRowItem :item="row[column.key]" :align="column.align">
								<div
									v-if="column.key == 'creation'"
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
				</ListRows>
				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="deleteAssignment(selections, unselectAll)"
							>
								<FeatherIcon name="trash-2" class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
			<EmptyState v-else type="Assignments" />
			<div
				v-if="assignments.data && assignments.hasNextPage"
				class="flex justify-center my-5"
			>
				<Button @click="assignments.next()">
					{{ __('Load More') }}
				</Button>
			</div>
		</div>

		<div v-else-if="currentTab === 'rubrics'">
			<ListView
				v-if="rubrics.data?.length"
				:columns="rubricColumns"
				:rows="rubrics.data"
				row-key="name"
				:options="{
					showTooltip: false,
					selectable: !readOnlyMode,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in rubricColumns">
						<template #prefix="{ item }">
							<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow
						v-for="row in rubrics.data"
						:key="row.name"
						:row="row"
						class="hover:bg-surface-gray-1"
						@click="
							() => {
								if (readOnlyMode) return
								rubricID = row.name
								showRubricForm = true
							}
						"
					>
						<template #default="{ column }">
							<ListRowItem :item="row[column.key]" :align="column.align">
								<div
									v-if="column.key == 'modified'"
									class="text-xs text-ink-gray-5"
								>
									{{ row[column.key] }}
								</div>
								<div v-else-if="column.key == 'is_public'">
									<Badge :theme="row[column.key] ? 'green' : 'gray'">
										{{ row[column.key] ? __('Shared') : __('Private') }}
									</Badge>
								</div>
								<div v-else class="truncate max-w-xs">
									{{ row[column.key] }}
								</div>
							</ListRowItem>
						</template>
					</ListRow>
				</ListRows>
				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="deleteRubrics(selections, unselectAll)"
							>
								<FeatherIcon name="trash-2" class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
			<EmptyState v-else type="Rubrics" />
			<div
				v-if="rubrics.data && rubrics.hasNextPage"
				class="flex justify-center my-5"
			>
				<Button @click="rubrics.next()">
					{{ __('Load More') }}
				</Button>
			</div>
		</div>
	</div>

	<AssignmentForm
		v-model="showAssignmentForm"
		v-model:assignments="assignments"
		:assignmentID="assignmentID"
	/>

	<RubricForm
		v-model="showRubricForm"
		:rubricID="rubricID"
		@saved="rubrics.reload()"
	/>
</template>
<script setup>
import {
	Breadcrumbs,
	Button,
	call,
	createListResource,
	FormControl,
	ListView,
	usePageMeta,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	ListSelectBanner,
	FeatherIcon,
	toast,
	TabButtons,
	Badge,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { Plus, ClipboardList } from 'lucide-vue-next'
import { useRouter, useRoute } from 'vue-router'
import { sessionStore } from '../stores/session'
import AssignmentForm from '@/components/Modals/AssignmentForm.vue'
import RubricForm from '@/components/Modals/RubricForm.vue'
import EmptyState from '@/components/EmptyState.vue'

const user = inject('$user')
const dayjs = inject('$dayjs')
const titleFilter = ref('')
const typeFilter = ref('')
const showAssignmentForm = ref(false)
const assignmentID = ref('new')
const assignmentCount = ref(0)
const { brand } = sessionStore()
const router = useRouter()
const route = useRoute()
const readOnlyMode = window.read_only_mode

const currentTab = ref('assignments')
const assignmentTabs = computed(() => [
	{ label: __('Assignments'), value: 'assignments' },
	{ label: __('Rubrics'), value: 'rubrics' },
])

const showRubricForm = ref(false)
const rubricID = ref('new')

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		router.push({ name: 'Courses' })
	}
	if (route.query.new === 'true') {
		assignmentID.value = 'new'
		showAssignmentForm.value = true
	}
	getAssignmentCount()
	titleFilter.value = router.currentRoute.value.query.title || ''
	typeFilter.value = router.currentRoute.value.query.type || ''
})

watch(currentTab, (val) => {
	titleFilter.value = ''
	typeFilter.value = ''
	if (val === 'rubrics') {
		reloadRubrics()
	} else {
		reloadAssignments()
	}
})

watch([titleFilter, typeFilter], () => {
	if (currentTab.value === 'assignments') {
		router.push({
			query: {
				title: titleFilter.value,
				type: typeFilter.value,
			},
		})
		reloadAssignments()
	} else {
		reloadRubrics()
	}
})

const reloadAssignments = () => {
	assignments.update({
		filters: assignmentFilter.value,
	})
	assignments.reload()
}

const assignmentFilter = computed(() => {
	let filters = {}
	if (titleFilter.value) {
		filters.title = ['like', `%${titleFilter.value}%`]
	}
	if (typeFilter.value) {
		filters.type = typeFilter.value
	}
	return filters
})

const assignments = createListResource({
	doctype: 'LMS Assignment',
	fields: ['name', 'title', 'type', 'creation', 'question', 'course'],
	orderBy: 'modified desc',
	cache: ['assignments'],
	transform(data) {
		return data.map((row) => {
			return {
				...row,
				creation: dayjs(row.creation).fromNow(),
			}
		})
	},
})

const assignmentColumns = computed(() => {
	return [
		{
			label: __('Title'),
			key: 'title',
			width: 2,
			icon: 'file-text',
		},
		{
			label: __('Type'),
			key: 'type',
			width: 1,
			align: 'left',
			icon: 'layers',
		},
		{
			label: __('Created'),
			key: 'creation',
			width: 1,
			align: 'right',
			icon: 'calendar',
		},
	]
})

const deleteAssignment = (selections, unselectAll) => {
	Array.from(selections).forEach(async (assignmentName) => {
		await assignments.delete.submit(assignmentName)
	})
	unselectAll()
	toast.success(__('Assignments deleted successfully'))
}

const rubrics = createListResource({
	doctype: 'Peer Review Rubric',
	fields: ['name', 'title', 'description', 'is_public', 'owner', 'modified'],
	orderBy: 'modified desc',
	cache: ['rubrics'],
	transform(data) {
		return data.map((row) => {
			return {
				...row,
				modified: dayjs(row.modified).fromNow(),
				is_public: row.is_public === 1,
			}
		})
	},
})

const rubricColumns = computed(() => {
	return [
		{
			label: __('Title'),
			key: 'title',
			width: 2,
			icon: 'file-text',
		},
		{
			label: __('Description'),
			key: 'description',
			width: 3,
			icon: 'align-left',
		},
		{
			label: __('Status'),
			key: 'is_public',
			width: 1.5,
			icon: 'share-2',
		},
		{
			label: __('Last Modified'),
			key: 'modified',
			width: 1.5,
			align: 'right',
			icon: 'calendar',
		},
	]
})

const deleteRubrics = (selections, unselectAll) => {
	Array.from(selections).forEach(async (rubricName) => {
		await rubrics.delete.submit(rubricName)
	})
	unselectAll()
	toast.success(__('Rubrics deleted successfully'))
}

const reloadRubrics = () => {
	rubrics.update({
		filters: rubricFilter.value,
	})
	rubrics.reload()
}

const rubricFilter = computed(() => {
	let filters = {}
	if (titleFilter.value) {
		filters.title = ['like', `%${titleFilter.value}%`]
	}
	return filters
})

const getAssignmentCount = () => {
	call('frappe.client.get_count', {
		doctype: 'LMS Assignment',
	}).then((data) => {
		assignmentCount.value = data
	})
}

const assignmentTypes = computed(() => {
	let types = ['', 'Document', 'Image', 'PDF', 'URL', 'Text']
	return types.map((type) => {
		return {
			label: __(type),
			value: type,
		}
	})
})

const breadcrumbs = computed(() => [
	{
		label: __('Assignments'),
		route: { name: 'Assignments' },
	},
])

usePageMeta(() => {
	return {
		title: __('Assignments'),
		icon: brand.favicon,
	}
})
</script>
