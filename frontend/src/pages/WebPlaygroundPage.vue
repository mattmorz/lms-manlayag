<template>
	<div class="p-6 max-w-7xl mx-auto space-y-6 font-sans text-ink-gray-9">
		<!-- Header -->
		<div class="flex items-center justify-between flex-wrap gap-4 border-b border-outline-gray-2 pb-4">
			<div>
				<h1 class="text-2xl font-black tracking-tight text-ink-gray-9 flex items-center gap-2.5">
					<Code2 class="size-7 text-blue-600" />
					<span>{{ __('Web Playground') }}</span>
				</h1>
				<p class="text-sm text-ink-gray-6 mt-1">
					{{ __('Experiment, build, and run HTML, CSS, and JavaScript code in a live sandboxed environment.') }}
				</p>
			</div>

			<!-- Template Presets Selector -->
			<div class="flex items-center space-x-2">
				<label class="text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
					{{ __('Template Presets:') }}
				</label>
				<select
					v-model="selectedPreset"
					class="text-xs border border-outline-gray-3 rounded-md px-2.5 py-1.5 bg-surface-white font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none"
					@change="loadPreset"
				>
					<option value="default">{{ __('Default Starter') }}</option>
					<option value="card">{{ __('HTML/CSS Card Component') }}</option>
					<option value="flexbox">{{ __('Flexbox Layout Grid') }}</option>
					<option value="counter">{{ __('Interactive JS Counter') }}</option>
				</select>
			</div>
		</div>

		<!-- Standalone Playground Component -->
		<WebPlayground ref="playgroundRef" />
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { Code2 } from 'lucide-vue-next'
import WebPlayground from '@/components/WebPlayground/WebPlayground.vue'

const selectedPreset = ref('default')
const playgroundRef = ref(null)

const presets = {
	default: {
		html: `<h1>Hello, Manlayag!</h1>\n\n<p>Welcome to the Web Playground.</p>\n\n<button id="demoButton">Click Me</button>`,
		css: `body {\n    font-family: Arial, sans-serif;\n    padding: 2rem;\n}\n\nh1 {\n    margin-bottom: 0.5rem;\n    color: #1e40af;\n}\n\nbutton {\n    padding: 0.5rem 1rem;\n    background: #2563eb;\n    color: white;\n    border: none;\n    border-radius: 0.375rem;\n    cursor: pointer;\n}`,
		js: `document.getElementById("demoButton").addEventListener("click", () => {\n    alert("Hello from Manlayag!");\n});`,
	},
	card: {
		html: `<div class="card">\n    <img src="https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=500" alt="Code">\n    <div class="card-body">\n        <h3>Web Development</h3>\n        <p>Learn HTML, CSS, and JavaScript interactively.</p>\n        <button>Explore Course</button>\n    </div>\n</div>`,
		css: `.card {\n    max-width: 320px;\n    border: 1px solid #e5e7eb;\n    border-radius: 0.75rem;\n    overflow: hidden;\n    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);\n}\n\n.card img {\n    width: 100%;\n    height: 180px;\n    object-fit: cover;\n}\n\n.card-body {\n    padding: 1.25rem;\n}\n\n.card-body h3 {\n    margin: 0 0 0.5rem 0;\n    font-size: 1.25rem;\n}\n\n.card-body p {\n    color: #4b5563;\n    font-size: 0.875rem;\n    line-height: 1.4;\n}\n\n.card-body button {\n    width: 100%;\n    margin-top: 1rem;\n    padding: 0.6rem;\n    background-color: #10b981;\n    color: white;\n    border: none;\n    border-radius: 0.375rem;\n    font-weight: bold;\n    cursor: pointer;\n}`,
		js: `document.querySelector(".card button").addEventListener("click", () => {\n    alert("Enrolling in Web Development!");\n});`,
	},
	flexbox: {
		html: `<div class="container">\n    <div class="box">Item 1</div>\n    <div class="box">Item 2</div>\n    <div class="box">Item 3</div>\n</div>`,
		css: `.container {\n    display: flex;\n    gap: 1rem;\n    justify-content: center;\n    align-items: center;\n    min-height: 200px;\n    background-color: #f3f4f6;\n    border-radius: 0.5rem;\n}\n\n.box {\n    background: #8b5cf6;\n    color: white;\n    padding: 1.5rem;\n    font-weight: bold;\n    border-radius: 0.5rem;\n}`,
		js: `// Click any box to highlight it\ndocument.querySelectorAll(".box").forEach(box => {\n    box.addEventListener("click", () => {\n        box.style.background = "#ec4899";\n    });\n});`,
	},
	counter: {
		html: `<div class="counter-box">\n    <h2>Counter App</h2>\n    <div id="count">0</div>\n    <div class="buttons">\n        <button id="decrement">-</button>\n        <button id="reset">Reset</button>\n        <button id="increment">+</button>\n    </div>\n</div>`,
		css: `body {\n    display: flex;\n    justify-content: center;\n    align-items: center;\n    height: 100vh;\n    margin: 0;\n    font-family: sans-serif;\n}\n\n.counter-box {\n    text-align: center;\n    padding: 2rem;\n    border: 1px solid #d1d5db;\n    border-radius: 1rem;\n    background: #ffffff;\n}\n\n#count {\n    font-size: 3rem;\n    font-weight: bold;\n    margin: 1rem 0;\n    color: #1f2937;\n}\n\n.buttons button {\n    padding: 0.5rem 1rem;\n    font-size: 1.2rem;\n    margin: 0 0.25rem;\n    cursor: pointer;\n}`,
		js: `let count = 0;\nconst countEl = document.getElementById("count");\n\ndocument.getElementById("increment").onclick = () => {\n    count++;\n    countEl.textContent = count;\n};\n\ndocument.getElementById("decrement").onclick = () => {\n    count--;\n    countEl.textContent = count;\n};\n\ndocument.getElementById("reset").onclick = () => {\n    count = 0;\n    countEl.textContent = count;\n};`,
	},
}

const loadPreset = () => {
	const preset = presets[selectedPreset.value] || presets.default
	if (playgroundRef.value) {
		playgroundRef.value.htmlCode = preset.html
		playgroundRef.value.cssCode = preset.css
		playgroundRef.value.jsCode = preset.js
		playgroundRef.value.runCode()
	}
}
</script>
