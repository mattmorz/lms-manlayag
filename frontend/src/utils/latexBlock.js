import { Sigma } from 'lucide-vue-next'
import { createApp, h } from 'vue'

export class LatexBlock {
	constructor({ data, api, readOnly, config }) {
		this.api = api
		this.readOnly = readOnly
		this.data = {
			formula: data.formula || '',
		}
		this.wrapper = null
		this.previewContainer = null
		this.inputElement = null
	}

	static get isReadOnlySupported() {
		return true
	}

	static get conversionConfig() {
		return {
			export: 'formula',
			import: (text) => {
				// Strip HTML tags and decode HTML entities to get clean LaTeX
				const temp = document.createElement('div')
				temp.innerHTML = text
				return {
					formula: temp.textContent || temp.innerText || '',
				}
			},
		}
	}

	static get toolbox() {
		const app = createApp({
			render: () =>
				h(Sigma, { size: 18, strokeWidth: 1.8, color: 'black' }),
		})

		const div = document.createElement('div')
		app.mount(div)
		return { title: 'LaTeX Math', icon: div.innerHTML }
	}

	render() {
		this.wrapper = document.createElement('div')
		this.wrapper.classList.add('latex-block-wrapper', 'py-2')

		if (this.readOnly) {
			const displayDiv = document.createElement('div')
			displayDiv.classList.add('latex-display-view', 'text-center', 'my-3', 'text-lg', 'overflow-x-auto')
			// Render display equation
			displayDiv.innerHTML = `$$\n${this.data.formula}\n$$`
			this.wrapper.appendChild(displayDiv)
			// Trigger MathJax after this wrapper is added to the DOM
			setTimeout(() => {
				if (window.triggerMathJax) {
					window.triggerMathJax(displayDiv)
				}
			}, 100)
		} else {
			// Editing mode
			// 1. Preview element
			this.previewContainer = document.createElement('div')
			this.previewContainer.classList.add(
				'latex-preview-container',
				'border',
				'border-dashed',
				'border-outline-gray-3',
				'rounded-md',
				'p-4',
				'bg-surface-gray-2',
				'text-center',
				'cursor-pointer',
				'min-h-[3rem]',
				'flex',
				'items-center',
				'justify-center',
				'text-base'
			)
			this.updatePreview()

			// 2. Input/textarea element
			this.inputElement = document.createElement('textarea')
			this.inputElement.classList.add(
				'latex-input-editor',
				'w-full',
				'font-mono',
				'text-sm',
				'p-2.5',
				'border',
				'border-outline-gray-3',
				'rounded-md',
				'outline-none',
				'focus:border-outline-gray-4',
				'resize-y',
				'min-h-[5rem]'
			)
			this.inputElement.value = this.data.formula
			this.inputElement.placeholder = 'Enter LaTeX (e.g. \\sum_{i=1}^n i = \\frac{n(n+1)}{2})'
			this.inputElement.style.display = this.data.formula ? 'none' : 'block'

			if (this.data.formula) {
				this.previewContainer.style.display = 'flex'
			} else {
				this.previewContainer.style.display = 'none'
			}

			// Add event listeners
			this.api.listeners.on(this.previewContainer, 'click', () => {
				this.previewContainer.style.display = 'none'
				this.inputElement.style.display = 'block'
				this.inputElement.focus()
			})

			const handleBlur = () => {
				this.data.formula = this.inputElement.value.trim()
				this.updatePreview()
				if (this.data.formula) {
					this.inputElement.style.display = 'none'
					this.previewContainer.style.display = 'flex'
				}
			}

			this.api.listeners.on(this.inputElement, 'blur', handleBlur)

			this.wrapper.appendChild(this.previewContainer)
			this.wrapper.appendChild(this.inputElement)

			// Helper notice
			const notice = document.createElement('div')
			notice.classList.add('text-xs', 'text-ink-gray-5', 'mt-1', 'px-1')
			notice.innerText = 'LaTeX equation (Click preview to edit, blur to save)'
			this.wrapper.appendChild(notice)
		}

		return this.wrapper
	}

	updatePreview() {
		if (this.previewContainer) {
			if (this.data.formula) {
				this.previewContainer.innerHTML = `$$\n${this.data.formula}\n$$`
				this.previewContainer.classList.remove('italic', 'text-ink-gray-5')
				// Trigger typesetting on the preview container
				setTimeout(() => {
					if (window.triggerMathJax) {
						window.triggerMathJax(this.previewContainer)
					}
				}, 50)
			} else {
				this.previewContainer.innerHTML = '<i>Click to edit LaTeX math</i>'
				this.previewContainer.classList.add('italic', 'text-ink-gray-5')
			}
		}
	}

	save(blockContent) {
		const input = blockContent.querySelector('.latex-input-editor')
		if (input) {
			this.data.formula = input.value.trim()
		}
		return {
			formula: this.data.formula,
		}
	}

	validate(savedData) {
		return true
	}
}

export default LatexBlock
