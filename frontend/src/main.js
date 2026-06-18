import './index.css'
import { createApp, watch, nextTick } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'
import dayjs from '@/utils/dayjs'
import { createDialog } from '@/utils/dialogs'
import translationPlugin from './translation'
import { usersStore } from './stores/user'
import { initSocket } from './socket'
import { FrappeUI, setConfig, frappeRequest, pageMetaPlugin } from 'frappe-ui'
import { telemetryPlugin } from 'frappe-ui/frappe'

let pinia = createPinia()
let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(FrappeUI)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
app.use(pageMetaPlugin)
app.provide('$dayjs', dayjs)
app.provide('$socket', initSocket())

const { userResource, allUsers } = usersStore()
app.provide('$user', userResource)
app.provide('$allUsers', allUsers)

app.mount('#app')

watch(userResource, () => {
	if (userResource.data) {
		app.use(telemetryPlugin, { app_name: 'lms' })
	}
})

app.config.globalProperties.$user = userResource
app.config.globalProperties.$dialog = createDialog

window.triggerMathJax = (elements) => {
	const runTypeset = () => {
		if (window.MathJax && window.MathJax.typesetPromise) {
			if (elements) {
				const els = Array.isArray(elements) ? elements : [elements]
				const validEls = els.filter((el) => el && el.nodeType)
				if (validEls.length > 0) {
					window.MathJax.typesetClear(validEls)
					window.MathJax.typesetPromise(validEls).catch((err) => console.error(err))
				}
			} else {
				window.MathJax.typesetPromise().catch((err) => console.error(err))
			}
		}
	}

	if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
		window.MathJax.startup.promise.then(runTypeset)
	} else {
		nextTick(() => {
			if (window.MathJax && window.MathJax.typesetPromise) {
				runTypeset()
			} else {
				setTimeout(runTypeset, 500)
			}
		})
	}
}


router.afterEach(() => {
	window.triggerMathJax()
})
