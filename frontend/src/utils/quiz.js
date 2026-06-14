import QuizBlock from '@/components/QuizBlock.vue'
import AssessmentPlugin from '@/components/AssessmentPlugin.vue'
import { createApp, h } from 'vue'
import { usersStore } from '../stores/user'
import translationPlugin from '../translation'
import { CircleHelp } from 'lucide-vue-next'
import router from '@/router'
import { getLmsRoute } from '@/utils/basePath'

export class Quiz {
	constructor({ data, api, readOnly }) {
		this.data = data
		this.api = api
		this.readOnly = readOnly
	}

	static get toolbox() {
		const app = createApp({
			render: () => h(CircleHelp, { size: 5, strokeWidth: 1.5 }),
		})

		const div = document.createElement('div')
		app.mount(div)

		return {
			title: __('Quiz'),
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		if (Object.keys(this.data).length) {
			this.renderQuiz(
				this.data.quiz,
				this.data.grading_category,
				this.data.due_date,
				this.data.due_time,
				this.data.include_in_grading,
				this.data.checkpoint_quiz
			)
		} else {
			this.renderQuizModal()
		}
		return this.wrapper
	}

	renderQuiz(
		quiz,
		category,
		due_date,
		due_time,
		include_in_grading = true,
		checkpoint_quiz = false
	) {
		if (this.readOnly) {
			const quizPath = getLmsRoute(`quiz/${quiz}?fromLesson=1`)
			this.wrapper.innerHTML = `<iframe src="${quizPath}" class="w-full h-[500px]"></iframe>`
			return
		}
		this.wrapper.innerHTML = `<div class='border rounded-md p-4 text-center bg-surface-menu-bar mb-4'>
			<div class="font-medium">
				Quiz: ${quiz}
			</div>
			${checkpoint_quiz ? `<div class="text-xs text-ink-blue-7 mt-1">${__('Checkpoint Quiz')}</div>` : ''}
			${category ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Category')}: ${category} ${due_date ? `| ${__('Due')}: ${due_date}` : ''} ${due_time ? due_time : ''}</div>` : !include_in_grading ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Not included in grading')}</div>` : ''}
		</div>`
		return
	}

	renderQuizModal() {
		if (this.readOnly) {
			return
		}
		this.api.saver.save().then((outputData) => {
			const currentAssessments = []
			for (const block of outputData.blocks || []) {
				if (block.type === 'quiz' && block.data?.quiz && block.data?.grading_category) {
					currentAssessments.push({
						type: 'quiz',
						id: block.data.quiz,
						category: block.data.grading_category,
					})
				} else if (block.type === 'assignment' && block.data?.assignment && block.data?.grading_category) {
					currentAssessments.push({
						type: 'assignment',
						id: block.data.assignment,
						category: block.data.grading_category,
					})
				}
			}

			const app = createApp(AssessmentPlugin, {
				type: 'quiz',
				courseName: router.currentRoute.value?.params?.courseName,
				allowCheckpointQuiz:
					router.currentRoute.value?.query?.mode !== 'assessment',
				currentAssessments: currentAssessments,
				onAddition: (data) => {
					this.data.quiz = data.item
					this.data.grading_category = data.grading_category
					this.data.include_in_grading = data.include_in_grading
					this.data.checkpoint_quiz = data.checkpoint_quiz
					this.data.due_date = data.due_date
					this.data.due_time = data.due_time
					this.renderQuiz(
						data.item,
						data.grading_category,
						data.due_date,
						data.due_time,
						data.include_in_grading,
						data.checkpoint_quiz
					)
				},
			})
			app.use(translationPlugin)
			app.use(router)
			app.mount(this.wrapper)
		})
	}

	save() {
		if (Object.keys(this.data).length === 0) return {}
		return {
			quiz: this.data.quiz,
			grading_category: this.data.grading_category,
			include_in_grading: this.data.include_in_grading,
			checkpoint_quiz: this.data.checkpoint_quiz,
			due_date: this.data.due_date,
			due_time: this.data.due_time,
		}
	}
}
