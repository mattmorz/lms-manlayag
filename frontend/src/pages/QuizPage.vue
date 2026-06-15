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
import { computed, inject, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '../stores/session'

const { brand } = sessionStore()
const user = inject('$user')
const router = useRouter()
const fromLesson = ref(false)

onMounted(() => {
	if (new URLSearchParams(window.location.search).get('fromLesson')) {
		fromLesson.value = true
		document.documentElement.classList.add('from-lesson-iframe')
		document.body.classList.add('from-lesson-iframe')
	}

	if (!user.data && !fromLesson.value) {
		router.push({ name: 'Courses' })
	}
})

onUnmounted(() => {
	document.documentElement.classList.remove('from-lesson-iframe')
	document.body.classList.remove('from-lesson-iframe')
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

.from-lesson-iframe,
.from-lesson-iframe body,
.from-lesson-iframe #app,
.from-lesson-iframe .h-screen,
.from-lesson-iframe .h-full,
.from-lesson-iframe #scrollContainer {
	height: auto !important;
	min-height: 0 !important;
	overflow: visible !important;
}

/* Fullscreen background & size overrides */
:fullscreen,
html:fullscreen,
body:fullscreen {
	background-color: #fafafa !important;
	min-height: 100vh !important;
	height: 100% !important;
	overflow-y: auto !important;
}

html:fullscreen body,
html:fullscreen #app,
html:fullscreen #scrollContainer {
	background-color: #fafafa !important;
	min-height: 100vh !important;
	height: 100% !important;
	overflow: auto !important;
}

::backdrop {
	background-color: #fafafa !important;
}
</style>

