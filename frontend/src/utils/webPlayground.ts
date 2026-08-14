import { createApp, h } from 'vue'
import { Code } from 'lucide-vue-next'
import translationPlugin from '@/translation'
import AssessmentPlugin from '@/components/AssessmentPlugin.vue'
import WebPlayground from '@/components/WebPlayground/WebPlayground.vue'
import { call } from 'frappe-ui'
import router from '@/router'

export class WebPlaygroundTool {
	data: any
	api: any
	readOnly: boolean
	wrapper: HTMLDivElement

	constructor({ data, api, readOnly }: { data: any; api: any; readOnly: boolean }) {
		this.data = data
		this.api = api
		this.readOnly = readOnly
		this.wrapper = document.createElement('div')
	}

	static get toolbox() {
		const app = createApp({
			render: () => h(Code, { size: 5, strokeWidth: 1.5 }),
		})
		const div = document.createElement('div')
		app.mount(div)

		return {
			title: __('Web Playground'),
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		this.wrapper.className = 'my-4'
		if (Object.keys(this.data).length && this.data.exercise) {
			this.renderExercise(this.data.exercise)
		} else {
			this.renderModal()
		}
		return this.wrapper
	}

	renderModal() {
		if (this.readOnly) return

		this.api.saver.save().then((outputData: any) => {
			const currentAssessments: any[] = []
			for (const block of outputData.blocks || []) {
				if (block.type === 'web_playground' && block.data?.exercise) {
					currentAssessments.push({
						type: 'web_playground',
						id: block.data.exercise,
						category: block.data.grading_category,
					})
				}
			}

			const app = createApp(AssessmentPlugin, {
				type: 'web_playground',
				courseName: router.currentRoute.value?.params?.courseName,
				creationMode: router.currentRoute.value?.query?.mode || 'lesson',
				currentAssessments: currentAssessments,
				onAddition: (data: any) => {
					this.data.exercise = data.item
					this.data.grading_category = data.grading_category
					this.data.include_in_grading = data.include_in_grading
					this.renderExercise(data.item)
				},
			})
			app.use(translationPlugin)
			app.use(router)
			app.mount(this.wrapper)
		})
	}

	renderExercise(exercise: string) {
		if (this.readOnly) {
			const app = createApp(WebPlayground, {
				exerciseId: exercise,
			})
			app.use(translationPlugin)
			app.mount(this.wrapper)
			return
		}

		call('frappe.client.get_value', {
			doctype: 'LMS Web Playground Exercise',
			filters: { name: exercise },
			fieldname: 'title',
		}).then((data: { title: string } | null) => {
			this.wrapper.innerHTML = `<div class="border rounded-md p-4 text-center bg-surface-menu-bar mb-4">
				<span class="font-medium">
					Web Playground: ${data && data.title ? data.title : exercise}
				</span>
			</div>`
		})
	}

	save() {
		if (!this.data.exercise) return {}
		return {
			exercise: this.data.exercise,
			grading_category: this.data.grading_category,
			include_in_grading: this.data.include_in_grading !== undefined ? this.data.include_in_grading : true,
		}
	}
}
