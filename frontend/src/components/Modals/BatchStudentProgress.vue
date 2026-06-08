<template>
	<Dialog
		v-model="show"
		:options="{
			size: 'xl',
		}"
	>
		<template #body>
			<div class="p-5 space-y-10 text-base">
				<div class="flex items-center space-x-2">
					<Avatar :image="student.user_image" size="3xl" />
					<div class="space-y-1">
						<div class="flex items-center space-x-2">
							<div class="text-xl font-semibold text-ink-gray-9">
								{{ student.full_name }}
							</div>
							<Badge
								v-if="
									Object.keys(student.assessments).length ||
									Object.keys(student.courses).length
								"
								:theme="student.progress === 100 ? 'green' : 'red'"
							>
								{{ student.progress }}% {{ __('Complete') }}
							</Badge>
						</div>
						<div class="text-sm text-ink-gray-7">
							{{ student.email }}
						</div>
					</div>
				</div>

				<div class="space-y-8">
					<!-- Assessments -->
					<div
						v-if="Object.keys(student.assessments).length"
						class="space-y-2 text-sm"
					>
						<div
							class="flex items-center border-b pb-1 font-medium text-ink-gray-9"
						>
							<span class="flex-1">
								{{ __('Assessment') }}
							</span>
							<span>
								{{ __('Percentage/Status') }}
							</span>
						</div>
						<router-link
							v-for="assessment in Object.keys(student.assessments)"
							class="flex items-center text-ink-gray-7 font-medium"
							:to="{
								name:
									student.assessments[assessment].type == 'LMS Assignment'
										? 'AssignmentSubmission'
										: '',
								params:
									student.assessments[assessment].type == 'LMS Assignment'
										? {
												assignmentID:
													student.assessments[assessment].assessment,
												submissionName:
													student.assessments[assessment].submission,
										  }
										: {},
							}"
						>
							<span class="flex-1">
								{{ assessment }}
							</span>
							<span v-if="isAssignment(student.assessments[assessment].status)">
								<Badge
									:theme="
										getStatusTheme(student.assessments[assessment].status)
									"
								>
									{{ student.assessments[assessment].status }}
								</Badge>
							</span>
							<span v-else>
								{{ student.assessments[assessment].status }}
							</span>
						</router-link>
					</div>

					<!-- Courses -->
					<div
						v-if="Object.keys(student.courses).length"
						class="space-y-4 text-sm"
					>
						<div
							class="flex items-center border-b pb-1 font-medium text-ink-gray-9"
						>
							<span class="flex-1">
								{{ __('Courses') }}
							</span>
							<span>
								{{ __('Progress / Grade') }}
							</span>
						</div>
						<div
							v-for="course in Object.keys(student.courses)"
							:key="course"
							class="space-y-2 py-2 border-b last:border-0"
						>
							<div class="flex items-center text-ink-gray-7 font-medium">
								<span class="flex-1">
									{{ course }}
								</span>
								<span v-if="student.course_grades?.[course]?.enable_grading_policy" class="font-semibold text-ink-green-3">
									{{ student.course_grades[course].final_percentage }}% ({{ student.course_grades[course].final_grade }})
								</span>
								<span v-else>
									{{ Math.floor(student.courses[course]) }}% {{ __('complete') }}
								</span>
							</div>

							<!-- Display category breakdown if grading policy is enabled -->
							<div
								v-if="student.course_grades?.[course]?.enable_grading_policy"
								class="pl-4 border-l-2 border-outline-gray-2 space-y-1 mt-1 text-xs text-ink-gray-5"
							>
								<div
									v-for="cat in student.course_grades[course].categories"
									:key="cat.category_name"
									class="flex justify-between"
								>
									<span>
										{{ cat.category_name }} ({{ cat.weight }}%)
										<span v-if="cat.number_of_assessments" class="text-ink-gray-4">
											({{ cat.items?.length || 0 }} / {{ cat.number_of_assessments }})
										</span>
									</span>
									<span class="font-medium">
										{{ cat.average }}%
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Heatmap -->
				<StudentHeatmap :member="student.email" :days="120" />
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Avatar, Badge, Dialog } from 'frappe-ui'
import StudentHeatmap from '@/components/StudentHeatmap.vue'

const show = defineModel()
const props = defineProps({
	student: {
		type: Object,
		default: null,
	},
})

const isAssignment = (value) => {
	return isNaN(value)
}

const getStatusTheme = (status) => {
	if (status === 'Pass') {
		return 'green'
	} else if (status == 'Not Graded') {
		return 'orange'
	} else {
		return 'red'
	}
}
</script>
