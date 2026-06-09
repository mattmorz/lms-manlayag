<template>
	<div>
		<div class="flex items-center justify-between mb-4">
			<div class="text-ink-gray-9 font-medium">
				{{ studentCount.data ?? 0 }} {{ __('Students') }}
			</div>
			<div class="flex items-center space-x-2">
				<Button
					v-slot:default
					v-if="students.data?.length"
					:loading="exporting"
					@click="exportCSV()"
				>
					<template #prefix>
						<Download class="h-4 w-4" />
					</template>
					{{ __('Export CSV') }}
				</Button>
				<Button v-if="!readOnlyMode" @click="openStudentModal()">
					<template #prefix>
						<Plus class="h-4 w-4" />
					</template>
					{{ __('Add') }}
				</Button>
			</div>
		</div>

		<div v-if="students.data?.length">
			<ListView
				class="max-h-[75vh]"
				:columns="studentColumns"
				:rows="students.data"
				row-key="name"
				:options="{
					showTooltip: false,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem
						:item="item"
						v-for="item in studentColumns"
						:title="item.label"
					>
						<template #prefix="{ item }">
							<FeatherIcon
								v-if="item.icon"
								:name="item.icon"
								class="h-4 w-4 stroke-1.5"
							/>
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow
						:row="row"
						v-for="row in students.data"
						class="group cursor-pointer hover:bg-surface-gray-2 rounded"
						@click="openStudentProgressModal(row)"
					>
						<template #default="{ column, item }">
							<ListRowItem
								:item="row[column.key]"
								:align="column.align"
								class="text-sm"
							>
								<template #prefix>
									<div v-if="column.key == 'full_name'">
										<Avatar
											class="flex items-center"
											:image="row['user_image']"
											:label="item"
											size="sm"
										/>
									</div>
								</template>
								<div v-if="column.isCourse" class="font-medium text-ink-gray-7">
									<span v-if="row.course_grades?.[column.courseTitle]?.enable_grading_policy" class="font-semibold text-ink-green-3">
										{{ row.course_grades[column.courseTitle].final_percentage }}% ({{ row.course_grades[column.courseTitle].final_grade }})
									</span>
									<span v-else>
										{{ Math.floor(row.courses?.[column.courseTitle] || 0) }}%
									</span>
								</div>
								<div v-else-if="column.isAssessments" class="font-medium text-ink-gray-7">
									{{ Math.floor(row.average_assessments_progress || 0) }}%
								</div>
								<div
									v-slot:default
									v-else-if="column.key == 'progress'"
									class="flex items-center space-x-4 w-full"
								>
									<ProgressBar :progress="row[column.key]" size="sm" />
									<div class="text-xs">{{ row[column.key] }}%</div>
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
								@click="removeStudents(selections, unselectAll)"
							>
								<Trash2 class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
				<div class="mt-4 flex justify-center" v-if="students.hasNextPage">
					<Button @click="students.next()">
						{{ __('Load More') }}
					</Button>
				</div>
			</ListView>
		</div>
		<div v-else-if="!students.loading" class="text-sm italic text-ink-gray-5">
			{{ __('There are no students in this batch.') }}
		</div>
	</div>

	<StudentModal
		:batch="props.batch.data.name"
		v-model="showStudentModal"
		v-model:reloadStudents="students"
		v-model:batchModal="props.batch"
	/>
	<BatchStudentProgress
		:student="selectedStudent"
		v-model="showStudentProgressModal"
	/>
</template>
<script setup>
import {
	Avatar,
	Button,
	createListResource,
	createResource,
	FeatherIcon,
	ListHeader,
	ListHeaderItem,
	ListSelectBanner,
	ListRow,
	ListRows,
	ListView,
	ListRowItem,
	toast,
} from 'frappe-ui'
import { Plus, Trash2, Download } from 'lucide-vue-next'
import { ref, computed } from 'vue'
import StudentModal from '@/components/Modals/StudentModal.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import BatchStudentProgress from '@/components/Modals/BatchStudentProgress.vue'

const showStudentModal = ref(false)
const showStudentProgressModal = ref(false)
const selectedStudent = ref(null)
const readOnlyMode = window.read_only_mode

const props = defineProps({
	batch: {
		type: Object,
		default: null,
	},
})

const studentCount = createResource({
	url: 'frappe.client.get_count',
	cache: ['batch_student_count', props.batch?.data?.name],
	params: {
		doctype: 'LMS Batch Enrollment',
		filters: { batch: props.batch?.data?.name },
	},
	auto: true,
})

const students = createListResource({
	doctype: 'LMS Batch Enrollment',
	url: 'lms.lms.utils.get_batch_students',
	cache: ['batch_students', props.batch?.data?.name],
	pageLength: 50,
	filters: {
		batch: props.batch?.data?.name,
	},
	auto: true,
})

const studentColumns = computed(() => {
	const cols = [
		{
			label: 'Full Name',
			key: 'full_name',
			width: '15rem',
			icon: 'user',
		},
	]

	const courses = props.batch?.data?.courses || []
	const hasGradingPolicy = students.data?.some(student => {
		return Object.values(student.course_grades || {}).some(g => g.enable_grading_policy)
	})

	if (hasGradingPolicy && courses.length) {
		courses.forEach(course => {
			cols.push({
				label: course.title,
				key: `course_${course.course}`,
				isCourse: true,
				courseTitle: course.title,
				courseName: course.course,
				width: '12rem',
				icon: 'book',
			})
		})

		const hasAssessments = students.data?.some(student => {
			return Object.keys(student.assessments || {}).length > 0
		})
		if (hasAssessments) {
			cols.push({
				label: 'Assessments',
				key: 'assessments_progress',
				isAssessments: true,
				width: '10rem',
				icon: 'activity',
			})
		}
	} else {
		cols.push({
			label: 'Progress',
			key: 'progress',
			width: '10rem',
			icon: 'activity',
		})
	}

	cols.push({
		label: 'Last Active',
		key: 'last_active',
		width: '8rem',
		align: 'center',
		icon: 'clock',
	})

	return cols
})

const exporting = ref(false)

const allStudentsResource = createResource({
	url: 'lms.lms.utils.get_batch_students',
	makeParams() {
		return {
			filters: { batch: props.batch?.data?.name },
			limit: 10000,
		}
	},
})

const exportCSV = () => {
	if (exporting.value) return
	exporting.value = true
	allStudentsResource.submit(
		{},
		{
			onSuccess(allStudents) {
				if (!allStudents || !allStudents.length) {
					toast.error(__('No students to export'))
					exporting.value = false
					return
				}

				const headers = []
				const rowMappers = []

				headers.push('Full Name')
				rowMappers.push(row => row.full_name || '')

				headers.push('Email')
				rowMappers.push(row => row.email || '')

				const hasGradingPolicy = allStudents.some(student => {
					return Object.values(student.course_grades || {}).some(g => g.enable_grading_policy)
				})

				const courses = props.batch?.data?.courses || []

				if (hasGradingPolicy && courses.length) {
					courses.forEach(course => {
						headers.push(`${course.title} Progress/Grade`)
						rowMappers.push(row => {
							const gradeInfo = row.course_grades?.[course.title]
							if (gradeInfo?.enable_grading_policy) {
								return `${gradeInfo.final_percentage}% (${gradeInfo.final_grade})`
							} else {
								const prog = row.courses?.[course.title] || 0
								return `${Math.floor(prog)}%`
							}
						})
					})

					const hasAssessments = allStudents.some(student => {
						return Object.keys(student.assessments || {}).length > 0
					})
					if (hasAssessments) {
						headers.push('Assessments Progress')
						rowMappers.push(row => `${Math.floor(row.average_assessments_progress || 0)}%`)
					}
				}

				headers.push('Overall Progress')
				rowMappers.push(row => `${row.progress || 0}%`)

				headers.push('Last Active')
				rowMappers.push(row => row.last_active || '')

				const csvRows = []
				const escapeCSV = (val) => {
					if (val === null || val === undefined) return ''
					const stringVal = String(val)
					if (stringVal.includes(',') || stringVal.includes('"') || stringVal.includes('\n')) {
						return `"${stringVal.replace(/"/g, '""')}"`
					}
					return stringVal
				}

				csvRows.push(headers.map(escapeCSV).join(','))

				allStudents.forEach(row => {
					const values = rowMappers.map(mapper => mapper(row))
					csvRows.push(values.map(escapeCSV).join(','))
				})

				const csvContent = csvRows.join('\n')

				const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
				const url = URL.createObjectURL(blob)
				const link = document.createElement('a')
				link.setAttribute('href', url)
				link.setAttribute('download', `${props.batch?.data?.title || props.batch?.data?.name || 'batch'}_students_progress.csv`)
				link.style.visibility = 'hidden'
				document.body.appendChild(link)
				link.click()
				document.body.removeChild(link)

				toast.success(__('CSV exported successfully'))
				exporting.value = false
			},
			onError(err) {
				console.error(err)
				toast.error(__('Failed to export CSV'))
				exporting.value = false
			}
		}
	)
}

const openStudentModal = () => {
	showStudentModal.value = true
}

const openStudentProgressModal = (row) => {
	showStudentProgressModal.value = true
	selectedStudent.value = row
}

const deleteStudents = createResource({
	url: 'lms.lms.api.delete_documents',
	makeParams(values) {
		return {
			doctype: 'LMS Batch Enrollment',
			documents: values.students,
		}
	},
})

const removeStudents = (selections, unselectAll) => {
	deleteStudents.submit(
		{
			students: Array.from(selections),
		},
		{
			onSuccess(data) {
				students.reload()
				studentCount.reload()
				props.batch.reload()
				toast.success(__('Students deleted successfully'))
				unselectAll()
			},
		}
	)
}
</script>
