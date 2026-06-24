<template>
	<Dialog
		v-model="show"
		:options="{
			size: 'xl',
		}"
	>
		<template #body>
			<div class="flex flex-col max-h-[85vh] bg-surface-white rounded-lg">
				<!-- Sticky Header -->
				<div class="px-6 pt-6 pb-4 border-b flex items-center justify-between">
					<div>
						<h3 class="text-xl font-bold text-ink-gray-9">
							{{ __('Submit Peer Review') }}
						</h3>
						<p class="text-sm text-ink-gray-5 mt-1">
							{{ __('Evaluate the work of your peer using the rubric below.') }}
						</p>
					</div>
				</div>

				<!-- Scrollable Content -->
				<div class="px-6 py-4 text-base overflow-y-auto flex-1 min-h-0 bg-surface-white">
					<div v-if="loadingRubric" class="py-12 flex justify-center items-center">
						<span class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></span>
					</div>

					<div v-else class="space-y-6">
						<!-- Rubric Section -->
						<div v-if="rubricDoc" class="space-y-6">
							<h4 class="text-base font-semibold text-ink-gray-8 border-b pb-2">
								{{ __('Rubric Criteria') }}: {{ rubricDoc.title }}
							</h4>
							<div
								v-for="(criterion, idx) in rubricDoc.criteria"
								:key="idx"
								class="p-5 rounded-lg bg-surface-white border border-outline-gray-2 border-l-4 space-y-4 shadow-sm"
								:class="[getCriterionColor(idx).border]"
							>
								<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
									<div>
										<h5 class="font-bold text-ink-gray-9 text-base">
											{{ criterion.criterion_name }}
										</h5>
										<p class="text-xs text-ink-gray-6 mt-1">
											{{ criterion.description }}
										</p>
									</div>
									<div class="flex flex-wrap gap-2 mt-1 sm:mt-0">
										<Badge :theme="getCriterionColor(idx).theme" size="sm" class="font-bold">
											{{ __('Weight') }}: {{ getRelativeWeight(criterion.weight).toFixed(0) }}%
										</Badge>
										<Badge theme="gray" size="sm" class="font-semibold">
											<template #prefix>
												<Award class="size-3 mr-1 text-ink-gray-5" />
											</template>
											{{ __('Max') }}: {{ criterion.max_score }}
										</Badge>
									</div>
								</div>

								<div class="bg-surface-gray-1 p-4 rounded-md border border-outline-gray-1 space-y-3">
									<div class="flex items-center justify-between text-xs text-ink-gray-5 font-semibold">
										<span>{{ __('Evaluation Score') }}</span>
										<span class="text-sm font-bold text-ink-gray-9">
											{{ scores[criterion.criterion_name] || 0 }} / {{ criterion.max_score }}
										</span>
									</div>

									<div class="flex items-center gap-4">
										<input
											type="range"
											min="0"
											:max="criterion.max_score"
											step="1"
											:value="scores[criterion.criterion_name] ?? 0"
											@input="scores[criterion.criterion_name] = Math.min(criterion.max_score, Math.max(0, Number($event.target.value) || 0))"
											class="flex-1 h-1.5 bg-outline-gray-2 rounded-lg appearance-none cursor-pointer accent-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
										/>
										<input
											type="number"
											min="0"
											:max="criterion.max_score"
											:value="scores[criterion.criterion_name] ?? 0"
											@input="scores[criterion.criterion_name] = Math.min(criterion.max_score, Math.max(0, Number($event.target.value) || 0))"
											class="w-20 rounded border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-center font-bold text-sm text-ink-gray-9 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										/>
									</div>
								</div>

								<div>
									<textarea
										v-model="comments[criterion.criterion_name]"
										class="w-full rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm text-ink-gray-9 placeholder-ink-gray-4 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										rows="2"
										:placeholder="__('Specific feedback comments for this criterion...')"
									></textarea>
								</div>
							</div>
						</div>

						<!-- General Feedback Section -->
						<div class="space-y-4">
							<h4 class="text-base font-semibold text-ink-gray-8 border-b pb-2">
								{{ __('Written Feedback') }}
							</h4>
							
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div class="space-y-1.5">
									<label class="block text-xs text-ink-gray-5">
										{{ __('Strengths') }}
									</label>
									<textarea
										v-model="strengths"
										class="w-full rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm text-ink-gray-9 placeholder-ink-gray-4 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										rows="3"
										:placeholder="__('What did they do well?')"
									></textarea>
								</div>

								<div class="space-y-1.5">
									<label class="block text-xs text-ink-gray-5">
										{{ __('Areas for Improvement') }}
									</label>
									<textarea
										v-model="areasForImprovement"
										class="w-full rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm text-ink-gray-9 placeholder-ink-gray-4 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										rows="3"
										:placeholder="__('What could be improved?')"
									></textarea>
								</div>
							</div>
							
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div class="space-y-1.5">
									<label class="block text-xs text-ink-gray-5">
										{{ __('Recommendations') }}
									</label>
									<textarea
										v-model="recommendations"
										class="w-full rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm text-ink-gray-9 placeholder-ink-gray-4 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										rows="3"
										:placeholder="__('How can they improve this output?')"
									></textarea>
								</div>

								<div class="space-y-1.5">
									<label class="block text-xs text-ink-gray-5">
										{{ __('General Feedback') }}
									</label>
									<textarea
										v-model="generalFeedback"
										class="w-full rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm text-ink-gray-9 placeholder-ink-gray-4 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										rows="3"
										:placeholder="__('Overall thoughts...')"
									></textarea>
								</div>
							</div>
						</div>

						<!-- Score indicator -->
						<div class="p-4 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-between">
							<div>
								<span class="text-sm font-semibold text-indigo-900">
									{{ __('Computed Review Score') }}
								</span>
								<p class="text-xs text-indigo-700 mt-0.5">
									{{ __('Normalized percentage score out of 100% based on criterion weights.') }}
								</p>
							</div>
							<div class="text-right">
								<span class="text-2xl font-black text-indigo-900">
									{{ computedScore.toFixed(1) }}%
								</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Sticky Footer -->
				<div class="px-6 py-4 border-t flex justify-end space-x-2 bg-surface-white rounded-b-lg">
					<Button variant="outline" @click="show = false">
						{{ __('Cancel') }}
					</Button>
					<Button variant="solid" :loading="submitting" @click="submitReview">
						{{ __('Submit Review') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, FormControl, Button, toast, call, Badge } from 'frappe-ui'
import { ref, computed, watch } from 'vue'
import { Award } from 'lucide-vue-next'

const show = defineModel()
const props = defineProps({
	assignmentName: {
		type: String,
		required: true,
	},
	peerAssignmentName: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['success'])

const loadingRubric = ref(false)
const rubricDoc = ref(null)
const scores = ref({})
const comments = ref({})
const strengths = ref('')
const areasForImprovement = ref('')
const recommendations = ref('')
const generalFeedback = ref('')
const submitting = ref(false)

const colors = [
	{ border: 'border-l-blue-500', text: 'text-blue-700', bg: 'bg-blue-50', theme: 'blue' },
	{ border: 'border-l-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', theme: 'emerald' },
	{ border: 'border-l-amber-500', text: 'text-amber-700', bg: 'bg-amber-50', theme: 'amber' },
	{ border: 'border-l-rose-500', text: 'text-rose-700', bg: 'bg-rose-50', theme: 'rose' },
	{ border: 'border-l-indigo-500', text: 'text-indigo-700', bg: 'bg-indigo-50', theme: 'indigo' },
	{ border: 'border-l-orange-500', text: 'text-orange-700', bg: 'bg-orange-50', theme: 'orange' },
	{ border: 'border-l-teal-500', text: 'text-teal-700', bg: 'bg-teal-50', theme: 'teal' },
	{ border: 'border-l-fuchsia-500', text: 'text-fuchsia-700', bg: 'bg-fuchsia-50', theme: 'fuchsia' },
]

const getCriterionColor = (idx) => {
	return colors[idx % colors.length]
}

const totalWeight = computed(() => {
	if (!rubricDoc.value || !rubricDoc.value.criteria) return 0
	return rubricDoc.value.criteria.reduce((sum, c) => sum + (c.weight || 0), 0)
})

const getRelativeWeight = (weight) => {
	if (totalWeight.value === 0) return 0
	return ((weight || 0) / totalWeight.value) * 100
}

// Fetch Rubric details when assignmentName changes
watch(
	() => props.assignmentName,
	async (newVal) => {
		if (newVal) {
			loadingRubric.value = true
			try {
				const assignment = await call('frappe.client.get', {
					doctype: 'LMS Assignment',
					name: newVal,
				})
				
				if (assignment && assignment.peer_review_rubric) {
					const rubric = await call('frappe.client.get', {
						doctype: 'Peer Review Rubric',
						name: assignment.peer_review_rubric,
					})
					
					rubricDoc.value = rubric
					// Initialize score and comment maps
					scores.value = {}
					comments.value = {}
					if (rubric && rubric.criteria) {
						rubric.criteria.forEach((c) => {
							scores.value[c.criterion_name] = c.max_score
							comments.value[c.criterion_name] = ''
						})
					}
				} else {
					rubricDoc.value = null
				}
			} catch (e) {
				console.error('Failed to load rubric:', e)
				toast.error('Failed to load evaluation rubric.')
			} finally {
				loadingRubric.value = false
			}
		}
	},
	{ immediate: true }
)

// Computed score out of 100
const computedScore = computed(() => {
	if (!rubricDoc.value || !rubricDoc.value.criteria || rubricDoc.value.criteria.length === 0) {
		return 0
	}
	
	let totalWeight = 0
	let weightedSum = 0
	
	rubricDoc.value.criteria.forEach((c) => {
		const score = scores.value[c.criterion_name] || 0
		const maxScore = c.max_score || 1
		const weight = c.weight || 1.0
		
		weightedSum += (score / maxScore) * weight
		totalWeight += weight
	})
	
	if (totalWeight === 0) return 0
	return (weightedSum / totalWeight) * 100
})

const submitReview = async () => {
	// Validate scores do not exceed maximums
	if (rubricDoc.value && rubricDoc.value.criteria) {
		for (const c of rubricDoc.value.criteria) {
			const val = scores.value[c.criterion_name]
			if (val === undefined || val === null || isNaN(val)) {
				toast.error(`Please provide a valid score for ${c.criterion_name}`)
				return
			}
			if (val < 0 || val > c.max_score) {
				toast.error(`Score for ${c.criterion_name} must be between 0 and ${c.max_score}`)
				return
			}
		}
	}

	submitting.value = true
	try {
		const criteriaFeedback = []
		if (rubricDoc.value && rubricDoc.value.criteria) {
			rubricDoc.value.criteria.forEach((c) => {
				criteriaFeedback.push({
					criterion: c.criterion_name,
					score: scores.value[c.criterion_name],
					comments: comments.value[c.criterion_name],
				})
			})
		}

		await call('lms.lms.api.submit_peer_review', {
			assignment_id: props.peerAssignmentName,
			score: computedScore.value,
			strengths: strengths.value,
			areas_for_improvement: areasForImprovement.value,
			recommendations: recommendations.value,
			general_feedback: generalFeedback.value,
			criteria_feedback: JSON.stringify(criteriaFeedback),
		})

		toast.success('Peer review submitted successfully!')
		show.value = false
		emit('success')
	} catch (e) {
		console.error(e)
		toast.error(e.messages?.[0] || e.message || 'Failed to submit review.')
	} finally {
		submitting.value = false
	}
}
</script>
