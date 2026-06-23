<template>
	<div class="space-y-6">
		<!-- Summary Cards -->
		<div class="grid grid-cols-4 gap-5">
			<div class="p-4 rounded-lg bg-surface-white border border-outline-gray-2 space-y-1">
				<span class="text-xs text-ink-gray-5 font-semibold uppercase tracking-wider">
					{{ __('Total Submissions') }}
				</span>
				<div class="text-2xl font-black text-ink-gray-9">
					{{ summary.submissions || 0 }}
				</div>
			</div>
			<div class="p-4 rounded-lg bg-surface-white border border-outline-gray-2 space-y-1">
				<span class="text-xs text-ink-gray-5 font-semibold uppercase tracking-wider">
					{{ __('Reviews Assigned') }}
				</span>
				<div class="text-2xl font-black text-ink-gray-9">
					{{ summary.assigned || 0 }}
				</div>
			</div>
			<div class="p-4 rounded-lg bg-surface-white border border-outline-gray-2 space-y-1">
				<span class="text-xs text-ink-gray-5 font-semibold uppercase tracking-wider">
					{{ __('Reviews Completed') }}
				</span>
				<div class="text-2xl font-black text-green-700">
					{{ summary.completed || 0 }}
				</div>
			</div>
			<div class="p-4 rounded-lg bg-surface-white border border-outline-gray-2 space-y-1">
				<span class="text-xs text-ink-gray-5 font-semibold uppercase tracking-wider">
					{{ __('Completion Rate') }}
				</span>
				<div class="text-2xl font-black text-indigo-700">
					{{ summary.completionRate.toFixed(1) }}%
				</div>
			</div>
		</div>

		<!-- Action Bar -->
		<div class="flex justify-between items-center bg-surface-gray-2 p-4 rounded-lg border border-outline-gray-2">
			<div>
				<h4 class="font-bold text-ink-gray-9 text-sm">
					{{ __('Peer Reviewer Assignment') }}
				</h4>
				<p class="text-xs text-ink-gray-6 mt-0.5">
					{{ __('Assign reviews to students who have submitted their work.') }}
				</p>
			</div>
			<Button variant="solid" :loading="assigning" @click="triggerAssign">
				{{ __('Run Reviewer Assignment') }}
			</Button>
		</div>

		<!-- Statistics Table -->
		<div class="bg-surface-white rounded-lg border border-outline-gray-2 overflow-hidden p-5">
			<h4 class="font-bold text-ink-gray-9 text-sm mb-4">
				{{ __('Reviewer Quality & Activity') }}
			</h4>

			<div v-if="stats.loading" class="py-12 flex justify-center items-center">
				<span class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></span>
			</div>

			<div v-else-if="!stats.data?.length" class="p-8 text-center text-ink-gray-5 italic">
				{{ __('No peer reviewer activity found.') }}
			</div>

			<div v-else>
				<ListView
					:columns="statsColumns"
					:rows="stats.data"
					rowKey="reviewer"
					:options="{
						selectable: false,
					}"
				>
					<ListHeader
						class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
					>
						<ListHeaderItem :item="item" v-for="item in statsColumns">
							<template #prefix="{ item }">
								<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
							</template>
						</ListHeaderItem>
					</ListHeader>
					<ListRows>
						<ListRow v-for="row in stats.data" :key="row.reviewer" :row="row">
							<template #default="{ column }">
								<ListRowItem :item="row[column.key]" :align="column.align">
									<div v-if="column.key === 'reviewer_name'" class="font-medium">
										{{ row.reviewer_name }}
									</div>
									<div v-else-if="column.key === 'completed'" class="text-green-700 font-semibold">
										{{ row.completed }}
									</div>
									<div v-else-if="column.key === 'completion_rate'">
										<Badge :theme="row.completion_rate >= 80 ? 'green' : row.completion_rate >= 50 ? 'orange' : 'red'">
											{{ row.completion_rate.toFixed(1) }}%
										</Badge>
									</div>
									<div v-else-if="column.key === 'avg_comment_length'">
										{{ Math.round(row.avg_comment_length) }} {{ __('chars') }}
									</div>
									<div v-else-if="column.key === 'timeliness'">
										<span class="text-green-700 font-semibold">{{ row.timely }}</span>
										<span class="text-ink-gray-4 mx-1">/</span>
										<span class="text-red-700 font-semibold">{{ row.late }}</span>
									</div>
									<div v-else-if="column.key === 'avg_deviation'">
										<span :class="row.avg_deviation > 15 ? 'text-red-600 font-semibold' : 'text-ink-gray-8'">
											±{{ row.avg_deviation.toFixed(1) }}%
										</span>
									</div>
									<div v-else>
										{{ row[column.key] }}
									</div>
								</ListRowItem>
							</template>
						</ListRow>
					</ListRows>
				</ListView>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	createResource,
	Button,
	Badge,
	toast,
	call,
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	FeatherIcon
} from 'frappe-ui'
import { ref, computed } from 'vue'

const statsColumns = computed(() => {
	return [
		{
			label: __('Reviewer'),
			key: 'reviewer_name',
			width: 2,
			icon: 'user',
		},
		{
			label: __('Assigned'),
			key: 'assigned',
			width: 1,
			align: 'center',
			icon: 'link-2',
		},
		{
			label: __('Completed'),
			key: 'completed',
			width: 1,
			align: 'center',
			icon: 'check-circle',
		},
		{
			label: __('Completion %'),
			key: 'completion_rate',
			width: 1.2,
			align: 'center',
			icon: 'percent',
		},
		{
			label: __('Avg Comment Length'),
			key: 'avg_comment_length',
			width: 1.5,
			align: 'center',
			icon: 'message-square',
		},
		{
			label: __('Timeliness'),
			key: 'timeliness',
			width: 1.5,
			align: 'center',
			icon: 'clock',
		},
		{
			label: __('Avg Consistency Deviation'),
			key: 'avg_deviation',
			width: 2.2,
			align: 'center',
			icon: 'trending-up',
		},
	]
})

const props = defineProps({
	assignmentID: {
		type: String,
		required: true,
	},
})

const assigning = ref(false)

// Fetch stats resource
const stats = createResource({
	url: 'lms.lms.api.get_reviewer_stats',
	params: {
		assignment_name: props.assignmentID,
	},
	auto: true,
})

// Summary metrics
const summary = computed(() => {
	let totalSubmissions = 0
	let totalAssigned = 0
	let totalCompleted = 0
	
	if (stats.data) {
		stats.data.forEach((row) => {
			totalAssigned += row.assigned
			totalCompleted += row.completed
		})
	}
	
	const rate = totalAssigned > 0 ? (totalCompleted / totalAssigned * 100) : 0
	
	return {
		submissions: stats.data?.length || 0,
		assigned: totalAssigned,
		completed: totalCompleted,
		completionRate: rate,
	}
})

const triggerAssign = async () => {
	assigning.value = true
	try {
		await call('lms.lms.api.assign_peer_reviewers', { assignment_name: props.assignmentID })
		toast.success('Reviewers assigned successfully!')
		stats.reload()
	} catch (e) {
		toast.error(e.messages?.[0] || e.message || 'Failed to assign reviewers.')
	} finally {
		assigning.value = false
	}
}
</script>
