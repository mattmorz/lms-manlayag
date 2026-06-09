<template>
	<div>
		<div class="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4 border-b pb-4">
			<div class="flex items-center space-x-6">
				<div class="text-ink-gray-9 font-medium text-base pr-4 border-r">
					{{ studentCount.data ?? 0 }} {{ __('Students') }}
				</div>
				<!-- Sub tabs for Course Progress and Grade -->
				<div v-if="subTabs.length > 1" class="flex space-x-1">
					<button
						v-for="tab in subTabs"
						:key="tab.value"
						class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
						:class="activeSubTab === tab.value ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-6 hover:text-ink-gray-9'"
						@click="activeSubTab = tab.value"
					>
						{{ tab.label }}
					</button>
				</div>
			</div>
			<div class="flex items-center space-x-2 self-end sm:self-auto">
				<!-- Course selector for Grade tab -->
				<FormControl
					v-if="activeSubTab === 'grade' && gradingCourses.length"
					type="select"
					v-model="selectedGradingCourse"
					:options="gradingCourses.map(c => ({ label: c.title, value: c.title }))"
					class="w-48 !mb-0"
				/>

				<Button
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
				:columns="activeColumns"
				:rows="students.data"
				row-key="name"
				:options="{
					showTooltip: false,
				}"
			>
				<ListHeader
					class="mb-2 grid items-center rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem
						:item="item"
						v-for="item in activeColumns"
					>
						<template #prefix>
							<FeatherIcon
								v-if="item.icon"
								:name="item.icon"
								class="h-4 w-4 stroke-1.5"
							/>
						</template>
						<div class="flex items-center space-x-1">
							<span>{{ item.label }}</span>
							<button
								v-if="item.isCategoryAverage"
								class="hover:bg-surface-gray-3 p-0.5 rounded cursor-pointer transition-colors"
								@click.stop="toggleCategory(item.categoryName)"
								:title="expandedCategories[item.categoryName] ? __('Collapse Assessments') : __('Expand Assessments')"
							>
								<ChevronRight v-if="!expandedCategories[item.categoryName]" class="h-3.5 w-3.5 text-ink-gray-5" />
								<ChevronDown v-else class="h-3.5 w-3.5 text-ink-gray-5" />
							</button>
						</div>
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
								<div v-if="column.isCourseProgress" class="font-medium text-ink-gray-7">
									{{ Math.floor(row.courses?.[column.courseTitle] || 0) }}%
								</div>
								<div v-else-if="column.isAssessmentsProgress" class="font-medium text-ink-gray-7">
									{{ Math.floor(row.average_assessments_progress || 0) }}%
								</div>
								<div v-else-if="column.isFinalGrade" class="font-medium text-ink-gray-7">
									<span v-if="row.course_grades?.[selectedGradingCourse]?.enable_grading_policy" class="font-semibold text-ink-green-3">
										{{ row.course_grades[selectedGradingCourse].final_percentage }}% ({{ row.course_grades[selectedGradingCourse].final_grade }})
									</span>
									<span v-else class="text-ink-gray-4">-</span>
								</div>
								<div v-else-if="column.isCategoryAverage" class="font-medium text-ink-gray-7">
									<span>
										{{ row.course_grades?.[selectedGradingCourse]?.categories?.find(c => c.category_name === column.categoryName)?.average || 0 }}%
									</span>
								</div>
								<div v-else-if="column.isCategoryItem" class="font-medium text-ink-gray-7">
									<span v-if="getItemScoreInfo(row, column.categoryName, column.itemName)" :class="getItemScoreInfo(row, column.categoryName, column.itemName).class">
										{{ getItemScoreInfo(row, column.categoryName, column.itemName).label }}
									</span>
									<span v-else class="text-ink-gray-4">-</span>
								</div>
								<div
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
	FormControl,
	toast,
} from 'frappe-ui'
import { Plus, Trash2, Download, ChevronRight, ChevronDown } from 'lucide-vue-next'
import { ref, computed, watch } from 'vue'
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

const activeSubTab = ref('progress')

const subTabs = computed(() => {
	const list = [
		{
			label: __('Course Progress'),
			value: 'progress',
		},
	]

	const courses = props.batch?.data?.courses || []
	const hasGradingPolicy = students.data?.some(student => {
		return Object.values(student.course_grades || {}).some(g => g.enable_grading_policy)
	})

	if (hasGradingPolicy && courses.length) {
		list.push({
			label: __('Grade'),
			value: 'grade',
		})
	}
	return list
})

const selectedGradingCourse = ref('')

const gradingCourses = computed(() => {
	const courses = props.batch?.data?.courses || []
	return courses.filter(c => {
		return students.data?.some(s => s.course_grades?.[c.title]?.enable_grading_policy)
	})
})

watch(gradingCourses, (newVal) => {
	if (newVal.length && !selectedGradingCourse.value) {
		selectedGradingCourse.value = newVal[0].title
	}
}, { immediate: true })

const expandedCategories = ref({})

const toggleCategory = (catName) => {
	expandedCategories.value[catName] = !expandedCategories.value[catName]
}

const progressColumns = computed(() => {
	const cols = [
		{
			label: 'Full Name',
			key: 'full_name',
			width: '18rem',
			icon: 'user',
		},
	]

	const courses = props.batch?.data?.courses || []
	courses.forEach(course => {
		cols.push({
			label: course.title,
			key: `course_progress_${course.course}`,
			isCourseProgress: true,
			courseTitle: course.title,
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
			isAssessmentsProgress: true,
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

const gradeColumns = computed(() => {
	if (!selectedGradingCourse.value) return []

	const cols = [
		{
			label: 'Full Name',
			key: 'full_name',
			width: '18rem',
			icon: 'user',
		},
		{
			label: 'Final Grade',
			key: 'final_grade',
			isFinalGrade: true,
			width: '10rem',
			icon: 'award',
		},
	]

	const studentWithGrades = students.data?.find(s => s.course_grades?.[selectedGradingCourse.value]?.enable_grading_policy)
	if (studentWithGrades) {
		const categories = studentWithGrades.course_grades[selectedGradingCourse.value].categories || []
		categories.forEach(cat => {
			const isExpanded = !!expandedCategories.value[cat.category_name]
			cols.push({
				label: `${cat.category_name} (${cat.weight}%)`,
				key: `cat_avg_${cat.category_name}`,
				isCategoryAverage: true,
				categoryName: cat.category_name,
				width: '10rem',
				icon: 'bar-chart-2',
			})

			if (isExpanded) {
				const items = cat.items || []
				items.forEach(item => {
					cols.push({
						label: item.title,
						key: `item_${cat.category_name}_${item.name}`,
						isCategoryItem: true,
						categoryName: cat.category_name,
						itemName: item.name,
						width: '10rem',
						icon: item.type === 'Quiz' ? 'help-circle' : 'file-text',
					})
				})
			}
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

const activeColumns = computed(() => {
	if (activeSubTab.value === 'grade') {
		return gradeColumns.value
	}
	return progressColumns.value
})

const getItemScoreInfo = (row, categoryName, itemName) => {
	const cat = row.course_grades?.[selectedGradingCourse.value]?.categories?.find(c => c.category_name === categoryName)
	const item = cat?.items?.find(i => i.name === itemName)
	if (!item) return null
	if (!item.is_submitted) {
		return { label: __('Pending'), class: 'text-ink-gray-4' }
	}
	if (item.is_late) {
		return { label: `0% (${__('Late')})`, class: 'text-ink-red-3 font-medium' }
	}
	return { label: `${item.score}%`, class: 'text-ink-gray-7' }
}

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

				if (activeSubTab.value === 'grade') {
					headers.push('Final Grade Percentage')
					rowMappers.push(row => {
						const gradeInfo = row.course_grades?.[selectedGradingCourse.value]
						return gradeInfo?.enable_grading_policy ? `${gradeInfo.final_percentage}%` : ''
					})

					headers.push('Final Grade Letter')
					rowMappers.push(row => {
						const gradeInfo = row.course_grades?.[selectedGradingCourse.value]
						return gradeInfo?.enable_grading_policy ? gradeInfo.final_grade : ''
					})

					const studentWithGrades = allStudents.find(s => s.course_grades?.[selectedGradingCourse.value]?.enable_grading_policy)
					if (studentWithGrades) {
						const categories = studentWithGrades.course_grades[selectedGradingCourse.value].categories || []
						categories.forEach(cat => {
							headers.push(`${cat.category_name} Average`)
							rowMappers.push(row => {
								const studentCat = row.course_grades?.[selectedGradingCourse.value]?.categories?.find(c => c.category_name === cat.category_name)
								return studentCat ? `${studentCat.average || 0}%` : '0%'
							})

							const items = cat.items || []
							items.forEach(item => {
								headers.push(`${cat.category_name} - ${item.title}`)
								rowMappers.push(row => {
									const info = getItemScoreInfo(row, cat.category_name, item.name)
									return info ? info.label : ''
								})
							})
						})
					}
				} else {
					const courses = props.batch?.data?.courses || []

					courses.forEach(course => {
						headers.push(`${course.title} Progress`)
						rowMappers.push(row => `${Math.floor(row.courses?.[course.title] || 0)}%`)
					})

					const hasAssessments = allStudents.some(student => {
						return Object.keys(student.assessments || {}).length > 0
					})
					if (hasAssessments) {
						headers.push('Assessments Progress')
						rowMappers.push(row => `${Math.floor(row.average_assessments_progress || 0)}%`)
					}

					headers.push('Overall Progress')
					rowMappers.push(row => `${row.progress || 0}%`)
				}

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
				const filename = activeSubTab.value === 'grade'
					? `${props.batch?.data?.title || props.batch?.data?.name || 'batch'}_${selectedGradingCourse.value.replace(/\s+/g, '_')}_grades.csv`
					: `${props.batch?.data?.title || props.batch?.data?.name || 'batch'}_students_progress.csv`
				link.setAttribute('download', filename)
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
