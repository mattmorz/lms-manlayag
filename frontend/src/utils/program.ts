import { createApp, h } from 'vue'
import { Code } from 'lucide-vue-next'
import translationPlugin from '@/translation'
import AssessmentPlugin from '@/components/AssessmentPlugin.vue'
import { call } from 'frappe-ui';
import { usersStore } from '@/stores/user'
import { getLmsRoute } from '@/utils/basePath'
import router from '@/router'


export class Program {

    data: any;
    api: any;
    readOnly: boolean;
    wrapper: HTMLDivElement;

    constructor({ data, api, readOnly }: { data: any; api: any; readOnly: boolean }) {
        this.data = data;
        this.api = api;
        this.readOnly = readOnly;
    }

    static get toolbox() {
        const app = createApp({
            render: () => h(Code, { size: 5, strokeWidth: 1.5 }),
        })

        const div = document.createElement('div')
        app.mount(div)

        return {
            title: __('Programming Exercise'),
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
			this.renderExercise(
				this.data.exercise,
				this.data.grading_category,
				this.data.due_date,
				this.data.due_time,
				include_in_grading
			)
		} else {
			this.renderModal()
		}
		return this.wrapper
	}

    renderModal() {
		if (this.readOnly) {
			return
		}
		this.api.saver.save().then((outputData: any) => {
			const currentAssessments: any[] = []
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
				type: 'program',
				courseName: router.currentRoute.value?.params?.courseName,
				creationMode: router.currentRoute.value?.query?.mode || 'lesson',
				currentAssessments: currentAssessments,
				onAddition: (data: any) => {
					this.data.exercise = data.item
					this.data.grading_category = data.grading_category
					this.data.include_in_grading = data.include_in_grading
					this.data.due_date = data.due_date
					this.data.due_time = data.due_time
					this.renderExercise(
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

    renderExercise(exercise: string, category?: string, due_date?: string, due_time?: string, include_in_grading: boolean = true) {
        if (this.readOnly) {
            const { userResource } = usersStore()
            const querySubmission = () => {
                call('frappe.client.get_value', {
                    doctype: 'LMS Programming Exercise Submission',
                    filters: {
                        exercise: exercise,
                        member: userResource.data?.name,
                    },
                    fieldname: ['name'],
                }).then((data: { name: string } | null) => {
                    let submission = (data && data.name) || 'new'
                    const submissionPath = getLmsRoute(
                        `programming-exercises/${exercise}/submission/${submission}?fromLesson=1` +
                        `${include_in_grading ? '&grading=1' : ''}`
                    )
                    this.wrapper.innerHTML = `<iframe src="${submissionPath}" class="w-full h-[900px] border rounded-md"></iframe>`
                })
            }
            if (userResource && userResource.promise) {
                userResource.promise.then(querySubmission).catch(querySubmission)
            } else {
                querySubmission()
            }
            return
        } 
        call("frappe.client.get_value", {
            doctype: 'LMS Programming Exercise',
            filters: {
                name: exercise
            },
            fieldname: "title"
        }).then((data: { title: string } | null) => {
            this.wrapper.innerHTML = `<div class='border rounded-md p-4 text-center bg-surface-menu-bar mb-4'>
                <span class="font-medium">
                    Programming Exercise: ${data && data.title ? data.title : ''}
                </span>
				${category ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Category')}: ${category} ${due_date ? `| ${__('Due')}: ${due_date}` : ''} ${due_time ? due_time : ''}</div>` : !include_in_grading ? `<div class="text-xs text-ink-gray-6 mt-1">${__('Not included in grading')}</div>` : ''}
            </div>`
            return
        })
    }

    save() {
        if (!this.data.exercise) return {}
		return {
			exercise: this.data.exercise,
			grading_category: this.data.grading_category,
			include_in_grading: this.data.include_in_grading !== undefined ? this.data.include_in_grading : true,
			due_date: this.data.due_date,
			due_time: this.data.due_time,
		}
	}
}
