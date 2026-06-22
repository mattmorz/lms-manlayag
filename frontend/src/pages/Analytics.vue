<template>
	<div class="min-h-screen bg-surface-gray-1">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>

		<!-- Role & Selection Selector Bar -->
		<div class="bg-surface-white border-b px-4 py-3 sm:px-6 flex flex-wrap items-center justify-between gap-3 shadow-xs">
			<!-- Tab Switcher for Instructors / Admins -->
			<div v-if="isAdminOrStaff" class="flex space-x-1 bg-surface-gray-2 p-1 rounded-lg">
				<button
					v-for="tab in availableTabs"
					:key="tab.value"
					@click="currentTab = tab.value"
					class="px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200"
					:class="currentTab === tab.value ? 'bg-surface-white text-indigo-600 shadow-sm' : 'text-ink-gray-7 hover:text-ink-gray-9'"
				>
					{{ __(tab.label) }}
				</button>
			</div>
			<div v-else class="text-sm font-semibold text-ink-gray-7">
				{{ __('My Learning Insights') }}
			</div>

			<!-- Dynamic Parameter Dropdown depending on currentTab -->
			<div class="flex items-center space-x-2">
				<!-- Student Course Selector -->
				<div v-if="currentTab === 'Student' && studentDashboard.data?.courses?.length" class="flex items-center space-x-2">
					<label class="text-xs text-ink-gray-5 font-medium">{{ __('Select Course:') }}</label>
					<select
						v-model="selectedStudentCourse"
						class="text-xs bg-surface-white border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					>
						<option
							v-for="c in studentDashboard.data.courses"
							:key="c.course"
							:value="c.course"
						>
							{{ c.title }}
						</option>
					</select>
				</div>

				<!-- Instructor Course Selector -->
				<div v-if="currentTab === 'Instructor' && instructorCourses.data?.length" class="flex items-center space-x-2">
					<label class="text-xs text-ink-gray-5 font-medium">{{ __('Course:') }}</label>
					<select
						v-model="selectedInstructorCourse"
						class="text-xs bg-surface-white border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					>
						<option
							v-for="c in instructorCourses.data"
							:key="c.name"
							:value="c.name"
						>
							{{ c.title }}
						</option>
					</select>
				</div>

				<!-- Batch Selector -->
				<div v-if="currentTab === 'Batch' && batchesList.data?.length" class="flex items-center space-x-2">
					<label class="text-xs text-ink-gray-5 font-medium">{{ __('Batch:') }}</label>
					<select
						v-model="selectedBatchName"
						class="text-xs bg-surface-white border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					>
						<option
							v-for="b in batchesList.data"
							:key="b.name"
							:value="b.name"
						>
							{{ b.title }}
						</option>
					</select>
				</div>

				<!-- Department Selector -->
				<div v-if="currentTab === 'Department' && categoriesList.data?.length" class="flex items-center space-x-2">
					<label class="text-xs text-ink-gray-5 font-medium">{{ __('Department:') }}</label>
					<select
						v-model="selectedDepartment"
						class="text-xs bg-surface-white border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					>
						<option
							v-for="cat in categoriesList.data"
							:key="cat.name"
							:value="cat.name"
						>
							{{ cat.name }}
						</option>
					</select>
				</div>
			</div>
		</div>

		<!-- Dashboard Body -->
		<div class="max-w-7xl mx-auto p-4 sm:p-6 space-y-6">
			<!-- 1. STUDENT DASHBOARD -->
			<div v-if="currentTab === 'Student'" class="space-y-6">
				<!-- KPI Cards -->
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="bg-surface-white border rounded-md p-5 flex items-center justify-between shadow-xs">
						<div>
							<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Learning Streak') }}</div>
							<div class="text-2xl font-extrabold text-indigo-600 flex items-center">
								{{ studentDashboard.data?.streak || 0 }} {{ __('days') }}
								<Flame class="w-5 h-5 text-orange-500 ml-1.5 fill-orange-500" />
							</div>
						</div>
						<div class="bg-indigo-50 p-2.5 rounded text-indigo-600">
							<Activity class="w-5 h-5 stroke-2" />
						</div>
					</div>

					<div class="bg-surface-white border rounded-md p-5 flex items-center justify-between shadow-xs">
						<div>
							<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Time Spent Learning') }}</div>
							<div class="text-2xl font-extrabold text-indigo-600">
								{{ formatDuration(studentDashboard.data?.total_time_spent) }}
							</div>
						</div>
						<div class="bg-indigo-50 p-2.5 rounded text-indigo-600">
							<Clock class="w-5 h-5 stroke-2" />
						</div>
					</div>

					<div class="bg-surface-white border rounded-md p-5 flex items-center justify-between shadow-xs">
						<div>
							<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Completed Courses') }}</div>
							<div class="text-2xl font-extrabold text-indigo-600">
								{{ studentDashboard.data?.completed_courses_count || 0 }}
							</div>
						</div>
						<div class="bg-indigo-50 p-2.5 rounded text-indigo-600">
							<CheckCircle2 class="w-5 h-5 stroke-2" />
						</div>
					</div>
				</div>

				<!-- Single Course Details if selected -->
				<div v-if="activeCourseData" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Left Details (Grades, Progress, Strengths, Recommendations) -->
					<div class="lg:col-span-2 space-y-6">
						<!-- Course Stats Overview -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs grid grid-cols-1 sm:grid-cols-3 gap-4">
							<div class="text-center sm:text-left border-r sm:border-r border-gray-100 last:border-0 pr-4">
								<div class="text-xs text-ink-gray-5 mb-1">{{ __('Course Progress') }}</div>
								<div class="text-xl font-bold text-ink-gray-8">{{ activeCourseData.progress }}%</div>
								<div class="w-full bg-gray-100 rounded-full h-1.5 mt-2 overflow-hidden">
									<div class="bg-green-500 h-1.5 rounded-full" :style="{ width: activeCourseData.progress + '%' }"></div>
								</div>
							</div>
							<div class="text-center sm:text-left border-r sm:border-r border-gray-100 last:border-0 px-4">
								<div class="text-xs text-ink-gray-5 mb-1">{{ __('Current Score') }}</div>
								<div class="text-xl font-bold text-ink-gray-8">{{ activeCourseData.current_grade }}%</div>
								<div class="text-xs text-indigo-600 mt-1.5 font-medium">{{ __('Grade Label: ') }} {{ activeCourseData.grade_label }}</div>
							</div>
							<div class="text-center sm:text-left last:border-0 pl-4">
								<div class="text-xs text-ink-gray-5 mb-1">{{ __('Exercise Completions') }}</div>
								<div class="text-xl font-bold text-ink-gray-8 text-green-600">{{ activeCourseData.passed_exercises || 0 }} <span class="text-xs text-ink-gray-4">{{ __('passed') }}</span></div>
								<div class="text-xs text-red-500 mt-1">{{ activeCourseData.failed_exercises || 0 }} {{ __('failed attempts') }}</div>
							</div>
						</div>

						<!-- Line Chart: Quiz Performance Trend -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Quiz Performance Trend') }}</h3>
							<div v-if="activeCourseData.quiz_trend?.length">
								<apexchart
									type="line"
									height="280"
									:options="getQuizTrendOptions(activeCourseData.quiz_trend)"
									:series="getQuizTrendSeries(activeCourseData.quiz_trend)"
								/>
							</div>
							<div v-else class="text-center py-10 text-xs text-ink-gray-4">
								{{ __('No quiz submissions recorded yet.') }}
							</div>
						</div>

						<!-- Recommendations & Feedback -->
						<div class="bg-indigo-50/55 border border-indigo-100 rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-indigo-900 mb-3 flex items-center">
								<Zap class="w-4 h-4 mr-1.5 text-indigo-600 fill-indigo-600" />
								{{ __('Personalized Action Recommendations') }}
							</h3>
							<div v-if="visibleRecommendations.length" class="space-y-3">
								<div
									v-for="(rec, idx) in visibleRecommendations"
									:key="idx"
									class="bg-surface-white border border-indigo-100/50 p-4 rounded-lg flex items-start space-x-3 shadow-xxs"
								>
									<div class="bg-indigo-100 text-indigo-700 p-1.5 rounded">
										<BookOpen v-if="rec.type === 'review_lesson'" class="w-4 h-4" />
										<Award v-else class="w-4 h-4" />
									</div>
									<div class="flex-1">
										<h4 class="text-xs font-bold text-ink-gray-9 mb-0.5">
											{{ rec.type === 'review_lesson' ? __('Review Lesson:') : __('Retake Assessment:') }}
											{{ rec.title }}
										</h4>
										<p class="text-xs text-ink-gray-6">{{ rec.reason }}</p>
									</div>
								</div>
								<div v-if="activeCourseData.recommendations?.length > visibleRecLimit" class="flex justify-center mt-3">
									<Button variant="outline" @click="visibleRecLimit += 3">
										{{ __('Load More Recommendations') }}
									</Button>
								</div>
							</div>
							<div v-else class="text-xs text-indigo-700 italic">
								{{ __('Excellent progress! No immediate reviews recommended. Keep studying!') }}
							</div>
						</div>
					</div>

					<!-- Right Sidebar (Risk score, Predictions, Missing activities) -->
					<div class="space-y-6">
						<!-- Risk Score Card -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Academic Risk Assessment') }}</h3>
							<div class="flex items-center justify-between mb-4">
								<div class="text-xs text-ink-gray-5">{{ __('Overall Risk Level') }}</div>
								<span
									class="px-2.5 py-1 text-xs font-extrabold rounded-md uppercase"
									:class="{
										'bg-red-100 text-red-700': activeCourseData.at_risk?.risk_level === 'High Risk',
										'bg-orange-100 text-orange-700': activeCourseData.at_risk?.risk_level === 'Medium Risk',
										'bg-green-100 text-green-700': activeCourseData.at_risk?.risk_level === 'Low Risk',
									}"
								>
									{{ __(activeCourseData.at_risk?.risk_level || 'Low Risk') }}
								</span>
							</div>

							<!-- Circular Indicator -->
							<div class="flex justify-center mb-4">
								<div class="relative w-28 h-28 flex items-center justify-center">
									<svg class="absolute w-full h-full transform -rotate-90">
										<circle cx="56" cy="56" r="48" stroke="#f3f4f6" stroke-width="8" fill="transparent" />
										<circle
											cx="56"
											cy="56"
											r="48"
											:stroke="getRiskColor(activeCourseData.at_risk?.risk_score)"
											stroke-width="8"
											fill="transparent"
											:stroke-dasharray="301.6"
											:stroke-dashoffset="301.6 - (301.6 * (activeCourseData.at_risk?.risk_score || 0)) / 100"
										/>
									</svg>
									<span class="text-2xl font-extrabold text-ink-gray-9">{{ activeCourseData.at_risk?.risk_score || 0 }}%</span>
								</div>
							</div>

							<!-- Risk Reasons -->
							<div v-if="activeCourseData.at_risk?.reasons?.length" class="space-y-2 mt-2">
								<div
									v-for="(reason, idx) in activeCourseData.at_risk.reasons"
									:key="idx"
									class="text-xs text-red-600 bg-red-50/50 p-2 rounded border border-red-100/30 flex items-start space-x-1.5"
								>
									<AlertTriangle class="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-red-500" />
									<span>{{ reason }}</span>
								</div>
							</div>
							<div v-else class="text-center py-2 text-xs text-green-600 font-medium">
								{{ __('Student is fully active and meeting all academic targets.') }}
							</div>
						</div>

						<!-- Explainable Predictions -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs space-y-4">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-1">{{ __('Foundational Predictions') }}</h3>
							<p class="text-xs text-ink-gray-5 leading-normal">{{ __('Explainable progress indices computed from engagement statistics.') }}</p>

							<!-- Completion Probability -->
							<div class="border-b pb-3 last:border-b-0 last:pb-0">
								<div class="flex items-center justify-between text-xs mb-1">
									<span class="font-semibold text-ink-gray-7">{{ __('Completion Probability') }}</span>
									<span class="font-extrabold text-indigo-600">{{ activeCourseData.predictions?.completion_probability }}%</span>
								</div>
								<div class="w-full bg-gray-100 rounded-full h-1.5 mb-2">
									<div class="bg-indigo-600 h-1.5 rounded-full" :style="{ width: activeCourseData.predictions?.completion_probability + '%' }"></div>
								</div>
								<div class="space-y-1">
									<p
										v-for="(f, i) in activeCourseData.predictions?.factors_completion"
										:key="i"
										class="text-xs text-ink-gray-5"
									>
										• {{ f }}
									</p>
								</div>
							</div>

							<!-- Pass Probability -->
							<div class="border-b pb-3 last:border-b-0 last:pb-0">
								<div class="flex items-center justify-between text-xs mb-1">
									<span class="font-semibold text-ink-gray-7">{{ __('Pass Probability') }}</span>
									<span class="font-extrabold text-green-600">{{ activeCourseData.predictions?.pass_probability }}%</span>
								</div>
								<div class="w-full bg-gray-100 rounded-full h-1.5 mb-2">
									<div class="bg-green-600 h-1.5 rounded-full" :style="{ width: activeCourseData.predictions?.pass_probability + '%' }"></div>
								</div>
								<div class="space-y-1">
									<p
										v-for="(f, i) in activeCourseData.predictions?.factors_pass"
										:key="i"
										class="text-xs text-ink-gray-5"
									>
										• {{ f }}
									</p>
								</div>
							</div>

							<!-- Dropout Probability -->
							<div class="last:border-b-0 last:pb-0">
								<div class="flex items-center justify-between text-xs mb-1">
									<span class="font-semibold text-ink-gray-7">{{ __('Dropout Risk Indicator') }}</span>
									<span class="font-extrabold text-red-600">{{ activeCourseData.predictions?.dropout_probability }}%</span>
								</div>
								<div class="w-full bg-gray-100 rounded-full h-1.5 mb-2">
									<div class="bg-red-600 h-1.5 rounded-full" :style="{ width: activeCourseData.predictions?.dropout_probability + '%' }"></div>
								</div>
								<div class="space-y-1">
									<p
										v-for="(f, i) in activeCourseData.predictions?.factors_dropout"
										:key="i"
										class="text-xs text-ink-gray-5"
									>
										• {{ f }}
									</p>
								</div>
							</div>
						</div>

						<!-- Missing Activities -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Pending / Missing Activities') }}</h3>
							<div v-if="visibleMissingActivities.length" class="space-y-2">
								<div
									v-for="(act, idx) in visibleMissingActivities"
									:key="idx"
									class="border rounded p-2.5 flex items-start justify-between bg-surface-gray-1 shadow-xxs"
								>
									<div>
										<div class="text-xs font-bold text-ink-gray-8 mb-0.5 leading-snug">{{ act.title }}</div>
										<span class="text-xs text-ink-gray-5 font-semibold uppercase">{{ act.type }}</span>
									</div>
									<span v-if="act.due" class="text-xs text-red-500 font-medium bg-red-50 px-1.5 py-0.5 rounded border border-red-100/50">
										{{ __('Due: ') }} {{ act.due }}
									</span>
								</div>
								<div v-if="activeCourseData.missing_activities?.length > visibleMissingLimit" class="flex justify-center mt-3">
									<Button variant="outline" @click="visibleMissingLimit += 5">
										{{ __('Load More') }}
									</Button>
								</div>
							</div>
							<div v-else class="text-center py-6 text-xs text-green-600 font-medium bg-green-50/20 border border-green-100/50 rounded-md">
								{{ __('All activities completed! Nice job!') }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- 2. INSTRUCTOR DASHBOARD -->
			<div v-if="currentTab === 'Instructor'" class="space-y-6">
				<!-- KPIs Grid -->
				<div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Total Enrollments') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ instructorDashboard.data?.enrollment_count || 0 }}</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Active Students (7d)') }}</div>
						<div class="text-2xl font-extrabold text-green-600">{{ instructorDashboard.data?.active_students || 0 }}</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1{{ __('Average Completion') }}">{{ __('Average Completion') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ instructorDashboard.data?.completion_rate || 0 }}%</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Average Grade') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ instructorDashboard.data?.average_grade || 0 }}%</div>
					</div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Struggling & At-Risk Students list -->
					<div class="lg:col-span-2 space-y-6">
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-4 flex items-center text-red-700">
								<AlertTriangle class="w-4 h-4 mr-1.5" />
								{{ __('Struggling & At-Risk Students') }}
							</h3>
							<div class="overflow-x-auto">
								<table v-if="visibleAtRiskStudents.length" class="w-full text-left border-collapse">
									<thead>
										<tr class="border-b text-xs text-ink-gray-5">
											<th class="py-2.5">{{ __('Student') }}</th>
											<th class="py-2.5">{{ __('Progress') }}</th>
											<th class="py-2.5 text-center">{{ __('Risk Score') }}</th>
											<th class="py-2.5">{{ __('Trigger Reasons') }}</th>
										</tr>
									</thead>
									<tbody class="divide-y text-xs">
										<tr v-for="s in visibleAtRiskStudents" :key="s.username">
											<td class="py-3 font-semibold text-ink-gray-8">{{ s.name }}</td>
											<td class="py-3">{{ s.progress }}%</td>
											<td class="py-3 text-center">
												<span
													class="px-2 py-0.5 rounded text-xs font-extrabold"
													:class="s.risk_level === 'High Risk' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'"
												>
													{{ s.risk_score }}%
												</span>
											</td>
											<td class="py-3 text-ink-gray-6 leading-relaxed">
												<ul class="list-disc pl-4 space-y-0.5 text-xs">
													<li v-for="(reason, i) in s.reasons" :key="i">{{ reason }}</li>
												</ul>
											</td>
										</tr>
									</tbody>
								</table>
								<div v-else class="text-center py-10 text-xs text-ink-gray-4 font-medium">
									{{ __('Hooray! No at-risk students flagged in this course.') }}
								</div>
								<div v-if="instructorDashboard.data?.at_risk_students?.length > visibleAtRiskLimit" class="flex justify-center mt-4">
									<Button variant="outline" @click="visibleAtRiskLimit += 5">
										{{ __('Load More') }}
									</Button>
								</div>
							</div>
						</div>

						<!-- Difficult Modules & Question Analytics -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs space-y-6">
							<div>
								<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Problematic / Ambiguous Questions') }}</h3>
								<div class="overflow-x-auto">
									<table v-if="visibleQuestions.length" class="w-full text-left border-collapse">
										<thead>
											<tr class="border-b text-xs text-ink-gray-5">
												<th class="py-2.5">{{ __('Question Name') }}</th>
												<th class="py-2.5">{{ __('Question Text') }}</th>
												<th class="py-2.5 text-center">{{ __('Pass Rate') }}</th>
												<th class="py-2.5">{{ __('Insight / Issue') }}</th>
											</tr>
										</thead>
										<tbody class="divide-y text-xs">
											<tr v-for="q in visibleQuestions" :key="q.question_name">
												<td class="py-3 font-semibold text-ink-gray-8">{{ q.question_name }}</td>
												<td class="py-3 max-w-[200px] truncate text-ink-gray-6" v-html="q.question_text"></td>
												<td class="py-3 text-center font-bold text-red-600">{{ q.correct_rate }}%</td>
												<td class="py-3 text-xs text-ink-gray-5">{{ q.reason }}</td>
											</tr>
										</tbody>
									</table>
									<div v-else class="text-center py-8 text-xs text-ink-gray-4">
										{{ __('No problematic questions identified.') }}
									</div>
									<div v-if="instructorDashboard.data?.high_failure_questions?.length > visibleQuestionsLimit" class="flex justify-center mt-4">
										<Button variant="outline" @click="visibleQuestionsLimit += 5">
											{{ __('Load More') }}
										</Button>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Right instructor stats column -->
					<div class="space-y-6">
						<!-- Difficult Lessons & Quizzes Dropoffs -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs space-y-6">
							<div>
								<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Difficult Lessons (Drop-Off Points)') }}</h3>
								<div v-if="visibleLessons.length" class="space-y-2.5">
									<div
										v-for="l in visibleLessons"
										:key="l.lesson_name"
										class="border p-3 rounded-md bg-surface-gray-1 shadow-xxs"
									>
										<div class="text-xs font-bold text-ink-gray-8 mb-1 leading-snug">{{ l.title }}</div>
										<p class="text-xs text-red-600 mb-2 leading-relaxed">{{ l.reason }}</p>
										<div class="flex items-center justify-between text-xs text-ink-gray-5 font-semibold">
											<span>{{ __('Views: ') }}{{ l.views }}</span>
											<span>{{ __('Avg Duration: ') }}{{ Math.round(l.avg_time_spent / 60) }} {{ __('mins') }}</span>
										</div>
									</div>
									<div v-if="instructorDashboard.data?.difficult_lessons?.length > visibleLessonsLimit" class="flex justify-center mt-3">
										<Button variant="outline" @click="visibleLessonsLimit += 5">
											{{ __('Load More') }}
										</Button>
									</div>
								</div>
								<div v-else class="text-center py-6 text-xs text-ink-gray-4">
									{{ __('All lessons have steady completion rates.') }}
								</div>
							</div>

							<hr class="border-gray-100" />

							<div>
								<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Difficult Quizzes') }}</h3>
								<div v-if="visibleQuizzes.length" class="space-y-2.5">
									<div
										v-for="q in visibleQuizzes"
										:key="q.quiz"
										class="border p-3 rounded-md bg-surface-gray-1 shadow-xxs"
									>
										<div class="text-xs font-bold text-ink-gray-8 mb-1 leading-snug">{{ q.quiz }}</div>
										<p class="text-xs text-red-600 mb-2 leading-relaxed">{{ q.reason }}</p>
										<div class="flex items-center justify-between text-xs text-ink-gray-5 font-semibold">
											<span>{{ __('Attempts: ') }}{{ q.attempts }}</span>
											<span>{{ __('Average Score: ') }}{{ q.avg_score }}%</span>
										</div>
									</div>
									<div v-if="instructorDashboard.data?.difficult_quizzes?.length > visibleQuizzesLimit" class="flex justify-center mt-3">
										<Button variant="outline" @click="visibleQuizzesLimit += 5">
											{{ __('Load More') }}
										</Button>
									</div>
								</div>
								<div v-else class="text-center py-6 text-xs text-ink-gray-4">
									{{ __('All quizzes meeting performance targets.') }}
								</div>
							</div>
						</div>

						<!-- Chart: Quizzes Averages comparison -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Assessment Averages') }}</h3>
							<div v-if="instructorDashboard.data?.quizzes_stats?.length">
								<apexchart
									type="bar"
									height="240"
									:options="getInstructorChartOptions(instructorDashboard.data.quizzes_stats)"
									:series="getInstructorChartSeries(instructorDashboard.data.quizzes_stats)"
								/>
							</div>
							<div v-else class="text-center py-8 text-xs text-ink-gray-4">
								{{ __('No assessment data logged.') }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- 3. BATCH DASHBOARD -->
			<div v-if="currentTab === 'Batch'" class="space-y-6">
				<!-- KPIs -->
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Batch Completion Rate') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ batchDashboard.data?.completion_rate || 0 }}%</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Batch Average Grade') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ batchDashboard.data?.average_grade || 0 }}%</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs flex items-center justify-between">
						<div>
							<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('At-Risk Learners in Batch') }}</div>
							<div class="text-2xl font-extrabold text-red-600">{{ batchDashboard.data?.at_risk_learners?.length || 0 }}</div>
						</div>
						<span class="bg-red-50 text-red-600 p-2 rounded">
							<AlertTriangle class="w-5 h-5" />
						</span>
					</div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Progress distribution and batch comparison -->
					<div class="lg:col-span-2 space-y-6">
						<!-- Distribution bar chart -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Progress Distribution (Student Counts)') }}</h3>
							<div v-if="batchDashboard.data?.progress_distribution">
								<apexchart
									type="bar"
									height="280"
									:options="getDistributionChartOptions(batchDashboard.data.progress_distribution)"
									:series="getDistributionChartSeries(batchDashboard.data.progress_distribution)"
								/>
							</div>
						</div>

						<!-- Comparisons with other semesters / batches -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Batch Comparisons (Progress vs Other Batches)') }}</h3>
							<div v-if="batchDashboard.data?.comparisons?.length" class="space-y-4">
								<div
									v-for="(comp, i) in batchDashboard.data.comparisons"
									:key="i"
									class="border rounded-md p-4 bg-surface-gray-1 shadow-xxs"
								>
									<h4 class="text-xs font-bold text-ink-gray-8 mb-3">{{ comp.course_title }}</h4>
									<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center sm:text-left">
										<!-- Current -->
										<div class="border-r border-gray-200/50 last:border-0 pr-4">
											<div class="text-xs text-indigo-600 font-bold uppercase mb-0.5">{{ comp.current_batch_title }}</div>
											<div class="text-base font-bold text-ink-gray-8">{{ comp.current_batch_progress }}%</div>
										</div>
										<!-- Others -->
										<div
											v-for="(ob, idx) in comp.comparison_batches"
											:key="idx"
											class="border-r border-gray-200/50 last:border-0 px-4"
										>
											<div class="text-xs text-ink-gray-5 font-bold uppercase mb-0.5">{{ ob.batch_title }}</div>
											<div class="text-base font-bold text-ink-gray-7">{{ ob.average_progress }}%</div>
										</div>
									</div>
								</div>
							</div>
							<div v-else class="text-center py-8 text-xs text-ink-gray-4">
								{{ __('No comparative batch structures available.') }}
							</div>
						</div>
					</div>

					<!-- Top performers & At-risk list -->
					<div class="space-y-6">
						<!-- Top Performers list -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-indigo-900 mb-3 flex items-center">
								<Award class="w-4 h-4 mr-1.5 text-indigo-600 fill-indigo-600" />
								{{ __('Top Performers') }}
							</h3>
							<div v-if="visiblePerformers.length" class="space-y-2">
								<div
									v-for="p in visiblePerformers"
									:key="p.username"
									class="border rounded p-2.5 flex items-center justify-between bg-surface-gray-1 shadow-xxs"
								>
									<div>
										<div class="text-xs font-bold text-ink-gray-8 leading-snug">{{ p.name }}</div>
										<span class="text-xs text-ink-gray-5">{{ __('Progress: ') }}{{ p.progress }}%</span>
									</div>
									<span class="text-xs font-extrabold text-indigo-600">
										{{ p.grade }}%
									</span>
								</div>
								<div v-if="batchDashboard.data?.top_performers?.length > visiblePerformersLimit" class="flex justify-center mt-3">
									<Button variant="outline" @click="visiblePerformersLimit += 5">
										{{ __('Load More') }}
									</Button>
								</div>
							</div>
							<div v-else class="text-center py-6 text-xs text-ink-gray-4">
								{{ __('No performers calculated.') }}
							</div>
						</div>

						<!-- Batch At-Risk Learners list -->
						<div class="bg-surface-white border rounded-md p-5 shadow-xs">
							<h3 class="text-sm font-bold text-red-900 mb-3 flex items-center">
								<AlertTriangle class="w-4 h-4 mr-1.5 text-red-500" />
								{{ __('Batch At-Risk Learners') }}
							</h3>
							<div v-if="visibleBatchRisk.length" class="space-y-3">
								<div
									v-for="s in visibleBatchRisk"
									:key="s.username"
									class="border rounded-md p-3 bg-red-50/30 border-red-100 flex flex-col space-y-2 shadow-xxs"
								>
									<div class="flex items-center justify-between">
										<div class="text-xs font-bold text-ink-gray-8">{{ s.name }}</div>
										<span class="px-2 py-0.5 rounded text-xs font-extrabold bg-red-100 text-red-700">
											{{ s.risk_score }}%
										</span>
									</div>
									<ul class="list-disc pl-4 space-y-0.5 text-xs text-ink-gray-6">
										<li v-for="(r, i) in s.reasons" :key="i">{{ r }}</li>
									</ul>
								</div>
								<div v-if="batchDashboard.data?.at_risk_learners?.length > visibleBatchRiskLimit" class="flex justify-center mt-3">
									<Button variant="outline" @click="visibleBatchRiskLimit += 5">
										{{ __('Load More') }}
									</Button>
								</div>
							</div>
							<div v-else class="text-center py-6 text-xs text-green-600 font-medium">
								{{ __('Zero risk flags in this batch.') }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- 4. DEPARTMENT DASHBOARD -->
			<div v-if="currentTab === 'Department'" class="space-y-6">
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Course completion rates in department -->
					<div class="lg:col-span-2 bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Department Course Completion Rates') }}</h3>
						<div v-if="visibleDepartmentCompletions.length" class="overflow-x-auto">
							<table class="w-full text-left border-collapse">
								<thead>
									<tr class="border-b text-xs text-ink-gray-5">
										<th class="py-2.5">{{ __('Course') }}</th>
										<th class="py-2.5">{{ __('Enrollments') }}</th>
										<th class="py-2.5">{{ __('Completion Rate') }}</th>
									</tr>
								</thead>
								<tbody class="divide-y text-xs">
									<tr v-for="c in visibleDepartmentCompletions" :key="c.course">
										<td class="py-3 font-semibold text-ink-gray-8">{{ c.course }}</td>
										<td class="py-3 text-ink-gray-6">{{ c.enrollments }}</td>
										<td class="py-3 font-semibold text-indigo-600">{{ c.completion_rate }}%</td>
									</tr>
								</tbody>
							</table>
							<div v-if="departmentDashboard.data?.course_completion_rates?.length > visibleDepCompletionsLimit" class="flex justify-center mt-4">
								<Button variant="outline" @click="visibleDepCompletionsLimit += 5">
									{{ __('Load More') }}
								</Button>
							</div>
						</div>
					</div>

					<!-- Weekly active users line chart -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Student Engagement Trend') }}</h3>
						<div v-if="departmentDashboard.data?.student_engagement_trends?.length">
							<apexchart
								type="line"
								height="260"
								:options="getDepartmentTrendOptions(departmentDashboard.data.student_engagement_trends)"
								:series="getDepartmentTrendSeries(departmentDashboard.data.student_engagement_trends)"
							/>
						</div>
					</div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Course Average Performance -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Average Student Performance (Grades)') }}</h3>
						<div v-if="departmentDashboard.data?.average_performance?.length">
							<apexchart
								type="bar"
								height="280"
								:options="getDepartmentPerformanceOptions(departmentDashboard.data.average_performance)"
								:series="getDepartmentPerformanceSeries(departmentDashboard.data.average_performance)"
							/>
						</div>
					</div>

					<!-- Faculty Course Performance -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Faculty Course Workloads') }}</h3>
						<div v-if="visibleFaculty.length" class="overflow-x-auto">
							<table class="w-full text-left border-collapse">
								<thead>
									<tr class="border-b text-xs text-ink-gray-5">
										<th class="py-2.5">{{ __('Faculty Member') }}</th>
										<th class="py-2.5 text-center">{{ __('Courses Managed') }}</th>
										<th class="py-2.5 text-center">{{ __('Total Enrolled Students') }}</th>
									</tr>
								</thead>
								<tbody class="divide-y text-xs">
									<tr v-for="f in visibleFaculty" :key="f.instructor">
										<td class="py-3 font-semibold text-ink-gray-8">{{ f.instructor }}</td>
										<td class="py-3 text-center text-ink-gray-6">{{ f.courses_count }}</td>
										<td class="py-3 text-center font-semibold text-indigo-600">{{ f.enrollments }}</td>
									</tr>
								</tbody>
							</table>
							<div v-if="departmentDashboard.data?.faculty_performance?.length > visibleFacultyLimit" class="flex justify-center mt-4">
								<Button variant="outline" @click="visibleFacultyLimit += 5">
									{{ __('Load More') }}
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- 5. ADMINISTRATIVE DASHBOARD -->
			<div v-if="currentTab === 'Administrative'" class="space-y-6">
				<!-- KPI Cards -->
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Total Enrollments (Platform)') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ adminDashboard.data?.total_enrollments || 0 }}</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Active Learners (30d)') }}</div>
						<div class="text-2xl font-extrabold text-green-600">{{ adminDashboard.data?.active_learners || 0 }}</div>
					</div>
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<div class="text-xs text-ink-gray-5 font-medium mb-1">{{ __('Overall Completion Rate') }}</div>
						<div class="text-2xl font-extrabold text-indigo-600">{{ adminDashboard.data?.overall_completion_rate || 0 }}%</div>
					</div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Signup activity trend (Line Chart) -->
					<div class="lg:col-span-2 bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-4">{{ __('Weekly Registration Trends (New Users)') }}</h3>
						<div v-if="adminDashboard.data?.signup_trends?.length">
							<apexchart
								type="line"
								height="280"
								:options="getAdminTrendOptions(adminDashboard.data.signup_trends)"
								:series="getAdminTrendSeries(adminDashboard.data.signup_trends)"
							/>
						</div>
					</div>

					<!-- Popular courses list -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-ink-gray-9 mb-3">{{ __('Most Popular Courses') }}</h3>
						<div v-if="adminDashboard.data?.popular_courses?.length" class="space-y-3">
							<div
								v-for="c in adminDashboard.data.popular_courses"
								:key="c.course"
								class="border rounded-md p-3 flex items-center justify-between bg-surface-gray-1 shadow-xxs"
							>
								<div class="text-xs font-bold text-ink-gray-8 leading-snug">{{ c.course }}</div>
								<span class="text-xs font-semibold text-indigo-600">
									{{ c.enrollments }} {{ __('enrolled') }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<!-- Lowest Completion Courses -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-red-900 mb-3 flex items-center">
							<AlertTriangle class="w-4 h-4 mr-1.5 text-red-500" />
							{{ __('Lowest Completion Courses') }}
						</h3>
						<div v-if="adminDashboard.data?.lowest_completion_courses?.length" class="space-y-3">
							<div
								v-for="c in adminDashboard.data.lowest_completion_courses"
								:key="c.course"
								class="border rounded-md p-3 flex items-center justify-between bg-red-50/10 border-red-100 shadow-xxs"
							>
								<div class="text-xs font-bold text-ink-gray-8 leading-snug">{{ c.course }}</div>
								<span class="text-xs font-bold text-red-600">
									{{ c.completion_rate }}% {{ __('completion') }}
								</span>
							</div>
						</div>
					</div>

					<!-- Highest Performing Courses -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-green-900 mb-3 flex items-center">
							<CheckCircle2 class="w-4 h-4 mr-1.5 text-green-500" />
							{{ __('Highest Performing Courses (Grades)') }}
						</h3>
						<div v-if="adminDashboard.data?.highest_performing_courses?.length" class="space-y-3">
							<div
								v-for="c in adminDashboard.data.highest_performing_courses"
								:key="c.course"
								class="border rounded-md p-3 flex items-center justify-between bg-green-50/10 border-green-100 shadow-xxs"
							>
								<div class="text-xs font-bold text-ink-gray-8 leading-snug">{{ c.course }}</div>
								<span class="text-xs font-bold text-green-600">
									{{ c.average_grade }}% {{ __('avg grade') }}
								</span>
							</div>
						</div>
					</div>

					<!-- Highest Risk Courses -->
					<div class="bg-surface-white border rounded-md p-5 shadow-xs">
						<h3 class="text-sm font-bold text-red-900 mb-3 flex items-center">
							<AlertTriangle class="w-4 h-4 mr-1.5 text-red-500" />
							{{ __('Highest Risk Courses') }}
						</h3>
						<div v-if="adminDashboard.data?.highest_risk_courses?.length" class="space-y-3">
							<div
								v-for="c in adminDashboard.data.highest_risk_courses"
								:key="c.course"
								class="border rounded-md p-3 flex items-center justify-between bg-red-50/20 border-red-100 shadow-xxs"
							>
								<div class="text-xs font-bold text-ink-gray-8 leading-snug">{{ c.course }}</div>
								<span class="text-xs font-bold text-red-600">
									{{ c.risk_percentage }}% {{ __('students at risk') }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { createResource, call, Breadcrumbs, Button, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'
import {
	TrendingUp,
	Activity,
	Clock,
	CheckCircle2,
	Flame,
	AlertTriangle,
	Zap,
	BookOpen,
	Award,
} from 'lucide-vue-next'
import apexchart from 'vue3-apexcharts'

// Fetch logged in user and roles
const { user, brand } = sessionStore()
const { userResource } = usersStore()

usePageMeta(() => {
	return {
		title: __('Analytics'),
		icon: brand.favicon,
	}
})

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Analytics'),
			route: {
				name: 'Analytics',
			},
		},
	]
})

const isAdminOrStaff = computed(() => {
	if (!userResource.data) return false
	return (
		userResource.data.is_instructor ||
		userResource.data.is_moderator ||
		userResource.data.is_evaluator ||
		userResource.data.is_system_manager
	)
})

// Tabs definition
const availableTabs = computed(() => {
	const tabs = []
	tabs.push({ label: 'Student Dashboard', value: 'Student' })
	
	if (userResource.data?.is_instructor || userResource.data?.is_moderator) {
		tabs.push({ label: 'Instructor View', value: 'Instructor' })
	}
	if (userResource.data?.is_instructor || userResource.data?.is_moderator || userResource.data?.is_evaluator) {
		tabs.push({ label: 'Batch Analytics', value: 'Batch' })
	}
	if (userResource.data?.is_moderator || userResource.data?.is_instructor) {
		tabs.push({ label: 'Department Trends', value: 'Department' })
	}
	if (userResource.data?.is_system_manager || userResource.data?.is_moderator) {
		tabs.push({ label: 'Administrative View', value: 'Administrative' })
	}
	return tabs
})

const currentTab = ref('Student')

// Selector values
const selectedStudentCourse = ref(null)
const selectedInstructorCourse = ref(null)
const selectedBatchName = ref(null)
const selectedDepartment = ref(null)

// ----------------------------------------------------
// Client-side pagination lists limits
// ----------------------------------------------------
const visibleRecLimit = ref(3)
const visibleMissingLimit = ref(5)
const visibleAtRiskLimit = ref(5)
const visibleQuestionsLimit = ref(5)
const visibleLessonsLimit = ref(5)
const visibleQuizzesLimit = ref(5)
const visiblePerformersLimit = ref(5)
const visibleBatchRiskLimit = ref(5)
const visibleDepCompletionsLimit = ref(5)
const visibleFacultyLimit = ref(5)

// Reset limits when tabs or course selection changes
const resetLimits = () => {
	visibleRecLimit.value = 3
	visibleMissingLimit.value = 5
	visibleAtRiskLimit.value = 5
	visibleQuestionsLimit.value = 5
	visibleLessonsLimit.value = 5
	visibleQuizzesLimit.value = 5
	visiblePerformersLimit.value = 5
	visibleBatchRiskLimit.value = 5
	visibleDepCompletionsLimit.value = 5
	visibleFacultyLimit.value = 5
}

watch(selectedStudentCourse, resetLimits)
watch(selectedInstructorCourse, resetLimits)
watch(selectedBatchName, resetLimits)
watch(selectedDepartment, resetLimits)
watch(currentTab, resetLimits)

// ----------------------------------------------------
// 1. Resources definitions
// ----------------------------------------------------

// Fetch dropdown inputs
const instructorCourses = createResource({
	url: 'frappe.client.get_list',
	makeParams() {
		return {
			doctype: 'LMS Course',
			filters: { published: 1 },
			fields: ['name', 'title'],
			limit_page_length: 100,
		}
	},
	onSuccess(data) {
		if (data?.length) {
			selectedInstructorCourse.value = data[0].name
		}
	},
})

const batchesList = createResource({
	url: 'frappe.client.get_list',
	makeParams() {
		return {
			doctype: 'LMS Batch',
			filters: { published: 1 },
			fields: ['name', 'title'],
			limit_page_length: 100,
		}
	},
	onSuccess(data) {
		if (data?.length) {
			selectedBatchName.value = data[0].name
		}
	},
})

const categoriesList = createResource({
	url: 'frappe.client.get_list',
	makeParams() {
		return {
			doctype: 'LMS Category',
			fields: ['name'],
			limit_page_length: 100,
		}
	},
	onSuccess(data) {
		if (data?.length) {
			selectedDepartment.value = data[0].name
		}
	},
})

// Master resource for analytics dashboards
const studentDashboard = createResource({
	url: 'lms.lms.api.get_analytics_dashboard',
	params: {
		dashboard_type: 'Student',
		reference_name: user,
	},
	auto: true,
	onSuccess(data) {
		if (data?.courses?.length) {
			selectedStudentCourse.value = data.courses[0].course
		}
	},
})

const instructorDashboard = createResource({
	url: 'lms.lms.api.get_analytics_dashboard',
	makeParams() {
		return {
			dashboard_type: 'Instructor',
			reference_name: selectedInstructorCourse.value,
		}
	},
})

const batchDashboard = createResource({
	url: 'lms.lms.api.get_analytics_dashboard',
	makeParams() {
		return {
			dashboard_type: 'Batch',
			reference_name: selectedBatchName.value,
		}
	},
})

const departmentDashboard = createResource({
	url: 'lms.lms.api.get_analytics_dashboard',
	makeParams() {
		return {
			dashboard_type: 'Department',
			reference_name: selectedDepartment.value,
		}
	},
})

const adminDashboard = createResource({
	url: 'lms.lms.api.get_analytics_dashboard',
	params: {
		dashboard_type: 'Administrative',
		reference_name: 'global',
	},
})

// Load active selectors data based on selection change
watch(selectedInstructorCourse, (newVal) => {
	if (newVal) instructorDashboard.reload()
})

watch(selectedBatchName, (newVal) => {
	if (newVal) batchDashboard.reload()
})

watch(selectedDepartment, (newVal) => {
	if (newVal) departmentDashboard.reload()
})

watch(currentTab, (newTab) => {
	if (newTab === 'Student') {
		studentDashboard.reload()
	} else if (newTab === 'Instructor') {
		instructorCourses.reload()
		if (selectedInstructorCourse.value) instructorDashboard.reload()
	} else if (newTab === 'Batch') {
		batchesList.reload()
		if (selectedBatchName.value) batchDashboard.reload()
	} else if (newTab === 'Department') {
		categoriesList.reload()
		if (selectedDepartment.value) departmentDashboard.reload()
	} else if (newTab === 'Administrative') {
		adminDashboard.reload()
	}
})

// Active Student course computed properties
const activeCourseData = computed(() => {
	if (!studentDashboard.data?.courses || !selectedStudentCourse.value) return null
	return studentDashboard.data.courses.find((c) => c.course === selectedStudentCourse.value)
})

// ----------------------------------------------------
// Paginated Visible Slices Computations
// ----------------------------------------------------
const visibleRecommendations = computed(() => {
	if (!activeCourseData.value?.recommendations) return []
	return activeCourseData.value.recommendations.slice(0, visibleRecLimit.value)
})

const visibleMissingActivities = computed(() => {
	if (!activeCourseData.value?.missing_activities) return []
	return activeCourseData.value.missing_activities.slice(0, visibleMissingLimit.value)
})

const visibleAtRiskStudents = computed(() => {
	if (!instructorDashboard.data?.at_risk_students) return []
	return instructorDashboard.data.at_risk_students.slice(0, visibleAtRiskLimit.value)
})

const visibleQuestions = computed(() => {
	if (!instructorDashboard.data?.high_failure_questions) return []
	return instructorDashboard.data.high_failure_questions.slice(0, visibleQuestionsLimit.value)
})

const visibleLessons = computed(() => {
	if (!instructorDashboard.data?.difficult_lessons) return []
	return instructorDashboard.data.difficult_lessons.slice(0, visibleLessonsLimit.value)
})

const visibleQuizzes = computed(() => {
	if (!instructorDashboard.data?.difficult_quizzes) return []
	return instructorDashboard.data.difficult_quizzes.slice(0, visibleQuizzesLimit.value)
})

const visiblePerformers = computed(() => {
	if (!batchDashboard.data?.top_performers) return []
	return batchDashboard.data.top_performers.slice(0, visiblePerformersLimit.value)
})

const visibleBatchRisk = computed(() => {
	if (!batchDashboard.data?.at_risk_learners) return []
	return batchDashboard.data.at_risk_learners.slice(0, visibleBatchRiskLimit.value)
})

const visibleDepartmentCompletions = computed(() => {
	if (!departmentDashboard.data?.course_completion_rates) return []
	return departmentDashboard.data.course_completion_rates.slice(0, visibleDepCompletionsLimit.value)
})

const visibleFaculty = computed(() => {
	if (!departmentDashboard.data?.faculty_performance) return []
	return departmentDashboard.data.faculty_performance.slice(0, visibleFacultyLimit.value)
})

onMounted(() => {
	if (isAdminOrStaff.value) {
		instructorCourses.reload()
		batchesList.reload()
		categoriesList.reload()
	}
})

// ----------------------------------------------------
// 2. Chart Layout Options Helper Calculations
// ----------------------------------------------------

const getRiskColor = (score) => {
	if (score >= 70) return '#ef4444' // red
	if (score >= 35) return '#f97316' // orange
	return '#22c55e' // green
}

const formatDuration = (sec) => {
	if (!sec) return '0 hrs'
	const hrs = Math.floor(sec / 3600)
	const mins = Math.floor((sec % 3600) / 60)
	if (hrs > 0) {
		return `${hrs}h ${mins}m`
	}
	return `${mins} mins`
}

const getQuizTrendOptions = (trend) => {
	return {
		chart: {
			id: 'quiz-trend',
			toolbar: { show: false },
			zoom: { enabled: false },
		},
		xaxis: {
			categories: trend.map((t) => t.quiz),
			labels: {
				style: { fontSize: '10px' },
				rotate: -15,
			},
		},
		yaxis: {
			max: 100,
			min: 0,
			labels: {
				formatter: (val) => `${val}%`,
			},
		},
		colors: ['#4f46e5'],
		stroke: { curve: 'smooth', width: 3 },
		markers: { size: 4 },
	}
}

const getQuizTrendSeries = (trend) => {
	return [
		{
			name: 'Score',
			data: trend.map((t) => t.score),
		},
	]
}

const getInstructorChartOptions = (stats) => {
	return {
		chart: {
			id: 'inst-quizzes',
			toolbar: { show: false },
		},
		xaxis: {
			categories: stats.map((q) => q.title),
			labels: {
				style: { fontSize: '9px' },
				rotate: -20,
			},
		},
		yaxis: {
			max: 100,
			labels: { formatter: (v) => `${v}%` },
		},
		plotOptions: {
			bar: {
				borderRadius: 4,
				horizontal: false,
			},
		},
		colors: ['#6366f1'],
	}
}

const getInstructorChartSeries = (stats) => {
	return [
		{
			name: 'Average Score',
			data: stats.map((q) => q.average),
		},
	]
}

const getDistributionChartOptions = (distribution) => {
	return {
		chart: {
			id: 'batch-dist',
			toolbar: { show: false },
		},
		xaxis: {
			categories: Object.keys(distribution),
			title: { text: 'Completion Bracket (%)', style: { fontSize: '11px', fontWeight: 'bold' } },
		},
		yaxis: {
			title: { text: 'Student Count', style: { fontSize: '11px', fontWeight: 'bold' } },
		},
		colors: ['#4f46e5'],
		plotOptions: {
			bar: { borderRadius: 4, columnWidth: '50%' },
		},
	}
}

const getDistributionChartSeries = (distribution) => {
	return [
		{
			name: 'Students',
			data: Object.values(distribution),
		},
	]
}

const getDepartmentTrendOptions = (trends) => {
	return {
		chart: {
			id: 'dep-trend',
			toolbar: { show: false },
		},
		xaxis: {
			categories: trends.map((t) => t.date),
			labels: { style: { fontSize: '9px' }, rotate: -15 },
		},
		colors: ['#10b981'],
		stroke: { width: 3 },
	}
}

const getDepartmentTrendSeries = (trends) => {
	return [
		{
			name: 'Active Users',
			data: trends.map((t) => t.active_users),
		},
	]
}

const getDepartmentPerformanceOptions = (perf) => {
	return {
		chart: {
			id: 'dep-perf',
			toolbar: { show: false },
		},
		xaxis: {
			categories: perf.map((p) => p.course),
			labels: { style: { fontSize: '9px' }, rotate: -20 },
		},
		colors: ['#3b82f6'],
		plotOptions: {
			bar: { borderRadius: 4 },
		},
	}
}

const getDepartmentPerformanceSeries = (perf) => {
	return [
		{
			name: 'Average Grade',
			data: perf.map((p) => p.average_grade),
		},
	]
}

const getAdminTrendOptions = (trends) => {
	return {
		chart: {
			id: 'admin-trend',
			toolbar: { show: false },
		},
		xaxis: {
			categories: trends.map((t) => t.date),
			labels: { style: { fontSize: '9px' }, rotate: -15 },
		},
		colors: ['#4f46e5'],
		stroke: { width: 3 },
	}
}

const getAdminTrendSeries = (trends) => {
	return [
		{
			name: 'New Registrations',
			data: trends.map((t) => t.signups),
		},
	]
}
</script>

<style scoped>
.shadow-xxs {
	box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
}
.shadow-xs {
	box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
}
</style>
