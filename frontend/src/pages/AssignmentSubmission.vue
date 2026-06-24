<template>
	<header
		v-if="!fromLesson"
		class="flex justify-between sticky top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
	</header>
	<div class="overflow-hidden h-[calc(100vh-3.2rem)]">
		<Assignment
			:assignmentID="assignmentID"
			:submissionName="submissionName"
			:showTitle="!fromLesson"
		/>
	</div>
</template>
<script setup>
import { Breadcrumbs, createResource, usePageMeta } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '../stores/session'
import Assignment from '@/components/Assignment.vue'

const user = inject('$user')
const fromLesson = ref(false)
const { brand } = sessionStore()

const props = defineProps({
	assignmentID: {
		type: String,
		required: true,
	},
	submissionName: {
		type: String,
		default: 'new',
	},
})

const router = useRouter()
const assignmentDetails = createResource({
	url: 'frappe.client.get',
	params: {
		doctype: 'LMS Assignment',
		name: props.assignmentID,
	},
	auto: true,
	onSuccess(doc) {
		if (
			user.data?.roles?.includes('Course Creator') &&
			doc.owner !== user.data.name &&
			!user.data?.is_moderator
		) {
			router.push({ name: 'Courses' })
		}
	}
})

onMounted(async () => {
	if (user && user.promise) {
		try {
			await user.promise
		} catch (e) {
			console.error('Failed to load user info:', e)
		}
	}
	if (!user.data) {
		window.location.href = '/login'
		return
	}

	if (new URLSearchParams(window.location.search).get('fromLesson')) {
		fromLesson.value = true
	}
})

const breadcrumbs = computed(() => {
	let crumbs = [
		{
			label: __('Submissions'),
			route: { name: 'AssignmentSubmissionList' },
		},
		{
			label: assignmentDetails.data?.title,
			route: {
				name: 'AssignmentSubmission',
				params: {
					assignmentID: props.assignmentID,
				},
			},
		},
	]
	return crumbs
})

usePageMeta(() => {
	return {
		title: assignmentDetails.data?.title,
		icon: brand.favicon,
	}
})
</script>
