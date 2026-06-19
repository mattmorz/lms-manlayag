<template>
	<div v-if="batch.data" class="border-2 rounded-md p-5 lg:w-72">
		<Badge
			v-if="batch.data.seat_count && batch.data.seats_left > 0"
			variant="subtle"
			theme="green"
			size="md"
			:class="
				batch.data.amount || batch.data.courses.length
					? 'float-right'
					: 'w-fit mb-4'
			"
			:label="
				batch.data.seats_left +
				' ' +
				(batch.data.seats_left > 1 ? __('Seats Left') : __('Seat Left'))
			"
		/>
		<Badge
			v-else-if="batch.data.seat_count && batch.data.seats_left <= 0"
			variant="subtle"
			theme="red"
			size="md"
			class="float-right"
			:label="__('Full')"
		/>
		<div
			v-if="batch.data.amount"
			class="text-lg font-semibold mb-3 text-ink-gray-9"
		>
			{{ formatNumberIntoCurrency(batch.data.amount, batch.data.currency) }}
		</div>
		<div
			v-if="batch.data.courses.length"
			class="flex items-center mb-3 text-ink-gray-7"
		>
			<BookOpen class="h-4 w-4 stroke-1.5 mr-2" />
			<span> {{ batch.data.courses.length }} {{ __('Courses') }} </span>
		</div>
		<DateRange
			:startDate="batch.data.start_date"
			:endDate="batch.data.end_date"
			class="mb-3"
		/>
		<div class="flex items-center mb-3 text-ink-gray-7">
			<Clock class="h-4 w-4 stroke-1.5 mr-2" />
			<span>
				{{ formatTime(batch.data.start_time) }} -
				{{ formatTime(batch.data.end_time) }}
			</span>
		</div>
		<div v-if="batch.data.timezone" class="flex items-center text-ink-gray-7">
			<Globe class="h-4 w-4 stroke-1.5 mr-2" />
			<span>
				{{ batch.data.timezone }}
			</span>
		</div>

		<div v-if="!readOnlyMode">
			<router-link
				v-if="canAccessBatch"
				:to="{
					name: 'Batch',
					params: {
						batchName: batch.data.name,
					},
				}"
			>
				<Button variant="solid" class="w-full mt-4">
					<template #prefix>
						<LogIn v-if="isStudent" class="size-4 stroke-1.5" />
						<Settings v-else class="size-4 stroke-1.5" />
					</template>
					<span>
						{{ isStudent ? __('Visit Batch') : __('Manage Batch') }}
					</span>
				</Button>
			</router-link>
			<router-link
				:to="{
					name: 'Billing',
					params: {
						type: 'batch',
						name: batch.data.name,
					},
				}"
				v-else-if="
					batch.data.paid_batch &&
					(!batch.data.seat_count || batch.data.seats_left > 0) &&
					batch.data.accept_enrollments
				"
			>
				<Button v-if="!isStudent" class="w-full mt-4" variant="solid">
					<template #prefix>
						<CreditCard class="size-4 stroke-1.5" />
					</template>
					<span>
						{{ __('Register Now') }}
					</span>
				</Button>
			</router-link>
			<Button
				variant="solid"
				class="w-full mt-2"
				v-else-if="
					batch.data.allow_self_enrollment &&
					!batch.data.use_enrolment_code &&
					(!batch.data.seat_count || batch.data.seats_left > 0) &&
					batch.data.accept_enrollments
				"
				@click="enrollInBatch()"
			>
				<template #prefix>
					<GraduationCap class="size-4 stroke-1.5" />
				</template>
				{{ __('Enroll Now') }}
			</Button>
			<router-link
				v-if="canEditBatch"
				:to="{
					name: 'BatchForm',
					params: {
						batchName: batch.data.name,
					},
				}"
			>
				<Button class="w-full mt-2">
					<template #prefix>
						<Pencil class="size-4 stroke-1.5" />
					</template>
					<span>
						{{ __('Edit') }}
					</span>
				</Button>
			</router-link>

			<!-- Student Enrolment Code Input (Directly visible instead of Enroll Now button) -->
			<div v-if="!isStudent && !canAccessBatch && batch.data.use_enrolment_code && (!batch.data.seat_count || batch.data.seats_left > 0) && batch.data.accept_enrollments" class="mt-4 border-t pt-4 space-y-2">
				<label class="text-xs text-ink-gray-5 font-medium">{{ __('Enter Enrolment Code') }}</label>
				<div class="flex gap-2">
					<input
						type="text"
						v-model="manualCode"
						placeholder="e.g. AB12CD34"
						class="flex-1 text-sm border rounded px-2.5 py-1.5 outline-none focus:border-outline-gray-4 uppercase font-mono"
					/>
					<Button variant="solid" :loading="enroll.loading" @click="enrollWithManualCode">
						{{ __('Enroll') }}
					</Button>
				</div>
			</div>

			<!-- Faculty Sharing Controls -->
			<div v-if="canEditBatch && batch.data.use_enrolment_code" class="mt-6 border-t pt-5">
				<div class="text-sm font-semibold text-ink-gray-9 mb-3">{{ __('Enrolment Code & Link') }}</div>
				
				<div class="mb-3">
					<label class="text-xs text-ink-gray-5">{{ __('Enrolment Code') }}</label>
					<div class="font-mono text-base font-bold bg-surface-gray-2 px-2.5 py-1.5 rounded border text-center select-all cursor-pointer">
						{{ batch.data.enrolment_code }}
					</div>
				</div>

				<div class="mb-3">
					<label class="text-xs text-ink-gray-5">{{ __('Direct Enrolment Link') }}</label>
					<div class="flex gap-2">
						<input
							type="text"
							readonly
							:value="directEnrolmentLink"
							class="flex-1 text-xs border rounded p-1.5 bg-surface-gray-2 text-ink-gray-7 outline-none font-mono overflow-ellipsis"
						/>
						<Button size="sm" @click="copyDirectLink">
							{{ __('Copy') }}
						</Button>
					</div>
				</div>

				<div v-if="batch.data.enrolment_code_expiry" class="mb-3 text-xs">
					<span class="text-ink-gray-5">{{ __('Expires:') }}</span>
					<span :class="isCodeExpired ? 'text-red-500 font-medium ml-1' : 'text-ink-gray-7 ml-1'">
						{{ formatExpiryDate(batch.data.enrolment_code_expiry) }}
						<span v-if="isCodeExpired">({{ __('Expired') }})</span>
					</span>
				</div>

				<div class="flex flex-col items-center mt-4 border border-dashed rounded p-3 bg-surface-gray-1">
					<div class="text-xs font-medium text-ink-gray-7 mb-2">{{ __('Scan QR Code to Enroll') }}</div>
					<img
						:src="`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(directEnrolmentLink)}`"
						alt="Enrolment QR Code"
						class="w-32 h-32 border bg-white p-1 rounded"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { inject, computed, ref, watch } from 'vue'
import { Badge, Button, createResource, toast } from 'frappe-ui'
import {
	BookOpen,
	Clock,
	CreditCard,
	Globe,
	GraduationCap,
	LogIn,
	Pencil,
	Settings,
} from 'lucide-vue-next'
import { formatNumberIntoCurrency, formatTime, cleanError } from '@/utils'
import DateRange from '@/components/Common/DateRange.vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const user = inject('$user')
const readOnlyMode = window.read_only_mode

const props = defineProps({
	batch: {
		type: Object,
		default: null,
	},
})

// State for manual code entry
const showCodeInput = ref(false)
const manualCode = ref(route.query.code || '')

watch(
	() => route.query.code,
	(newCode) => {
		if (newCode) {
			manualCode.value = newCode
		}
	}
)

// Compute direct enrolment link, QR and expiry
const directEnrolmentLink = computed(() => {
	const origin = window.location.origin
	const basePath = window.location.pathname.split('/batches')[0]
	return `${origin}${basePath}/batches/details/${props.batch.data.name}?code=${props.batch.data.enrolment_code}`
})

const copyDirectLink = () => {
	navigator.clipboard.writeText(directEnrolmentLink.value)
	toast.success(__('Direct link copied to clipboard.'))
}

const isCodeExpired = computed(() => {
	if (!props.batch.data.enrolment_code_expiry) return false
	return new Date(props.batch.data.enrolment_code_expiry) < new Date()
})

const formatExpiryDate = (dateStr) => {
	return new Date(dateStr).toLocaleString()
}

const enroll = createResource({
	url: 'lms.lms.utils.enroll_in_batch',
	makeParams(values) {
		return {
			batch: props.batch.data.name,
			code: values.code || null,
		}
	},
})

const enrollInBatch = (code) => {
	const activeCode = code || route.query.code
	if (!activeCode && props.batch.data.use_enrolment_code) {
		showCodeInput.value = true
		toast.error(__('An enrolment code is required to join this batch.'))
		return
	}

	if (!user.data) {
		let redirUrl = `/login?redirect-to=/batches/details/${props.batch.data.name}`
		if (activeCode) {
			redirUrl += `?code=${activeCode}`
		}
		window.location.href = redirUrl
		return
	}

	enroll.submit(
		{
			code: activeCode || null,
		},
		{
			onSuccess(data) {
				toast.success(__('You have been enrolled in this batch'))
				router.push({
					name: 'Batch',
					params: {
						batchName: props.batch.data.name,
					},
				})
			},
			onError(err) {
				let errorMsg = __('Failed to enroll.')
				if (err) {
					if (err.messages && err.messages[0]) {
						errorMsg = err.messages[0]
					} else if (err.message) {
						errorMsg = err.message
					} else if (typeof err === 'string') {
						errorMsg = err
					}
				}
				toast.error(cleanError(errorMsg))
			},
		}
	)
}

const enrollWithManualCode = () => {
	if (!manualCode.value.trim()) {
		toast.error(__('Please enter an enrolment code.'))
		return
	}
	enrollInBatch(manualCode.value.trim())
}

const isStudent = computed(() => {
	return user.data
		? props.batch.data?.students?.includes(user.data?.name)
		: false
})

const isModerator = computed(() => {
	return user.data?.is_moderator
})

const isEvaluator = computed(() => {
	return user.data?.is_evaluator
})

const isInstructor = computed(() => {
	return (
		props.batch.data?.instructors?.filter(
			(instructor) => instructor.name === user.data?.name
		).length > 0
	)
})

const canAccessBatch = computed(() => {
	if (!user.data) {
		return false
	}
	return isModerator.value || isStudent.value || isEvaluator.value
})

const canEditBatch = computed(() => {
	return isModerator.value || isInstructor.value
})
</script>
