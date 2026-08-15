/**
 * Web Playground DOM Test Runner & Utilities
 * Evaluates predefined test assertions against a sandboxed iframe Document.
 */

export function runDomTests(iframeDocument, testCases = []) {
	if (!iframeDocument) {
		return {
			passed: false,
			score: 0,
			totalPoints: 0,
			percentage: 0,
			results: [],
		}
	}

	let earnedPoints = 0
	let totalPoints = 0
	let allRequiredPassed = true
	const results = []

	for (const tc of testCases) {
		const points = parseInt(tc.points, 10) || 10
		totalPoints += points

		let testPassed = false
		let detailMessage = ''

		try {
			const selector = tc.selector || ''
			const elem = selector ? iframeDocument.querySelector(selector) : null
			const elements = selector ? iframeDocument.querySelectorAll(selector) : []

			switch (tc.test_type) {
				case 'Element Exists':
					testPassed = elem !== null
					detailMessage = testPassed
						? `Element '${selector}' exists`
						: `Element '${selector}' was not found`
					break

				case 'Element Does Not Exist':
					testPassed = elem === null
					detailMessage = testPassed
						? `Element '${selector}' does not exist`
						: `Element '${selector}' should not exist`
					break

				case 'Text Content':
					if (!elements.length) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const expectedText = (tc.expected_text || tc.expected_value || '').trim().toLowerCase()
						const matchedElem = Array.from(elements).find(el => (el.textContent || '').trim().toLowerCase().includes(expectedText))
						testPassed = !!matchedElem
						detailMessage = testPassed
							? `Element '${selector}' contains text '${tc.expected_text || tc.expected_value}'`
							: `Expected text '${tc.expected_text || tc.expected_value}' in '${selector}'`
					}
					break

				case 'CSS Property':
					if (!elements.length) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const win = iframeDocument.defaultView || window
						const propName = tc.property || ''
						const expectedVal = (tc.expected_value || '').trim().toLowerCase()
						const matchedElem = Array.from(elements).find(el => {
							const computedStyle = win.getComputedStyle(el)
							const actualVal = (computedStyle.getPropertyValue(propName) || computedStyle[propName] || '').trim().toLowerCase()
							return actualVal.includes(expectedVal)
						})
						testPassed = !!matchedElem
						detailMessage = testPassed
							? `CSS property '${propName}' matches '${tc.expected_value}'`
							: `CSS property '${propName}' does not match '${tc.expected_value}' on '${selector}'`
					}
					break

				case 'Attribute':
					if (!elements.length) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const attrName = tc.property || ''
						const expectedAttr = (tc.expected_value || '').trim().toLowerCase()
						const matchedElem = Array.from(elements).find(el => {
							const actualAttr = (el.getAttribute(attrName) || '').toLowerCase()
							return !expectedAttr || actualAttr.includes(expectedAttr)
						})
						testPassed = !!matchedElem
						detailMessage = testPassed
							? `Attribute '${attrName}' matches '${expectedAttr}'`
							: `Attribute '${attrName}' missing or invalid on '${selector}'`
					}
					break

				case 'Element Count':
					const actualCount = elements.length
					const expectedCount = parseInt(tc.expected_value, 10) || 0
					testPassed = actualCount >= expectedCount
					detailMessage = testPassed
						? `Found ${actualCount} matching element(s) for '${selector}'`
						: `Expected at least ${expectedCount} elements for '${selector}', found ${actualCount}`
					break

				case 'Input Value':
					if (!elements.length) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const expectedVal = (tc.expected_value || '').trim()
						const matchedElem = Array.from(elements).find(el => (el.value || '').trim() === expectedVal)
						testPassed = !!matchedElem
						detailMessage = testPassed
							? `Input value matches '${expectedVal}'`
							: `Input value '${expectedVal}' not found on '${selector}'`
					}
					break

				case 'Class Exists':
					if (!elements.length) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const className = (tc.expected_value || tc.property || '').trim()
						const matchedElem = Array.from(elements).find(el => el.classList.contains(className))
						testPassed = !!matchedElem
						detailMessage = testPassed
							? `Class '${className}' exists on '${selector}'`
							: `Class '${className}' missing on '${selector}'`
					}
					break

				case 'Class Does Not Exist':
					if (!elements.length) {
						testPassed = true
						detailMessage = `Element '${selector}' not found`
					} else {
						const className = (tc.expected_value || tc.property || '').trim()
						const hasClass = Array.from(elements).some(el => el.classList.contains(className))
						testPassed = !hasClass
						detailMessage = testPassed
							? `Class '${className}' is absent on '${selector}'`
							: `Class '${className}' should not exist on '${selector}'`
					}
					break

				default:
					testPassed = false
					detailMessage = `Unknown test type '${tc.test_type}'`
					break
			}
		} catch (err) {
			testPassed = false
			detailMessage = `Error evaluating test: ${err.message}`
		}

		if (testPassed) {
			earnedPoints += points
		} else if (tc.required) {
			allRequiredPassed = false
		}

		results.push({
			title: tc.title || `Test: ${tc.test_type}`,
			description: tc.description || '',
			test_type: tc.test_type,
			points: points,
			earned_points: testPassed ? points : 0,
			passed: testPassed,
			required: !!tc.required,
			message: detailMessage,
		})
	}

	const percentage = totalPoints > 0 ? Math.round((earnedPoints / totalPoints) * 100) : 100
	const finalPassed = allRequiredPassed && percentage >= 70

	return {
		passed: finalPassed,
		score: percentage,
		earnedPoints,
		totalPoints,
		results,
	}
}

/**
 * Combines HTML, CSS, and JS into a complete sandboxed document string.
 * Injects a lightweight console capturer that sends console logs back via postMessage.
 */
export function buildSandboxedDocument(html = '', css = '', js = '', options = {}) {
	const allowConsole = options.allowConsole !== false
	const allowJs = options.allowJs !== false

	const consoleScript = allowConsole ? `
<script>
(function() {
	function sendLog(type, args) {
		try {
			var msg = Array.prototype.slice.call(args).map(function(item) {
				if (typeof item === 'object') {
					try { return JSON.stringify(item); } catch(e) { return String(item); }
				}
				return String(item);
			}).join(' ');
			parent.postMessage({ type: 'web_playground_console', logType: type, message: msg }, '*');
		} catch(e) {}
	}
	var origLog = console.log, origWarn = console.warn, origError = console.error;
	console.log = function() { sendLog('log', arguments); origLog && origLog.apply(console, arguments); };
	console.warn = function() { sendLog('warn', arguments); origWarn && origWarn.apply(console, arguments); };
	console.error = function() { sendLog('error', arguments); origError && origError.apply(console, arguments); };

	window.onerror = function(msg, url, lineNo, columnNo, error) {
		sendLog('error', ['Runtime Error: ' + msg + ' (Line ' + lineNo + ')']);
		return false;
	};
})();
</script>
` : ''

	const jsContent = allowJs ? `<script>${js}</script>` : ''

	return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<style>
		/* Default reset inside sandbox */
		body {
			font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
			margin: 8px;
		}
		${css}
	</style>
	${consoleScript}
</head>
<body>
	${html}
	${jsContent}
</body>
</html>`
}
