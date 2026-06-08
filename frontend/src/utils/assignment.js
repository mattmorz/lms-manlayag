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
			this.renderAssignment(
				this.data.assignment,
				this.data.grading_category,
				this.data.due_date,
				this.data.due_time
			)
		} else {
			this.renderAssignmentModal()
		}
		return this.wrapper
	}

	renderAssignment(assignment, category, due_date, due_time) {
		if (this.readOnly) {
			const { userResource } = usersStore()
			call('frappe.client.get_value', {
				doctype: 'LMS Assignment Submission',
				filters: {
					assignment: assignment,
					member: userResource.data?.name,
				},
				fieldname: ['name'],
			}).then((data) => {
				let submission = data.name || 'new'
				const submissionPath = getLmsRoute(
					`assignment-submission/${assignment}/${submission}?fromLesson=1`
				)
				this.wrapper.innerHTML = `<iframe src="${submissionPath}" class="w-full h-[500px]"></iframe>`
			})
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
					Assignment: ${data.title}
				</div>
				${category ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Category')}: ${category} ${due_date ? `| ${__('Due')}: ${due_date}` : ''} ${due_time ? due_time : ''}</div>` : ''}
			</div>`
			return
		})
	}

	renderAssignmentModal() {
		if (this.readOnly) {
			return
		}
		const app = createApp(AssessmentPlugin, {
			type: 'assignment',
			onAddition: (data) => {
				this.data.assignment = data.item
				this.data.grading_category = data.grading_category
				this.data.due_date = data.due_date
				this.data.due_time = data.due_time
				this.renderAssignment(data.item, data.grading_category, data.due_date, data.due_time)
			},
		})
		app.use(translationPlugin)
		app.use(router)
		app.mount(this.wrapper)
	}

	save() {
		if (Object.keys(this.data).length === 0) return {}
		return {
			assignment: this.data.assignment,
			grading_category: this.data.grading_category,
			due_date: this.data.due_date,
			due_time: this.data.due_time,
		}
	}
}
