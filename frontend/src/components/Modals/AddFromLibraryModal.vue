<template>
	<Dialog
		v-model="isOpen"
		:options="{
			title: __('Add from Content Library'),
			size: 'lg',
		}"
	>
		<template #body-content>
			<div class="space-y-6">
				<!-- Step 1: Select Library -->
				<div class="flex flex-col">
					<label class="block text-sm font-semibold text-ink-gray-9 mb-1.5">{{ __('Select Content Library') }}</label>
					<select
						v-model="selectedLibrary"
						@change="fetchLibraryItems()"
						class="w-full border rounded-md p-3 text-sm bg-surface-white focus:ring-1 focus:ring-brand-indigo"
					>
						<option value="" disabled>{{ __('Choose a content library...') }}</option>
						<optgroup :label="__('My Libraries')" v-if="libraries.my_libraries.length">
							<option v-for="lib in libraries.my_libraries" :key="lib.name" :value="lib.name">
								{{ lib.library_name }} (v{{ lib.version }})
							</option>
						</optgroup>
						<optgroup :label="__('Department Libraries')" v-if="libraries.department_libraries.length">
							<option v-for="lib in libraries.department_libraries" :key="lib.name" :value="lib.name">
								{{ lib.library_name }} (v{{ lib.version }})
							</option>
						</optgroup>
						<optgroup :label="__('Shared Libraries')" v-if="libraries.shared_libraries.length">
							<option v-for="lib in libraries.shared_libraries" :key="lib.name" :value="lib.name">
								{{ lib.library_name }} (v{{ lib.version }})
							</option>
						</optgroup>
					</select>
				</div>

				<!-- Step 2: Display Items and Multiselect -->
				<div v-if="selectedLibrary" class="space-y-3">
					<div class="flex items-center justify-between border-b pb-2">
						<label class="block text-sm font-semibold text-ink-gray-9">{{ __('Select Content Items') }}</label>
						<div class="flex gap-2">
							<Button variant="ghost" size="sm" class="text-indigo-600 p-0 text-xs" @click="selectAllItems()">
								{{ __('Select All') }}
							</Button>
							<span class="text-ink-gray-3">|</span>
							<Button variant="ghost" size="sm" class="text-indigo-600 p-0 text-xs" @click="deselectAllItems()">
								{{ __('Deselect All') }}
							</Button>
						</div>
					</div>

					<div v-if="loadingItems" class="flex justify-center py-10">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
					</div>

					<div v-else-if="libraryItems.length" class="space-y-2 max-h-60 overflow-y-auto pr-1">
						<div
							v-for="item in libraryItems"
							:key="item.name"
							@click="toggleItemSelection(item)"
							class="flex items-center justify-between p-3.5 bg-surface-gray-2 hover:bg-indigo-50/50 rounded-md border border-outline-gray-2 hover:border-indigo-200 transition-all cursor-pointer"
						>
							<div class="flex items-center gap-3 min-w-0">
								<!-- Checkbox -->
								<input
									type="checkbox"
									:checked="isItemSelected(item)"
									class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
									@click.stop="toggleItemSelection(item)"
								/>
								<!-- Icon -->
								<div class="p-1.5 rounded bg-white text-ink-gray-8 border">
									<component :is="itemTypeIcon(item.content_doctype)" class="w-3.5 h-3.5" />
								</div>
								<!-- Text -->
								<div class="min-w-0 text-left">
									<span class="font-medium text-sm text-ink-gray-9 block truncate">{{ item.title || item.content_name }}</span>
									<span class="text-[10px] text-ink-gray-4">{{ item.content_doctype }}</span>
								</div>
							</div>
						</div>
					</div>

					<div v-else class="text-center text-sm text-ink-gray-5 py-8">
						{{ __('This library does not contain any content items.') }}
					</div>
				</div>

				<!-- Step 3: Choose Mode -->
				<div v-if="selectedLibrary && selectedItems.length" class="bg-indigo-50/40 rounded-md p-5 border border-indigo-100/50 space-y-3">
					<label class="block text-sm font-semibold text-ink-gray-9 mb-1">{{ __('Choose Reuse Mode') }}</label>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<!-- Linked Mode -->
						<div
							@click="importMode = 'Linked'"
							class="cursor-pointer border-2 rounded-md p-4 bg-white transition-all text-left"
							:class="importMode === 'Linked' ? 'border-indigo-600 ring-2 ring-indigo-50' : 'border-outline-gray-2'"
						>
							<div class="flex items-center justify-between mb-1.5">
								<span class="font-bold text-sm text-ink-gray-9">{{ __('Linked Mode') }}</span>
								<div class="h-4 w-4 rounded-full border flex items-center justify-center" :class="importMode === 'Linked' ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-gray-300'">
									<div class="h-2 w-2 rounded-full bg-white" v-if="importMode === 'Linked'"></div>
								</div>
							</div>
							<p class="text-xs text-ink-gray-5 leading-normal">
								{{ __('Recommended. Modifying the original library content automatically updates this course without duplicating content.') }}
							</p>
						</div>

						<!-- Copied Mode -->
						<div
							@click="importMode = 'Copied'"
							class="cursor-pointer border-2 rounded-md p-4 bg-white transition-all text-left"
							:class="importMode === 'Copied' ? 'border-indigo-600 ring-2 ring-indigo-50' : 'border-outline-gray-2'"
						>
							<div class="flex items-center justify-between mb-1.5">
								<span class="font-bold text-sm text-ink-gray-9">{{ __('Copied Mode') }}</span>
								<div class="h-4 w-4 rounded-full border flex items-center justify-center" :class="importMode === 'Copied' ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-gray-300'">
									<div class="h-2 w-2 rounded-full bg-white" v-if="importMode === 'Copied'"></div>
								</div>
							</div>
							<p class="text-xs text-ink-gray-5 leading-normal">
								{{ __('Creates independent clones. Future updates to the library or other courses referencing it will not propagate here.') }}
							</p>
						</div>
					</div>
				</div>

				<!-- Actions -->
				<div class="flex justify-end gap-3 pt-4 border-t">
					<Button variant="ghost" @click="isOpen = false">
						{{ __('Cancel') }}
					</Button>
					<Button
						variant="solid"
						@click="importContent()"
						:disabled="!selectedLibrary || !selectedItems.length"
						:loading="importing"
					>
						{{ __('Add to Course') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, Button, toast, call } from 'frappe-ui'
import { ref, computed, watch, onMounted } from 'vue'
import {
	HelpCircle,
	NotebookPen,
	SquareCode,
	FileText,
	GitCommit,
} from 'lucide-vue-next'

const props = defineProps({
	modelValue: {
		type: Boolean,
		required: true,
	},
	course: {
		type: String,
		required: true,
	},
	chapter: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['update:modelValue', 'imported'])

const isOpen = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val),
})

const libraries = ref({
	my_libraries: [],
	department_libraries: [],
	shared_libraries: [],
})

const selectedLibrary = ref('')
const libraryItems = ref([])
const selectedItems = ref([])
const importMode = ref('Linked')
const loadingItems = ref(false)
const importing = ref(false)

onMounted(() => {
	fetchLibraries()
})

const fetchLibraries = () => {
	call('lms.lms.api.get_content_libraries')
		.then((res) => {
			if (res) {
				libraries.value = res
			}
		})
}

const fetchLibraryItems = () => {
	if (!selectedLibrary.value) return
	loadingItems.value = true
	selectedItems.value = []
	call('frappe.client.get', {
		doctype: 'Content Library',
		name: selectedLibrary.value,
	})
		.then((res) => {
			if (res) {
				libraryItems.value = res.items || []
			}
		})
		.finally(() => {
			loadingItems.value = false
		})
}

const selectAllItems = () => {
	selectedItems.value = [...libraryItems.value]
}

const deselectAllItems = () => {
	selectedItems.value = []
}

const isItemSelected = (item) => {
	return selectedItems.value.some(
		(it) => it.content_doctype === item.content_doctype && it.content_name === item.content_name
	)
}

const toggleItemSelection = (item) => {
	const index = selectedItems.value.findIndex(
		(it) => it.content_doctype === item.content_doctype && it.content_name === item.content_name
	)
	if (index === -1) {
		selectedItems.value.push(item)
	} else {
		selectedItems.value.splice(index, 1)
	}
}

const importContent = () => {
	if (!selectedLibrary.value || !selectedItems.value.length) return
	importing.value = true
	
	const itemsList = selectedItems.value.map((it) => ({
		content_doctype: it.content_doctype,
		content_name: it.content_name,
		title: it.title || it.content_name,
	}))

	call('lms.lms.api.add_library_content_to_course', {
		course: props.course,
		chapter: props.chapter,
		library: selectedLibrary.value,
		items: itemsList,
		mode: importMode.value,
	})
		.then((res) => {
			if (res && res.success) {
				toast.success(__('Library content added to course successfully'))
				emit('imported')
				isOpen.value = false
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to add library content to course'))
		})
		.finally(() => {
			importing.value = false
		})
}

const itemTypeIcon = (doctype) => {
	if (doctype === 'Course Lesson') return FileText
	if (doctype === 'LMS Quiz') return HelpCircle
	if (doctype === 'LMS Assignment') return NotebookPen
	if (doctype === 'LMS Programming Exercise') return SquareCode
	return GitCommit
}
</script>
