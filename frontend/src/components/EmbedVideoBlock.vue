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

		<div v-if="hasTranscript" class="mt-4">
			<div class="flex items-center space-x-2">
				<Button
					variant="ghost"
					class="flex items-center space-x-2 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
					@click="showTranscript = !showTranscript"
				>
					<template #prefix>
						<FileText class="w-4 h-4 stroke-1.5" />
					</template>
					<span>{{ showTranscript ? __('Hide Transcript') : __('Show Transcript') }}</span>
				</Button>

				<Button
					v-if="isAdmin"
					variant="ghost"
					class="flex items-center space-x-2 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
					@click="triggerTranscriptUpload"
				>
					<template #prefix>
						<Upload class="w-4 h-4 stroke-1.5" />
					</template>
					<span>{{ __('Upload Transcript') }}</span>
				</Button>

				<Button
					v-if="isAdmin && wordsList.length > 0"
					variant="ghost"
					class="flex items-center space-x-2 text-sm text-ink-gray-7 hover:text-ink-gray-9 hover:bg-gray-100 dark:hover:bg-gray-800"
					@click="openEditTranscriptModal"
				>
					<template #prefix>
						<Edit class="w-4 h-4 stroke-1.5" />
					</template>
					<span>{{ __('Edit Transcript') }}</span>
				</Button>

				<input
					ref="transcriptFileInput"
					type="file"
					accept=".vtt,.srt,.json"
					class="hidden"
					@change="handleTranscriptFile"
				/>
			</div>
			
			<div 
				v-show="showTranscript" 
				class="mt-2 border border-outline-gray-2 rounded-md bg-surface-gray-2 p-4 transition-all duration-300"
			>
				<div 
					v-if="transcriptResource.loading" 
					class="flex items-center justify-center py-6 text-sm text-ink-gray-5"
				>
					<LoadingIndicator class="w-5 h-5 mr-2" />
					<span>{{ __('Loading transcript...') }}</span>
				</div>
				<div 
					v-else-if="transcriptResource.error" 
					class="text-sm text-red-500 py-2 text-center"
				>
					{{ __('Could not load transcript for this video.') }}
				</div>
				<div 
					v-else-if="wordsList.length === 0" 
					class="text-sm text-ink-gray-5 py-2 text-center"
				>
					{{ __('No transcript available.') }}
				</div>
				<div 
					v-else
					ref="transcriptContainer"
					class="relative overflow-y-auto max-h-48 scrollbar-thin scroll-smooth text-base leading-relaxed pr-2"
				>
					<span 
						v-for="(word, index) in wordsList" 
						:key="index"
						:id="'word-' + index"
						class="inline-block mr-1 cursor-pointer transition-colors duration-150 rounded px-0.5 select-none"
						:class="index === activeWordIndex ? 'bg-yellow-200/80 text-ink-gray-9 font-bold dark:bg-yellow-900/50 dark:text-yellow-100' : 'text-ink-gray-7 hover:bg-gray-100 dark:hover:bg-gray-800'"
						@click="seekToWord(word.start)"
					>
						{{ word.text }}
					</span>
				</div>
			</div>
		</div>

		<Quiz
			v-if="showQuiz"
			:quizName="currentQuiz"
			:inVideo="true"
			:enforce-pass="currentQuizObj.enforce_pass"
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
	<Dialog
		v-model="showEditTranscriptModal"
		:options="{
			title: __('Edit Transcript'),
			size: 'xl',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: () => saveEditedTranscript(),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
				<div 
					v-for="(segment, index) in editableSegments" 
					:key="index"
					class="flex items-center space-x-3 border-b pb-2 last:border-0"
				>
					<span class="text-xs text-ink-gray-5 w-16 shrink-0 font-mono">
						{{ formatSeconds(segment.start) }}
					</span>
					<input
						v-model="segment.start"
						type="number"
						step="0.1"
						class="w-16 border rounded px-1.5 py-0.5 text-xs text-center font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
						title="Start Time (seconds)"
					/>
					<textarea
						v-model="segment.text"
						rows="1"
						class="flex-1 border rounded px-2 py-1 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-amber-500"
					/>
					<Button
						variant="ghost"
						class="text-red-500 hover:text-red-700 p-1"
						@click="removeSegment(index)"
					>
						<template #icon>
							<Trash2 class="size-4" />
						</template>
					</Button>
				</div>
				<div class="pt-2">
					<Button
						variant="outline"
						class="w-full flex justify-center items-center py-2"
						@click="addSegment"
					>
						<template #prefix>
							<Plus class="size-4" />
						</template>
						{{ __('Add Segment') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, onMounted, computed, watch, onBeforeUnmount, inject } from 'vue'
import { Button, Dialog, LoadingIndicator, createResource, toast } from 'frappe-ui'
import { FileText, Upload, Edit, Trash2, Plus } from 'lucide-vue-next'
import { formatSeconds, formatTimestamp } from '@/utils'
import QuizInVideo from '@/components/Modals/QuizInVideo.vue'
import { usersStore } from '@/stores/user'

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

// Refs
const plyrElement = ref(null)
const videoContainer = ref(null)
const showQuizModal = ref(false)
const showQuiz = ref(false)
const showQuizLoader = ref(false)
const quizLoadTimer = ref(0)
const currentQuiz = ref(null)
const nextQuiz = ref({})
const duration = ref(0)
const currentTime = ref(0)
const showTranscript = ref(false)
const transcriptContainer = ref(null)
const transcriptFileInput = ref(null)

const triggerTranscriptUpload = () => {
	transcriptFileInput.value?.click()
}

const getRouteParams = () => {
	const path = window.location.pathname
	const match = path.match(/courses\/([^\/]+)\/learn\/([^\/\-]+)-([^\/\-]+)/)
	if (match) {
		return {
			courseName: match[1],
			chapterNumber: match[2],
			lessonNumber: match[3],
		}
	}
	return {}
}

const isAdmin = computed(() => {
	return (
		user.data?.is_instructor ||
		user.data?.is_moderator ||
		user.data?.is_evaluator
	)
})

const uploadTranscriptResource = createResource({
	url: 'lms.lms.api.upload_video_transcript',
	onSuccess(data) {
		toast.success(__('Transcript saved successfully.'))
		transcriptResource.reload()
		showTranscript.value = true
		showEditTranscriptModal.value = false
		if (transcriptFileInput.value) {
			transcriptFileInput.value.value = ''
		}
	},
	onError(err) {
		toast.error(err.messages?.[0] || err || __('Failed to upload transcript.'))
		if (transcriptFileInput.value) {
			transcriptFileInput.value.value = ''
		}
	}
})

const showEditTranscriptModal = ref(false)
const editableSegments = ref([])

const openEditTranscriptModal = () => {
	editableSegments.value = JSON.parse(JSON.stringify(transcriptResource.data || []))
	showEditTranscriptModal.value = true
}

const removeSegment = (index) => {
	editableSegments.value.splice(index, 1)
}

const addSegment = () => {
	let lastStart = 0
	if (editableSegments.value.length > 0) {
		const lastSeg = editableSegments.value[editableSegments.value.length - 1]
		lastStart = parseFloat(lastSeg.start) + 5
	}
	editableSegments.value.push({
		text: '',
		start: lastStart,
		duration: 5
	})
}

const saveEditedTranscript = () => {
	const sorted = [...editableSegments.value].sort((a, b) => parseFloat(a.start) - parseFloat(b.start))
	sorted.forEach(s => {
		s.start = parseFloat(s.start) || 0
		s.duration = parseFloat(s.duration) || 0
	})

	const params = getRouteParams()
	uploadTranscriptResource.submit({
		course_name: params.courseName,
		chapter_number: params.chapterNumber,
		lesson_number: params.lessonNumber,
		video_id: videoId.value,
		file_content: JSON.stringify(sorted),
		file_name: 'transcript.json',
	})
}

const handleTranscriptFile = (event) => {
	const file = event.target.files?.[0]
	if (!file) return

	const reader = new FileReader()
	reader.onload = (e) => {
		const content = e.target.result
		const params = getRouteParams()
		uploadTranscriptResource.submit({
			course_name: params.courseName,
			chapter_number: params.chapterNumber,
			lesson_number: params.lessonNumber,
			video_id: videoId.value,
			file_content: content,
			file_name: file.name,
		})
	}
	reader.readAsText(file)
}

let player = null
let checkInterval = null

// Inject / User Store
const user = inject('$user') || usersStore().userResource

// Resources
const passedQuizzes = createResource({
	url: 'frappe.client.get_list',
	makeParams() {
		return {
			doctype: 'LMS Quiz Submission',
			filters: {
				member: user.data?.name,
				quiz: ['in', (props.data.quizzes || []).map(q => q.quiz)],
			},
			fields: ['quiz', 'percentage', 'passing_percentage'],
		}
	},
})

// Computed Properties for Transcripts
const hasTranscript = computed(() => {
	const service = props.data.service || ''
	return service.toLowerCase() === 'youtube' || service.toLowerCase() === 'vimeo'
})

const videoId = computed(() => {
	const embedUrl = props.data.embed
	const service = props.data.service
	if (!embedUrl) return ''
	const s = String(embedUrl).trim()
	if (service === 'youtube') {
		try {
			const urlObj = new URL(s)
			if (urlObj.hostname.includes('youtube.com')) {
				return urlObj.searchParams.get('v') || urlObj.pathname.split('/').pop()
			} else if (urlObj.hostname.includes('youtu.be')) {
				return urlObj.pathname.split('/').pop()
			}
		} catch (e) {}
		const match = s.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=))([\w-]{11})/)
		return match ? match[1] : s
	} else if (service === 'vimeo') {
		const match = s.match(/(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)/)
		return match ? match[1] : s
	}
	return s
})

const transcriptResource = createResource({
	url: 'lms.lms.api.get_video_transcript',
	makeParams() {
		return {
			video_id: videoId.value,
			service: props.data.service
		}
	},
	auto: false
})

const passedQuizNames = computed(() => {
	const submissions = passedQuizzes.data || []
	const passed = new Set()
	submissions.forEach(sub => {
		const passingPercent = sub.passing_percentage || 0
		if (Math.ceil(sub.percentage) >= passingPercent) {
			passed.add(sub.quiz)
		}
	})
	return passed
})

const currentQuizObj = computed(() => {
	const quizzes = props.data.quizzes || []
	return quizzes.find(q => q.quiz === currentQuiz.value) || {}
})

const wordsList = computed(() => {
	if (!transcriptResource.data) return []
	const words = []
	transcriptResource.data.forEach((segment) => {
		const segmentText = segment.text || ''
		const segmentWords = segmentText.trim().split(/\s+/)
		if (segmentWords.length === 0 || (segmentWords.length === 1 && segmentWords[0] === '')) return
		
		const wordDuration = segment.duration / segmentWords.length
		segmentWords.forEach((wordText, index) => {
			words.push({
				text: wordText,
				start: segment.start + (index * wordDuration),
				duration: wordDuration
			})
		})
	})
	return words
})

const activeWordIndex = computed(() => {
	const time = currentTime.value
	let activeIndex = -1
	for (let i = 0; i < wordsList.value.length; i++) {
		const word = wordsList.value[i]
		if (word.start <= time) {
			activeIndex = i
		} else {
			break
		}
	}
	return activeIndex
})

// Methods / Actions
const seekToWord = (start) => {
	if (player) {
		player.currentTime = start
		player.play()
	}
}

const resumeVideo = () => {
	showQuiz.value = false
	currentQuiz.value = null
	passedQuizzes.reload()
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
		(quiz) => quiz.time > currentTime.value && !passedQuizNames.value.has(quiz.quiz)
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

// Watchers
watch(
	() => [props.data.quizzes, user.data?.name],
	([quizzes, username]) => {
		if (quizzes && quizzes.length > 0 && username) {
			passedQuizzes.reload()
		}
	},
	{ immediate: true }
)

watch(passedQuizNames, () => {
	updateNextQuiz()
})

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

watch(
	() => [videoId.value, props.data.service],
	([vid, svc]) => {
		if (vid && svc && hasTranscript.value) {
			transcriptResource.reload()
		}
	},
	{ immediate: true }
)

watch(activeWordIndex, (newIndex) => {
	if (newIndex === -1 || !transcriptContainer.value) return
	const container = transcriptContainer.value
	const activeWordEl = container.querySelector(`#word-${newIndex}`)
	if (activeWordEl) {
		const containerRect = container.getBoundingClientRect()
		const elRect = activeWordEl.getBoundingClientRect()
		
		const relativeTop = elRect.top - containerRect.top
		const scrollTarget = container.scrollTop + relativeTop - (containerRect.height / 2) + (elRect.height / 2)
		
		container.scrollTo({
			top: scrollTarget,
			behavior: 'smooth'
		})
	}
})

watch(() => props.data.quizzes, () => {
	updateNextQuiz()
	updateMarkers()
}, { deep: true })

// Lifecycle hooks
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
</script>

<style scoped>
.video-block {
	width: 100%;
	margin: 0 auto;
}
</style>
