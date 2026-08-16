import { Code } from "lucide-vue-next"
import { h, createApp } from "vue"
import hljs from 'highlight.js/lib/core';


const DEFAULT_THEMES = ['light', 'dark'];
const COMMON_LANGUAGES = {
	none: 'Auto-detect', apache: 'Apache', bash: 'Bash', cs: 'C#', cpp: 'C++', css: 'CSS', coffeescript: 'CoffeeScript', diff: 'Diff',
	go: 'Go', html: 'HTML, XML', http: 'HTTP', json: 'JSON', java: 'Java', javascript: 'JavaScript', kotlin: 'Kotlin',
	less: 'Less', lua: 'Lua', makefile: 'Makefile', markdown: 'Markdown', nginx: 'Nginx', objectivec: 'Objective-C',
	php: 'PHP', perl: 'Perl', properties: 'Properties', python: 'Python', ruby: 'Ruby', rust: 'Rust', scss: 'SCSS',
	sql: 'SQL', shell: 'Shell Session', swift: 'Swift', toml: 'TOML, also INI', typescript: 'TypeScript', yaml: 'YAML',
	plaintext: 'Plaintext'
};

export class CodeBox {
	api: any;
	config: { themeName: any; themeURL: any; useDefaultTheme: any; };
	readOnly: boolean;
	previewToggleButton: HTMLButtonElement;
	previewContainer: HTMLDivElement;
	isPreviewMode: boolean;

	constructor({ data, api, config, readOnly }) {
		this.api = api;
		this.readOnly = readOnly;
		this.config = {
			themeName: config.themeName && typeof config.themeName === 'string' ? config.themeName : '',
			themeURL: config.themeURL && typeof config.themeURL === 'string' ? config.themeURL : '',
			useDefaultTheme: (config.useDefaultTheme && typeof config.useDefaultTheme === 'string'
				&& DEFAULT_THEMES.includes(config.useDefaultTheme.toLowerCase())) ? config.useDefaultTheme : 'light',
		};
		this.data = {
			code: data.code && typeof data.code === 'string' ? data.code : '',
			language: data.language && typeof data.language === 'string' ? data.language : 'none',
			theme: data.theme && typeof data.theme === 'string' && DEFAULT_THEMES.includes(data.theme)
				? data.theme
				: this.config.useDefaultTheme,
		};
		this.highlightScriptID = 'highlightJSScriptElement';
		this.highlightCSSID = 'highlightJSCSSElement';
		this.codeArea = document.createElement('div');
		this.selectInput = document.createElement('input');
		this.selectDropIcon = document.createElement('i');
		this.themeToggleButton = document.createElement('button');
		this.previewToggleButton = document.createElement('button');
		this.previewContainer = document.createElement('div');
		this.isPreviewMode = false;

		this._injectHighlightJSCSSElement();

		this.api.listeners.on(window, 'click', this._closeAllLanguageSelects, true);
	}

	static get isReadOnlySupported() {
		return true
	}

	static get sanitize() {
		return {
			code: true,
			language: false,
			theme: false,
		}
	}

	static get toolbox() {
		const app = createApp({
			render: () => h(Code, { size: 18, strokeWidth: 1.5, color: 'black' }),
		});

		const div = document.createElement('div');
		app.mount(div);

		return {
			title: 'CodeBox',
			icon: div.innerHTML
		};
	}

	static get displayInToolbox() {
		return true;
	}

	static get enableLineBreaks() {
		return true;
	}

	render() {
		const codeAreaHolder = document.createElement('pre');
		const languageSelect = this._createLanguageSelectElement();
		const themeToggle = this._createThemeToggleElement();
		const previewToggle = this._createPreviewToggleElement();
		const controlsHolder = document.createElement('div');

		codeAreaHolder.setAttribute('class', 'codeBoxHolder relative');
		this._applyCodeAreaClass();
		this.codeArea.setAttribute('contenteditable', this.readOnly ? 'false' : 'true');
		this.codeArea.style.whiteSpace = 'pre-wrap';
		this.codeArea.style.wordBreak = 'break-word';
		this.codeArea.textContent = this.data.code;
		this.api.listeners.on(this.codeArea, 'blur', event => this._highlightCodeArea(event), false);
		this.api.listeners.on(this.codeArea, 'paste', event => this._handleCodeAreaPaste(event), false);

		this.previewContainer.setAttribute('class', 'codeBoxPreviewArea hidden p-4 bg-white text-black border rounded-md my-2 overflow-auto');
		this.previewContainer.style.display = 'none';

		controlsHolder.setAttribute('class', 'codeBoxControls flex items-center space-x-2');
		controlsHolder.appendChild(languageSelect);
		controlsHolder.appendChild(themeToggle);
		controlsHolder.appendChild(previewToggle);

		codeAreaHolder.appendChild(this.codeArea);
		codeAreaHolder.appendChild(this.previewContainer);
		codeAreaHolder.appendChild(controlsHolder);

		this._updatePreviewButtonVisibility();

		return codeAreaHolder;
	}

	_getRawCode() {
		let html = this.codeArea.innerHTML || '';
		html = html.replace(/<br\s*\/?>/gi, '\n');
		html = html.replace(/<\/div>/gi, '\n');
		html = html.replace(/<div>/gi, '');
		html = html.replace(/<\/p>/gi, '\n');
		html = html.replace(/<p>/gi, '');

		const txt = document.createElement('textarea');
		txt.innerHTML = html;
		return txt.value;
	}

	save(blockContent) {
		return Object.assign(this.data, {
			code: this._getRawCode(),
			theme: this.data.theme,
			language: this.data.language
		});
	}

	validate(savedData) {
		if (!savedData.code.trim()) return false;
		return true;
	}

	destroy() {
		this.api.listeners.off(window, 'click', this._closeAllLanguageSelects, true);
		this.api.listeners.off(this.codeArea, 'blur', event => this._highlightCodeArea(event), false);
		this.api.listeners.off(this.codeArea, 'paste', event => this._handleCodeAreaPaste(event), false);
		this.api.listeners.off(this.selectInput, 'click', event => this._handleSelectInputClick(event), false);
		this.api.listeners.off(this.themeToggleButton, 'click', event => this._handleThemeToggleClick(event), false);
		this.api.listeners.off(this.previewToggleButton, 'click', event => this._handlePreviewToggleClick(event), false);
	}

	_createLanguageSelectElement() {
		const selectHolder = document.createElement('div');
		const selectPreview = document.createElement('div');
		const languages = Object.entries(COMMON_LANGUAGES);

		selectHolder.setAttribute('class', 'codeBoxSelectDiv');

		this.selectDropIcon.setAttribute('class', `codeBoxSelectDropIcon ${this.data.theme}`);
		this.selectDropIcon.innerHTML = '&#8595;';
		this.selectInput.setAttribute('class', `codeBoxSelectInput ${this.data.theme}`);
		this.selectInput.setAttribute('type', 'text');
		this.selectInput.setAttribute('readonly', 'true');
		this.selectInput.value = COMMON_LANGUAGES[this.data.language] || COMMON_LANGUAGES.none;
		this.api.listeners.on(this.selectInput, 'click', event => this._handleSelectInputClick(event), false);

		selectPreview.setAttribute('class', 'codeBoxSelectPreview');

		languages.forEach(language => {
			const selectItem = document.createElement('p');
			selectItem.setAttribute('class', `codeBoxSelectItem ${this.data.theme}`);
			selectItem.setAttribute('data-key', language[0]);
			selectItem.textContent = language[1];
			this.api.listeners.on(selectItem, 'click', event => this._handleSelectItemClick(event, language), false);

			selectPreview.appendChild(selectItem);
		});

		selectHolder.appendChild(this.selectDropIcon);
		selectHolder.appendChild(this.selectInput);
		selectHolder.appendChild(selectPreview);

		return selectHolder;
	}

	_createThemeToggleElement() {
		this.themeToggleButton.setAttribute('type', 'button');
		this.themeToggleButton.setAttribute('class', 'codeBoxThemeToggle');
		this.themeToggleButton.textContent = this.data.theme === 'light' ? 'Light' : 'Dark';
		this.api.listeners.on(this.themeToggleButton, 'click', event => this._handleThemeToggleClick(event), false);

		return this.themeToggleButton;
	}

	_createPreviewToggleElement() {
		this.previewToggleButton.setAttribute('type', 'button');
		this.previewToggleButton.setAttribute('class', 'codeBoxThemeToggle codeBoxPreviewToggle');
		this.previewToggleButton.textContent = 'Preview HTML';
		this.api.listeners.on(this.previewToggleButton, 'click', event => this._handlePreviewToggleClick(event), false);

		return this.previewToggleButton;
	}

	_updatePreviewButtonVisibility() {
		const lang = (this.data.language || '').toLowerCase();
		const rawCode = this._getRawCode();
		const isHtml = lang === 'html' || (lang === 'none' && /<[a-z][\s\S]*>/i.test(rawCode));

		if (isHtml) {
			this.previewToggleButton.style.display = 'inline-block';
		} else {
			this.previewToggleButton.style.display = 'none';
			if (this.isPreviewMode) {
				this.isPreviewMode = false;
				this.codeArea.style.display = 'block';
				this.previewContainer.style.display = 'none';
				this.previewToggleButton.textContent = 'Preview HTML';
			}
		}
	}

	_handlePreviewToggleClick(event) {
		event.preventDefault();
		this.isPreviewMode = !this.isPreviewMode;
		if (this.isPreviewMode) {
			const rawCode = this._getRawCode();
			this.previewContainer.innerHTML = rawCode;
			this.codeArea.style.display = 'none';
			this.previewContainer.style.display = 'block';
			this.previewToggleButton.textContent = 'View Code';
		} else {
			this.codeArea.style.display = 'block';
			this.previewContainer.style.display = 'none';
			this.previewToggleButton.textContent = 'Preview HTML';
		}
	}

	_highlightCodeArea(event) {
		this._updatePreviewButtonVisibility();
		hljs.highlightBlock(this.codeArea);
	}

	_handleCodeAreaPaste(event) {
		event.stopPropagation();
	}

	_handleSelectInputClick(event) {
		event.target.nextSibling.classList.toggle('codeBoxShow');
	}

	_handleSelectItemClick(event, language) {
		event.target.parentNode.parentNode.querySelector('.codeBoxSelectInput').value = language[1];
		event.target.parentNode.classList.remove('codeBoxShow');
		this.data.language = language[0];
		this._applyCodeAreaClass();
		this._updatePreviewButtonVisibility();

		hljs.highlightElement(this.codeArea);
	}

	_handleThemeToggleClick(event) {
		event.preventDefault();
		this.data.theme = this.data.theme === 'light' ? 'dark' : 'light';
		localStorage.setItem('lms-code-highlight-theme', this.data.theme);
		this.themeToggleButton.textContent = this.data.theme === 'light' ? 'Light' : 'Dark';
		this._applyControlThemeClass();
		this._applyCodeAreaClass();
		this._injectHighlightJSCSSElement();
		delete this.codeArea.dataset.highlighted;
		hljs.highlightElement(this.codeArea);
	}

	_applyCodeAreaClass() {
		this.codeArea.setAttribute('class', `codeBoxTextArea ${this.data.theme} ${this.data.language}`);
	}

	_applyControlThemeClass() {
		this.selectInput.setAttribute('class', `codeBoxSelectInput ${this.data.theme}`);
		this.selectDropIcon.setAttribute('class', `codeBoxSelectDropIcon ${this.data.theme}`);

		const selectHolder = this.selectInput.parentElement;
		const items = selectHolder ? selectHolder.querySelectorAll('.codeBoxSelectItem') : [];
		items.forEach((item) => {
			item.classList.remove('light', 'dark');
			item.classList.add(this.data.theme);
		});
	}

	_closeAllLanguageSelects() {
		const selectPreviews = document.querySelectorAll('.codeBoxSelectPreview');
		for (let i = 0, len = selectPreviews.length; i < len; i++) selectPreviews[i].classList.remove('codeBoxShow');
	}

	_injectHighlightJSCSSElement() {
		const highlightJSCSSElement = document.querySelector(`#${this.highlightCSSID}`);
		let highlightJSCSSURL = this._getThemeURLFromConfig();
		if (!highlightJSCSSElement) {
			const link = document.createElement('link');
			const head = document.querySelector('head');
			link.setAttribute('rel', 'stylesheet');
			link.setAttribute('href', highlightJSCSSURL);
			link.setAttribute('id', this.highlightCSSID);

			if (head) head.appendChild(link);
		}
		else highlightJSCSSElement.setAttribute('href', highlightJSCSSURL);
	}

	_getThemeURLFromConfig() {
		const currentTheme = localStorage.getItem('lms-code-highlight-theme') || this.data.theme || this.config.useDefaultTheme;
		let themeURL = `https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@9.18.1/build/styles/atom-one-${currentTheme}.min.css`;

		if (this.config.themeName) themeURL = `https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@9.18.1/build/styles/${this.config.themeName}.min.css`;
		if (this.config.themeURL) themeURL = this.config.themeURL;

		return themeURL;
	}
}


export default CodeBox;