<template>
	<header
		v-if="!fromLesson"
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
	</header>
	<div
		class="md:w-7/12 md:mx-auto mx-4"
		:class="fromLesson ? 'pt-0 pb-0 md:w-full' : 'py-10'"
	>
		<Quiz :quizName="quizID" />
	</div>
</template>
<script setup>
import Quiz from '@/components/Quiz.vue'
import { createResource, Breadcrumbs, usePageMeta } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '../stores/session'

const { brand } = sessionStore()
const user = inject('$user')
const router = useRouter()
const fromLesson = ref(false)

onMounted(() => {
	if (!user.data) {
		router.push({ name: 'Courses' })
	}

	if (new URLSearchParams(window.location.search).get('fromLesson')) {
		fromLesson.value = true
	}
})

const props = defineProps({
	quizID: {
		type: String,
		required: true,
	},
})

const title = createResource({
	url: 'frappe.client.get_value',
	params: {
		doctype: 'LMS Quiz',
		fieldname: 'title',
		filters: {
			name: props.quizID,
		},
	},
	auto: true,
})

const breadcrumbs = computed(() => {
	return [{ label: __('Quiz Submission') }, { label: title.data?.title }]
})

usePageMeta(() => {
	return {
		title: `${title.data?.title}`,
		icon: brand.favicon,
	}
})
</script>

<style>
body {
	margin: 0 !important;
	padding: 0 !important;
}
</style>
