import EmbedTool from '@editorjs/embed'
import EmbedVideoBlock from '@/components/EmbedVideoBlock.vue'
import { createApp } from 'vue'
import translationPlugin from '../translation'
import { createDialog } from '@/utils/dialogs'

export class CustomEmbed {
	constructor({ data, api, readOnly, config }) {
		this.data = data || {}
		this.api = api
		this.readOnly = readOnly
		this.config = config
		this.embedTool = new EmbedTool({ data, api, readOnly, config })
		this.resolveServiceFromSource()
	}

	static get toolbox() {
		return EmbedTool.toolbox
	}

	static get isReadOnlySupported() {
		return true
	}

	static get conversionConfig() {
		return {
			import: 'source',
			export: 'source'
		}
	}

	static get pasteConfig() {
		return EmbedTool.pasteConfig
	}

	static get sanitize() {
		return EmbedTool.sanitize
	}

	static prepare(options) {
		EmbedTool.prepare(options)
	}

	resolveServiceFromSource() {
		if (this.data && this.data.source && !this.data.service) {
			const source = this.data.source.trim()
			const services = EmbedTool.services || {}
			for (const [name, service] of Object.entries(services)) {
				const match = service.regex.exec(source)
				if (match) {
					const idFn = service.id || ((c) => c.shift())
					const matchedGroups = match.slice(1)
					const remoteId = idFn(matchedGroups)
					const embedUrl = service.embedUrl.replace(/<%= remote_id %>/g, remoteId)
					
					this.data.service = name
					this.data.embed = embedUrl
					this.data.width = service.width
					this.data.height = service.height
					
					this.embedTool.data = {
						service: name,
						source: source,
						embed: embedUrl,
						width: service.width,
						height: service.height,
						caption: this.data.caption || ''
					}
					break
				}
			}
		}
	}

	render() {
		const isVideoService = this.data && (this.data.service === 'youtube' || this.data.service === 'vimeo')
		if (isVideoService) {
			this.wrapper = document.createElement('div')
			this.wrapper.className = 'custom-video-embed-wrapper w-full'
			
			const app = createApp(EmbedVideoBlock, {
				data: this.data,
				readOnly: this.readOnly,
				saveQuizzes: (quizzes) => {
					if (this.readOnly) return
					this.data.quizzes = quizzes
				},
			})
			app.use(translationPlugin)
			app.config.globalProperties.$dialog = createDialog
			app.mount(this.wrapper)
			return this.wrapper
		}

		return this.embedTool.render()
	}

	save(blockContent) {
		const isVideoService = this.data && (this.data.service === 'youtube' || this.data.service === 'vimeo')
		if (isVideoService) {
			return {
				service: this.data.service,
				source: this.data.source,
				embed: this.data.embed,
				width: this.data.width,
				height: this.data.height,
				caption: this.data.caption || '',
				quizzes: this.data.quizzes || [],
			}
		}
		return this.embedTool.save(blockContent)
	}

	validate(savedData) {
		if (savedData && (savedData.service === 'youtube' || savedData.service === 'vimeo')) {
			return !!savedData.embed
		}
		return this.embedTool.validate ? this.embedTool.validate(savedData) : true
	}
}
