import { Pencil } from 'lucide-vue-next'
import { createApp, h } from 'vue'
import AssessmentPlugin from '@/components/AssessmentPlugin.vue'
import translationPlugin from '../translation'
import { usersStore } from '@/stores/user'
import { call } from 'frappe-ui'
import router from '@/router'
import { getLmsRoute } from '@/utils/basePath'

export class Assignment {
	constructor({ data, api, readOnly }) {
		this.data = data
		this.api = api
		this.readOnly = readOnly
	}

	static get toolbox() {
		const app = createApp({
			render: () =>
				h(Pencil, { size: 18, strokeWidth: 1.5, color: 'black' }),
		})

		const div = document.createElement('div')
		app.mount(div)

		return {
			title: __('Assignment'),
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		if (Object.keys(this.data).length) {
			const include_in_grading = this.data.include_in_grading !== undefined ? this.data.include_in_grading : true
			this.renderAssignment(
				this.data.assignment,
				this.data.grading_category,
				this.data.due_date,
				this.data.due_time,
				include_in_grading
			)
		} else {
			this.renderAssignmentModal()
		}
		return this.wrapper
	}

	renderAssignment(assignment, category, due_date, due_time, include_in_grading = true) {
		if (this.readOnly) {
			const { userResource } = usersStore()
			const querySubmission = () => {
				call('frappe.client.get_value', {
					doctype: 'LMS Assignment Submission',
					filters: {
						assignment: assignment,
						member: userResource.data?.name,
					},
					fieldname: ['name'],
				}).then((data) => {
					let submission = (data && data.name) || 'new'
					const submissionPath = getLmsRoute(
						`assignment-submission/${assignment}/${submission}?fromLesson=1` +
						`${include_in_grading ? '&grading=1' : ''}`
					)
					this.wrapper.innerHTML = `<iframe src="${submissionPath}" class="w-full h-[500px]"></iframe>`
				})
			}
			if (userResource && userResource.promise) {
				userResource.promise.then(querySubmission).catch(querySubmission)
			} else {
				querySubmission()
			}
			return
		}
		call('frappe.client.get_value', {
			doctype: 'LMS Assignment',
			filters: {
				name: assignment,
			},
			fieldname: ['title'],
		}).then((data) => {
			this.wrapper.innerHTML = `<div class='border rounded-md p-4 text-center bg-surface-menu-bar mb-4'>
				<div class="font-medium">
					Assignment: ${data && data.title ? data.title : ''}
				</div>
				${category ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Category')}: ${category} ${due_date ? `| ${__('Due')}: ${due_date}` : ''} ${due_time ? due_time : ''}</div>` : !include_in_grading ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Not included in grading')}</div>` : ''}
			</div>`
			return
		})
	}

	renderAssignmentModal() {
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
				} else if (block.type === 'program' && block.data?.exercise && block.data?.grading_category) {
					currentAssessments.push({
						type: 'program',
						id: block.data.exercise,
						category: block.data.grading_category,
					})
				}
			}

			const app = createApp(AssessmentPlugin, {
				type: 'assignment',
				courseName: router.currentRoute.value?.params?.courseName,
				creationMode: router.currentRoute.value?.query?.mode || 'lesson',
				currentAssessments: currentAssessments,
				onAddition: (data) => {
					this.data.assignment = data.item
					this.data.grading_category = data.grading_category
					this.data.include_in_grading = data.include_in_grading
					this.data.due_date = data.due_date
					this.data.due_time = data.due_time
					this.renderAssignment(
						data.item,
						data.grading_category,
						data.due_date,
						data.due_time,
						data.include_in_grading
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
			assignment: this.data.assignment,
			grading_category: this.data.grading_category,
			include_in_grading: this.data.include_in_grading !== undefined ? this.data.include_in_grading : true,
			due_date: this.data.due_date,
			due_time: this.data.due_time,
		}
	}
}
