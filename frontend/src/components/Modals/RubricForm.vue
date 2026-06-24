<template>
	<Dialog
		v-model="show"
		:options="{
			size: 'xl',
		}"
	>
		<template #body>
			<div class="p-5 text-base">
				<div class="text-lg text-ink-gray-9 font-semibold mb-5 flex justify-between items-center">
					<span>
						{{
							rubricID === 'new'
								? __('Create a Rubric')
								: isReadOnly
								? __('View Rubric')
								: __('Edit Rubric')
						}}
					</span>
				</div>

				<div v-if="loading" class="py-12 flex justify-center items-center">
					<span class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></span>
				</div>

				<div v-else class="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
					<FormControl
						v-model="rubric.title"
						:label="__('Title')"
						:required="true"
						:disabled="isReadOnly"
					/>
					<FormControl
						v-model="rubric.description"
						type="textarea"
						:label="__('Description')"
						:disabled="isReadOnly"
						rows="3"
					/>
					<FormControl
						v-model="rubric.is_public"
						type="checkbox"
						:label="__('Share with others')"
						:disabled="isReadOnly"
					/>

					<!-- Criteria Section -->
					<div class="border-t pt-4 mt-4 space-y-4">
						<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
							<div class="flex items-center space-x-2 flex-wrap gap-y-1">
								<h4 class="font-semibold text-ink-gray-9 text-sm">
									{{ __('Evaluation Criteria') }}
								</h4>
								<span
									v-if="rubric.criteria?.length"
									class="px-2.5 py-0.5 text-xs font-bold rounded-full border transition-all duration-200"
									:class="
										totalWeight === 100
											? 'bg-emerald-50 text-emerald-700 border-emerald-200'
											: 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
									"
								>
									{{ __('Total Weight: ') }}{{ totalWeight }}% / 100%
								</span>
							</div>
							<div v-if="!isReadOnly" class="flex items-center space-x-2">
								<Button
									v-if="rubric.criteria?.length > 1"
									size="sm"
									variant="subtle"
									@click="equalizeWeights"
								>
									{{ __('Distribute Equally') }}
								</Button>
								<Button
									size="sm"
									variant="subtle"
									@click="addCriterion"
								>
									<template #prefix>
										<Plus class="size-4" />
									</template>
									{{ __('Add Criterion') }}
								</Button>
							</div>
						</div>

						<div
							v-if="rubric.criteria?.length && totalWeight !== 100"
							class="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center space-x-2 transition-all duration-200"
						>
							<span class="text-sm">⚠️</span>
							<span>{{ __('The total weight currently sums to ') }}<strong>{{ totalWeight }}%</strong>. {{ __('Please adjust weights to total exactly 100% before saving.') }}</span>
						</div>

						<div v-if="!rubric.criteria?.length" class="text-xs text-ink-gray-5 py-6 border rounded-lg text-center bg-surface-gray-2">
							{{ __('No criteria added yet. Add at least one criterion to evaluate submissions.') }}
						</div>

						<div
							v-for="(criterion, idx) in rubric.criteria"
							:key="idx"
							class="p-4 rounded-lg bg-surface-gray-2 border border-outline-gray-2 space-y-4 relative"
						>
							<button
								v-if="!isReadOnly"
								type="button"
								class="absolute top-2 right-2 text-ink-gray-4 hover:text-ink-red-3 transition-colors"
								@click="removeCriterion(idx)"
							>
								<Trash2 class="size-4" />
							</button>

							<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pr-6">
								<FormControl
									v-model="criterion.criterion_name"
									:label="__('Criterion Name')"
									:required="true"
									:disabled="isReadOnly"
								/>
								<FormControl
									v-model.number="criterion.max_score"
									type="number"
									:label="__('Maximum Score')"
									:required="true"
									:disabled="isReadOnly"
									min="1"
								/>
								<div class="space-y-1">
									<FormControl
										v-model.number="criterion.weight"
										type="number"
										step="0.1"
										:label="__('Weight (%)')"
										:required="true"
										:disabled="isReadOnly"
										min="0"
										max="100"
									/>
									<p class="text-[10px] text-ink-gray-5 leading-normal mt-1">
										{{ __('Percentage weight for this criterion out of 100% total.') }}
									</p>
								</div>
							</div>

							<FormControl
								v-model="criterion.description"
								type="textarea"
								:label="__('Description')"
								:disabled="isReadOnly"
								rows="2"
							/>
						</div>
					</div>
				</div>

				<div class="flex justify-end space-x-2 mt-5">
					<Button variant="subtle" @click="show = false">
						{{ isReadOnly ? __('Close') : __('Cancel') }}
					</Button>
					<Button v-if="!isReadOnly && !loading" variant="solid" @click="saveRubric">
						{{ __('Save') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, FormControl, Button, toast, call, Badge } from 'frappe-ui'
import { ref, reactive, watch, computed, inject } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'

const show = defineModel()
const props = defineProps({
	rubricID: {
		type: String,
		default: 'new',
	},
})

const emit = defineEmits(['saved'])
const user = inject('$user')

const loading = ref(false)
const hasSubmissions = ref(false)
const rubricDoc = ref(null)
const rubric = reactive({
	title: '',
	description: '',
	is_public: false,
	criteria: [],
	owner: '',
	modified: '',
})

const isReadOnly = computed(() => {
	if (props.rubricID === 'new') return false
	if (hasSubmissions.value) return true
	if (user.data?.is_moderator) return false
	return rubric.owner && rubric.owner !== user.data?.name
})

const totalWeight = computed(() => {
	if (!rubric.criteria) return 0
	const sum = rubric.criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0)
	return Math.round(sum * 100) / 100
})

const equalizeWeights = () => {
	const count = rubric.criteria.length
	if (count === 0) return
	const baseWeight = Math.floor((100 / count) * 100) / 100
	let sum = 0
	rubric.criteria.forEach((c, idx) => {
		if (idx === count - 1) {
			c.weight = Math.round((100 - sum) * 100) / 100
		} else {
			c.weight = baseWeight
			sum += baseWeight
		}
	})
}

watch(
	[show, () => props.rubricID],
	([visible, id]) => {
		if (visible) {
			if (id === 'new') {
				rubricDoc.value = null
				hasSubmissions.value = false
				rubric.title = ''
				rubric.description = ''
				rubric.is_public = false
				rubric.criteria = [
					{
						doctype: 'Peer Review Rubric Criterion',
						criterion_name: '',
						max_score: 20,
						weight: 100.0,
						description: '',
					},
				]
				rubric.owner = user.data?.name || ''
				rubric.modified = ''
			} else {
				fetchRubric(id)
			}
		}
	},
	{ immediate: true }
)

const fetchRubric = (id) => {
	loading.value = true
	hasSubmissions.value = false

	// Check if there are submissions first
	call('lms.lms.api.check_content_before_save', {
		content_doctype: 'Peer Review Rubric',
		content_name: id,
	})
		.then((res) => {
			hasSubmissions.value = !!(res && res.has_submissions)
			if (hasSubmissions.value) {
				toast.info(__('This rubric cannot be modified because assignments using it already have student submissions.'))
			}
		})
		.catch((err) => {
			console.error('Error checking submissions:', err)
		})

	call('frappe.client.get', {
		doctype: 'Peer Review Rubric',
		name: id,
	})
		.then((doc) => {
			rubricDoc.value = doc
			rubric.title = doc.title || ''
			rubric.description = doc.description || ''
			rubric.is_public = doc.is_public === 1
			rubric.criteria = doc.criteria || []
			rubric.owner = doc.owner || ''
			rubric.modified = doc.modified || ''
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to load rubric'))
			show.value = false
		})
		.finally(() => {
			loading.value = false
		})
}

const addCriterion = () => {
	rubric.criteria.push({
		doctype: 'Peer Review Rubric Criterion',
		criterion_name: '',
		max_score: 20,
		weight: 0.0,
		description: '',
	})
}

const removeCriterion = (idx) => {
	rubric.criteria.splice(idx, 1)
}

const validateFields = () => {
	if (!rubric.title.trim()) {
		toast.error(__('Please enter a title'))
		return false
	}
	if (!rubric.criteria.length) {
		toast.error(__('Please add at least one criterion'))
		return false
	}
	for (const c of rubric.criteria) {
		if (!c.criterion_name.trim()) {
			toast.error(__('All criteria must have a name'))
			return false
		}
		if (c.max_score <= 0) {
			toast.error(__('Maximum score must be greater than 0'))
			return false
		}
		if (c.weight < 0) {
			toast.error(__('Weight must be 0 or greater'))
			return false
		}
	}
	if (Math.abs(totalWeight.value - 100) > 0.01) {
		toast.error(__('The total weight of all criteria must equal 100% (currently ' + totalWeight.value + '%)'))
		return false
	}
	return true
}

const saveRubric = () => {
	if (hasSubmissions.value) {
		toast.error(__('Cannot modify rubric because there are already submissions using it.'))
		return
	}
	if (!validateFields()) return
	loading.value = true

	const data = {
		title: rubric.title.trim(),
		description: rubric.description.trim(),
		is_public: rubric.is_public ? 1 : 0,
		modified: rubric.modified,
		criteria: rubric.criteria.map((c) => ({
			name: c.name,
			doctype: 'Peer Review Rubric Criterion',
			criterion_name: c.criterion_name.trim(),
			max_score: c.max_score,
			weight: c.weight,
			description: c.description || '',
		})),
	}

	if (props.rubricID === 'new') {
		call('frappe.client.insert', {
			doc: {
				doctype: 'Peer Review Rubric',
				...data,
			},
		})
			.then(() => {
				toast.success(__('Rubric created successfully'))
				emit('saved')
				show.value = false
			})
			.catch((err) => {
				toast.error(err.messages?.[0] || err.message || __('Failed to create rubric'))
			})
			.finally(() => {
				loading.value = false
			})
	} else {
		call('frappe.client.save', {
			doc: {
				...rubricDoc.value,
				...data,
				doctype: 'Peer Review Rubric',
				name: props.rubricID,
			},
		})
			.then(() => {
				toast.success(__('Rubric updated successfully'))
				emit('saved')
				show.value = false
			})
			.catch((err) => {
				toast.error(err.messages?.[0] || err.message || __('Failed to update rubric'))
			})
			.finally(() => {
				loading.value = false
			})
	}
}
</script>

<style scoped>
:deep(input:not([type="checkbox"]):not(:disabled)),
:deep(textarea:not(:disabled)) {
	background-color: #ffffff !important;
	border-color: #d1d5db !important;
	color: #1f2937 !important;
	border-width: 1px !important;
	border-style: solid !important;
	border-radius: 0.375rem !important;
}

:deep(input:not([type="checkbox"]):not(:disabled):focus),
:deep(textarea:not(:disabled):focus) {
	border-color: #6366f1 !important;
	box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}
</style>

