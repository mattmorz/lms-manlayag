<template>
	<div class="relative w-full">
		<div v-if="props.data.quizzes?.length && !showQuiz && readOnly" class="leading-6 mb-2">
			{{
				__('This video contains {0} {1}:').format(
					props.data.quizzes.length,
					props.data.quizzes.length == 1 ? 'quiz' : 'quizzes'
				)
			}}

			<div v-for="(quiz, index) in props.data.quizzes" :key="index" class="pl-3 mt-1 text-sm text-ink-gray-7">
				<span>
					{{ index + 1 }}. <span class="font-semibold"> {{ quiz.quiz }} </span>
				</span>
				{{ __('at {0} minutes').format(formatTimestamp(quiz.time)) }}
			</div>
		</div>
		<div
			v-show="!showQuiz"
			ref="videoContainer"
			class="video-block relative group"
		>
			<div
				ref="plyrElement"
				class="video-player rounded-md border border-gray-100"
				:src="props.data.embed"
				:data-plyr-provider="props.data.service"
			></div>
		</div>
		<Quiz
			v-if="showQuiz"
			:quizName="currentQuiz"
			:inVideo="true"
			:backToVideo="resumeVideo"
		/>
		<div v-if="!readOnly" class="mt-2 text-center" @click="showQuizModal = true">
			<Button variant="solid">
				{{ __('Add Quiz to Video') }}
			</Button>
		</div>
	</div>
	<QuizInVideo
		v-model="showQuizModal"
		:quizzes="props.data.quizzes || []"
		:saveQuizzes="props.saveQuizzes"
		:duration="duration"
	/>
	<Dialog
		v-model="showQuizLoader"
		:options="{
			size: 'sm',
		}"
	>
		<template #body>
			<div class="flex flex-col space-y-2 p-5 text-base leading-5">
				<span class="font-semibold">
					{{ __('Time for a Quiz') }}
				</span>
				<span>
					{{
						__(
							'Complete the upcoming quiz to continue watching the video. The quiz will open in {0} {1}.'
						).format(quizLoadTimer, quizLoadTimer === 1 ? 'second' : 'seconds')
					}}
				</span>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { formatSeconds, formatTimestamp } from '@/utils'
import QuizInVideo from '@/components/Modals/QuizInVideo.vue'

const plyrElement = ref(null)
const videoContainer = ref(null)
const showQuizModal = ref(false)
const showQuiz = ref(false)
const showQuizLoader = ref(false)
const quizLoadTimer = ref(0)
const currentQuiz = ref(null)
const nextQuiz = ref({})
let player = null

const props = defineProps({
	data: {
		type: Object,
		required: true,
	},
	readOnly: {
		type: Boolean,
		default: true,
	},
	saveQuizzes: {
		type: Function,
		default: () => {},
	},
})

const duration = ref(0)
const currentTime = ref(0)

let checkInterval = null

onMounted(() => {
	checkInterval = setInterval(() => {
		if (plyrElement.value && plyrElement.value.plyr) {
			clearInterval(checkInterval)
			player = plyrElement.value.plyr
			setupPlayer(player)
		}
	}, 100)
})

onBeforeUnmount(() => {
	if (checkInterval) clearInterval(checkInterval)
})

const setupPlayer = (plyrInstance) => {
	if (plyrInstance.duration) {
		duration.value = plyrInstance.duration
		updateMarkers()
		updateNextQuiz()
	}

	plyrInstance.on('ready', () => {
		duration.value = plyrInstance.duration
		updateMarkers()
		updateNextQuiz()
	})

	plyrInstance.on('timeupdate', () => {
		if (!duration.value && plyrInstance.duration) {
			duration.value = plyrInstance.duration
			updateMarkers()
		}
		currentTime.value = plyrInstance.currentTime
		
		// If we hit the next quiz, pause and trigger loading
		if (nextQuiz.value?.time && currentTime.value >= nextQuiz.value.time) {
			plyrInstance.pause()
			currentQuiz.value = nextQuiz.value.quiz
			quizLoadTimer.value = 7
		}
	})
}

watch(quizLoadTimer, () => {
	if (quizLoadTimer.value > 0) {
		showQuizLoader.value = true
		setTimeout(() => {
			quizLoadTimer.value -= 1
		}, 1000)
	} else {
		showQuizLoader.value = false
		showQuiz.value = true
	}
})

const resumeVideo = () => {
	showQuiz.value = false
	currentQuiz.value = null
	if (player) {
		player.play()
	}
	updateNextQuiz()
}

const updateNextQuiz = () => {
	const quizzes = props.data.quizzes || []
	if (!quizzes.length) {
		nextQuiz.value = {}
		return
	}

	quizzes.forEach((quiz) => {
		if (typeof quiz.time == 'string' && quiz.time.includes(':')) {
			let time = quiz.time.split(':')
			let timeInSeconds = parseInt(time[0]) * 60 + parseInt(time[1])
			quiz.time = timeInSeconds
		}
	})

	quizzes.sort((a, b) => a.time - b.time)

	const nextQuizIndex = quizzes.findIndex(
		(quiz) => quiz.time > currentTime.value
	)
	if (nextQuizIndex !== -1) {
		nextQuiz.value = quizzes[nextQuizIndex]
	} else {
		nextQuiz.value = {}
	}
}

const updateMarkers = () => {
	if (!player || !duration.value) return
	const container = player.elements.container
	if (!container) return
	const progressEl = container.querySelector('.plyr__progress')
	if (!progressEl) return

	// Remove old markers if any
	let markersContainer = progressEl.querySelector('.plyr-quiz-markers')
	if (!markersContainer) {
		markersContainer = document.createElement('div')
		markersContainer.className = 'plyr-quiz-markers absolute inset-0 pointer-events-none'
		markersContainer.style.position = 'absolute'
		markersContainer.style.top = '0'
		markersContainer.style.bottom = '0'
		markersContainer.style.left = '0'
		markersContainer.style.right = '0'
		markersContainer.style.height = '100%'
		markersContainer.style.pointerEvents = 'none'
		progressEl.appendChild(markersContainer)
	}
	
	markersContainer.innerHTML = ''
	
	const quizzes = props.data.quizzes || []
	quizzes.forEach((q) => {
		const marker = document.createElement('div')
		marker.className = 'absolute top-0 h-full bg-amber-500 rounded-sm z-10'
		marker.style.position = 'absolute'
		marker.style.backgroundColor = '#f59e0b'
		marker.style.width = '6px'
		marker.style.height = '100%'
		marker.style.top = '0'
		marker.style.zIndex = '10'
		
		let t = q.time
		if (typeof t === 'string' && t.includes(':')) {
			let parts = t.split(':')
			t = parseInt(parts[0]) * 60 + parseInt(parts[1])
		}
		
		const pct = (t / duration.value) * 100
		marker.style.left = `${pct}%`
		markersContainer.appendChild(marker)
	})
}

watch(() => props.data.quizzes, () => {
	updateNextQuiz()
	updateMarkers()
}, { deep: true })
</script>

<style scoped>
.video-block {
	width: 100%;
	margin: 0 auto;
}
</style>
