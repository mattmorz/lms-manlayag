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
					if (!elem) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const actualText = (elem.textContent || '').trim().toLowerCase()
						const expectedText = (tc.expected_text || tc.expected_value || '').trim().toLowerCase()
						testPassed = actualText.includes(expectedText)
						detailMessage = testPassed
							? `Element '${selector}' contains text '${tc.expected_text || tc.expected_value}'`
							: `Expected text '${tc.expected_text || tc.expected_value}', found '${elem.textContent.trim()}'`
					}
					break

				case 'CSS Property':
					if (!elem) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const win = iframeDocument.defaultView || window
						const computedStyle = win.getComputedStyle(elem)
						const propName = tc.property || ''
						const actualVal = computedStyle.getPropertyValue(propName) || computedStyle[propName] || ''
						const expectedVal = (tc.expected_value || '').trim().toLowerCase()

						// Normalize colors/values where possible
						testPassed = (actualVal || '').trim().toLowerCase().includes(expectedVal)
						detailMessage = testPassed
							? `CSS property '${propName}' matches '${tc.expected_value}'`
							: `CSS '${propName}' is '${actualVal}', expected '${tc.expected_value}'`
					}
					break

				case 'Attribute':
					if (!elem) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const attrName = tc.property || ''
						const actualAttr = elem.getAttribute(attrName) || ''
						const expectedAttr = (tc.expected_value || '').trim().toLowerCase()
						testPassed = actualAttr.toLowerCase().includes(expectedAttr)
						detailMessage = testPassed
							? `Attribute '${attrName}' matches '${expectedAttr}'`
							: `Attribute '${attrName}' is '${actualAttr}', expected '${expectedAttr}'`
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
					if (!elem) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const actualVal = (elem.value || '').trim()
						const expectedVal = (tc.expected_value || '').trim()
						testPassed = actualVal === expectedVal
						detailMessage = testPassed
							? `Input value matches '${expectedVal}'`
							: `Input value is '${actualVal}', expected '${expectedVal}'`
					}
					break

				case 'Class Exists':
					if (!elem) {
						testPassed = false
						detailMessage = `Element '${selector}' not found`
					} else {
						const className = (tc.expected_value || tc.property || '').trim()
						testPassed = elem.classList.contains(className)
						detailMessage = testPassed
							? `Class '${className}' exists on '${selector}'`
							: `Class '${className}' missing on '${selector}'`
					}
					break

				case 'Class Does Not Exist':
					if (!elem) {
						testPassed = true
						detailMessage = `Element '${selector}' not found`
					} else {
						const className = (tc.expected_value || tc.property || '').trim()
						testPassed = !elem.classList.contains(className)
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
