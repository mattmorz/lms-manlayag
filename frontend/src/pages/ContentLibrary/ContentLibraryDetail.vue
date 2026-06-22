<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div class="flex gap-2" v-if="library">
			<Button variant="outline" @click="showVersionModal = true">
				<template #prefix>
					<GitBranch class="w-4 h-4" />
				</template>
				{{ __('Create Version') }}
			</Button>
			<Button variant="solid" @click="saveLibrary()" :loading="saving">
				<template #prefix>
					<Save class="w-4 h-4" />
				</template>
				{{ __('Save Changes') }}
			</Button>
		</div>
	</header>

	<div class="py-6 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" v-if="library">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
			<!-- Left/Center Column: Composer / Composition Editor -->
			<div class="lg:col-span-2 space-y-6">
				<div class="bg-white border border-outline-gray-2 rounded-md p-6">
					<div class="flex items-center justify-between border-b border-gray-100 pb-4 mb-4">
						<div>
							<h2 class="text-lg font-bold text-ink-gray-9">{{ __('Library Composition') }}</h2>
							<p class="text-sm text-ink-gray-5">{{ __('Drag and drop items to reorder the content of this library.') }}</p>
						</div>
						<Button variant="solid" size="sm" @click="openAddItemModal()">
							<template #prefix>
								<Plus class="w-4 h-4" />
							</template>
							{{ __('Add Content') }}
						</Button>
					</div>

					<!-- Composition List -->
					<div v-if="library.items && library.items.length">
						<Draggable
							:list="library.items"
							item-key="name"
							handle=".drag-handle"
							class="space-y-3"
						>
							<template #item="{ element: item, index }">
								<div class="flex items-center justify-between p-4 bg-surface-gray-2 rounded-md border border-outline-gray-2 group">
									<div class="flex items-center gap-3 min-w-0">
										<!-- Drag Handle -->
										<div class="drag-handle cursor-grab text-ink-gray-4 group-hover:text-ink-gray-6 p-1">
											<GripVertical class="w-4 h-4" />
										</div>
										<!-- Icon -->
										<div class="p-2 rounded-md" :class="itemTypeClass(item.content_doctype)">
											<component :is="itemTypeIcon(item.content_doctype)" class="w-4 h-4" />
										</div>
										<!-- Title & Details -->
										<div class="min-w-0">
											<h4 class="font-semibold text-sm text-ink-gray-9 truncate">
												{{ item.title || item.content_name }}
											</h4>
											<div class="flex items-center gap-2 mt-0.5 text-xs text-ink-gray-4">
												<span class="font-medium text-ink-gray-6">{{ item.content_doctype }}</span>
												<span>•</span>
												<span class="truncate max-w-[150px]" :title="item.content_name">{{ item.content_name }}</span>
											</div>
										</div>
									</div>
									<div class="flex items-center gap-2">
										<Button
											variant="ghost"
											class="text-red-600 hover:bg-red-50 hover:text-red-800 p-1.5 rounded"
											@click="removeItem(index)"
										>
											<Trash2 class="w-4 h-4 text-red-500" />
										</Button>
									</div>
								</div>
							</template>
						</Draggable>
					</div>

					<div v-else class="flex flex-col items-center justify-center py-16 text-center text-ink-gray-5 border border-dashed border-outline-gray-3 rounded-md bg-surface-gray-1">
						<Library class="w-10 h-10 text-ink-gray-3 mb-2" />
						<div class="font-semibold">{{ __('Empty Library') }}</div>
						<p class="text-sm max-w-xs mt-1">{{ __('Add reusable lessons, quizzes, or assignments to this library.') }}</p>
						<Button variant="outline" size="sm" class="mt-4" @click="openAddItemModal()">
							{{ __('Add Content Now') }}
						</Button>
					</div>
				</div>
			</div>

			<!-- Right Column: Sidebar (Metadata details, Usage tracking, Version history) -->
			<div class="space-y-6">
				<!-- Library Info Panel -->
				<div class="bg-white border border-outline-gray-2 rounded-md p-6 space-y-4">
					<h3 class="text-base font-bold text-ink-gray-9 border-b border-gray-100 pb-3">{{ __('Library Details') }}</h3>
					
					<FormControl
						v-model="library.library_name"
						:label="__('Library Name')"
						type="text"
						:required="true"
					/>
					<FormControl
						v-model="library.description"
						:label="__('Description')"
						type="textarea"
						rows="3"
					/>
					<FormControl
						v-model="library.department"
						:label="__('Department')"
						type="text"
					/>
					<FormControl
						type="select"
						:options="[
							{ label: 'Draft', value: 'Draft' },
							{ label: 'Published', value: 'Published' },
							{ label: 'Archived', value: 'Archived' },
						]"
						v-model="library.status"
						:label="__('Status')"
					/>
					<FormControl
						v-model="library.shared"
						:label="__('Shared with other instructors')"
						type="checkbox"
					/>
					<MultiSelect
						v-slot="scope"
						v-if="library.shared"
						v-model="selectedInstructors"
						doctype="User"
						:label="__('Specific Instructors (Leave blank to share with all)')"
						class="mt-3"
					/>
				</div>

				<!-- Usage Panel -->
				<div class="bg-white border border-outline-gray-2 rounded-md p-6 space-y-4">
					<h3 class="text-base font-bold text-ink-gray-9 border-b border-gray-100 pb-3 flex items-center gap-2">
						<BarChart2 class="w-4 h-4 text-indigo-600" />
						{{ __('Usage Statistics') }}
					</h3>
					<div class="grid grid-cols-2 gap-4 text-center">
						<div class="bg-indigo-50/50 rounded-md p-3 border border-indigo-100">
							<div class="text-xl font-bold text-indigo-600">{{ usage.linked_count || 0 }}</div>
							<div class="text-xs text-ink-gray-5">{{ __('Linked Links') }}</div>
						</div>
						<div class="bg-emerald-50/50 rounded-md p-3 border border-emerald-100">
							<div class="text-xl font-bold text-emerald-600">{{ usage.copied_count || 0 }}</div>
							<div class="text-xs text-ink-gray-5">{{ __('Copied Copies') }}</div>
						</div>
					</div>

					<div class="mt-4" v-if="usage.courses && usage.courses.length">
						<h4 class="text-xs font-semibold text-ink-gray-6 mb-2">{{ __('Linked in Courses:') }}</h4>
						<div class="space-y-1.5 max-h-40 overflow-y-auto">
							<div
								v-for="c in usage.courses"
								:key="c.name"
								class="text-xs flex items-center gap-1.5 text-indigo-600 hover:underline cursor-pointer"
								@click="goToCourse(c.name)"
							>
								<ExternalLink class="w-3.5 h-3.5" />
								<span>{{ c.title }}</span>
							</div>
						</div>
					</div>
					<div v-else class="text-xs text-center text-ink-gray-4 py-2">
						{{ __('Not yet used in any course.') }}
					</div>
				</div>

				<!-- Version Panel -->
				<div class="bg-white border border-outline-gray-2 rounded-md p-6 space-y-4">
					<h3 class="text-base font-bold text-ink-gray-9 border-b border-gray-100 pb-3 flex items-center gap-2">
						<History class="w-4 h-4 text-indigo-600" />
						{{ __('Version History') }}
					</h3>
					<div class="space-y-4 max-h-72 overflow-y-auto pr-1" v-if="versions.length">
						<div
							v-for="v in versions"
							:key="v.name"
							class="text-xs border-l-2 border-indigo-200 pl-3 py-1 space-y-1 relative"
						>
							<div class="flex items-center justify-between">
								<span class="font-bold text-ink-gray-9">v{{ v.version_number }}</span>
								<span class="text-[10px] text-ink-gray-4">{{ formatDate(v.timestamp) }}</span>
							</div>
							<p class="text-ink-gray-6 italic line-clamp-2" :title="v.change_log">
								{{ v.change_log || __('No details.') }}
							</p>
							<div class="pt-1 flex gap-2">
								<Button
									variant="ghost"
									size="sm"
									class="h-6 text-indigo-600 p-0 text-[10px]"
									@click="restoreVersion(v.version_number)"
								>
									{{ __('Restore version') }}
								</Button>
							</div>
						</div>
					</div>
					<div v-else class="text-xs text-center text-ink-gray-4 py-2">
						{{ __('No version history available.') }}
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Add Content Modal -->
	<Dialog
		v-model="showAddModal"
		:options="{
			title: __('Add Content to Library'),
			size: 'md',
			actions: [
				{
					label: __('Add'),
					variant: 'solid',
					onClick: () => handleAddItem()
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					type="select"
					:options="[
						{ label: 'Course Lesson', value: 'Course Lesson' },
						{ label: 'LMS Quiz', value: 'LMS Quiz' },
						{ label: 'LMS Assignment', value: 'LMS Assignment' },
						{ label: 'LMS Programming Exercise', value: 'LMS Programming Exercise' },
						{ label: 'LMS Assessment', value: 'LMS Assessment' },
					]"
					v-model="newItem.doctype"
					:label="__('Content Type')"
				/>

				<div class="flex flex-col">
					<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">{{ __('Search Content') }}</label>
					<div class="relative">
						<input
							type="text"
							v-model="newItem.searchQuery"
							@input="debounceSearch()"
							class="w-full border rounded-md p-2 pl-8 text-sm bg-surface-white"
							placeholder="Type to search..."
						/>
						<SearchIcon class="size-4 text-ink-gray-4 absolute left-2.5 top-3" />
					</div>
				</div>

				<!-- Search Results List -->
				<div class="border rounded-md divide-y max-h-60 overflow-y-auto" v-if="newItem.searchResults.length">
					<div
						v-for="res in newItem.searchResults"
						:key="res.name"
						class="p-2.5 text-sm hover:bg-indigo-50 cursor-pointer flex items-center justify-between gap-4"
						:class="newItem.selectedItem && newItem.selectedItem.name === res.name ? 'bg-indigo-50 border-indigo-200' : ''"
						@click="selectSearchItem(res)"
					>
						<span class="font-medium text-ink-gray-9 truncate">{{ res.title || res.name }}</span>
						<span class="text-xs text-ink-gray-4 flex-shrink-0">{{ res.name }}</span>
					</div>
				</div>
				<div v-else-if="newItem.searchQuery && !newItem.searching" class="text-center text-xs text-ink-gray-4 py-4">
					{{ __('No matching items found.') }}
				</div>
			</div>
		</template>
	</Dialog>

	<!-- Create Version Dialog -->
	<Dialog
		v-model="showVersionModal"
		:options="{
			title: __('Create Library Version'),
			size: 'md',
			actions: [
				{
					label: __('Snapshot & Save'),
					variant: 'solid',
					onClick: () => handleCreateVersion()
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-sm text-ink-gray-6">
					{{ __('This will increment the version number, save the current composition, and create a restore snapshot.') }}
				</p>
				<FormControl
					v-model="versionChangeLog"
					:label="__('Change Log Description')"
					type="textarea"
					placeholder="Describe the changes in this version..."
					:required="true"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	Dialog,
	FormControl,
	toast,
	call,
} from 'frappe-ui'
import MultiSelect from '@/components/Controls/MultiSelect.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Draggable from 'vuedraggable'
import dayjs from '@/utils/dayjs'
import {
	Library,
	Save,
	Plus,
	GitBranch,
	GripVertical,
	Trash2,
	GitCommit,
	HelpCircle,
	NotebookPen,
	SquareCode,
	FileText,
	History,
	BarChart2,
	ExternalLink,
	Search as SearchIcon,
} from 'lucide-vue-next'

const props = defineProps({
	libraryName: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const library = ref(null)
const versions = ref([])
const usage = ref({ linked_count: 0, copied_count: 0, courses: [] })

const saving = ref(false)
const showAddModal = ref(false)
const showVersionModal = ref(false)
const versionChangeLog = ref('')
const selectedInstructors = ref([])

const newItem = ref({
	doctype: 'Course Lesson',
	searchQuery: '',
	searchResults: [],
	selectedItem: null,
	searching: false,
})

let searchTimeout

onMounted(() => {
	loadLibrary()
})

const loadLibrary = () => {
	call('frappe.client.get', {
		doctype: 'Content Library',
		name: props.libraryName,
	})
		.then((res) => {
			if (res) {
				library.value = res
				selectedInstructors.value = (res.shared_instructors || []).map(i => i.instructor)
				fetchUsage()
				fetchVersions()
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to load content library'))
		})
}

const fetchUsage = () => {
	call('lms.lms.api.get_library_usage', { library_name: props.libraryName }).then((res) => {
		if (res) {
			usage.value = res
		}
	})
}

const fetchVersions = () => {
	call('lms.lms.api.get_library_versions', { library_name: props.libraryName }).then((res) => {
		if (res) {
			versions.value = res
		}
	})
}

const saveLibrary = (createVersion = false, changeLog = '') => {
	if (!library.value.library_name.trim()) {
		toast.error(__('Please enter a library name'))
		return
	}
	saving.value = true
	
	const itemsList = (library.value.items || []).map((it) => ({
		content_doctype: it.content_doctype,
		content_name: it.content_name,
		title: it.title || it.content_name,
	}))

	call('lms.lms.api.update_content_library', {
		library_name: props.libraryName,
		title: library.value.library_name,
		description: library.value.description,
		department: library.value.department,
		shared: library.value.shared ? 1 : 0,
		shared_instructors: library.value.shared ? selectedInstructors.value : [],
		items: itemsList,
		create_new_version: createVersion ? 1 : 0,
		change_log: changeLog,
	})
		.then((res) => {
			toast.success(__('Library changes saved successfully'))
			if (res) {
				library.value = res
				selectedInstructors.value = (res.shared_instructors || []).map(i => i.instructor)
				if (library.value.name !== props.libraryName) {
					router.replace({
						name: 'ContentLibraryDetail',
						params: { libraryName: library.value.name },
					})
				}
				fetchUsage()
				fetchVersions()
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to save library changes'))
		})
		.finally(() => {
			saving.value = false
		})
}

const handleCreateVersion = () => {
	const log = versionChangeLog.value.trim()
	if (!log) {
		toast.error(__('Please enter a change log description'))
		return
	}
	showVersionModal.value = false
	saveLibrary(true, log)
	versionChangeLog.value = ''
}

const restoreVersion = (versionNumber) => {
	if (!confirm(__('Are you sure you want to restore version v{0}? This will replace the current composition.', [versionNumber]))) {
		return
	}
	call('lms.lms.api.restore_library_version', {
		library_name: props.libraryName,
		version_number: versionNumber,
	})
		.then((res) => {
			toast.success(__('Version restored successfully'))
			if (res) {
				library.value = res
				fetchVersions()
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to restore version'))
		})
}

const openAddItemModal = () => {
	newItem.value = {
		doctype: 'Course Lesson',
		searchQuery: '',
		searchResults: [],
		selectedItem: null,
		searching: false,
	}
	showAddModal.value = true
}

const debounceSearch = () => {
	clearTimeout(searchTimeout)
	newItem.value.searching = true
	searchTimeout = setTimeout(() => {
		const q = newItem.value.searchQuery.trim()
		const titleField = newItem.value.doctype === 'LMS Assessment' ? 'name' : 'title'
		const filters = {}
		if (q) {
			filters[titleField] = ['like', `%${q}%`]
		}
		
		call('frappe.client.get_list', {
			doctype: newItem.value.doctype,
			fields: ['name', titleField],
			filters: filters,
			limit: 50,
		})
			.then((res) => {
				newItem.value.searchResults = res || []
			})
			.finally(() => {
				newItem.value.searching = false
			})
	}, 300)
}

const selectSearchItem = (item) => {
	newItem.value.selectedItem = item
}

const handleAddItem = () => {
	if (!newItem.value.selectedItem) {
		toast.error(__('Please select an item from the search results'))
		return
	}
	const item = newItem.value.selectedItem
	const titleField = newItem.value.doctype === 'LMS Assessment' ? 'name' : 'title'
	const title = item[titleField] || item.name

	if (!library.value.items) {
		library.value.items = []
	}
	
	// Check if already in list
	const exists = library.value.items.some(
		(it) => it.content_doctype === newItem.value.doctype && it.content_name === item.name
	)
	if (exists) {
		toast.error(__('This item is already added to the library.'))
		return
	}

	library.value.items.push({
		content_doctype: newItem.value.doctype,
		content_name: item.name,
		title: title,
	})

	showAddModal.value = false
	toast.success(__('Item added to composition list'))
}

const removeItem = (index) => {
	library.value.items.splice(index, 1)
}

const itemTypeClass = (doctype) => {
	if (doctype === 'Course Lesson') return 'bg-blue-50 text-blue-600'
	if (doctype === 'LMS Quiz') return 'bg-amber-50 text-amber-600'
	if (doctype === 'LMS Assignment') return 'bg-rose-50 text-rose-600'
	if (doctype === 'LMS Programming Exercise') return 'bg-emerald-50 text-emerald-600'
	return 'bg-purple-50 text-purple-600'
}

const itemTypeIcon = (doctype) => {
	if (doctype === 'Course Lesson') return FileText
	if (doctype === 'LMS Quiz') return HelpCircle
	if (doctype === 'LMS Assignment') return NotebookPen
	if (doctype === 'LMS Programming Exercise') return SquareCode
	return GitCommit
}

const formatDate = (dateStr) => {
	return dayjs(dateStr).format('MMM DD, YYYY hh:mm A')
}

const goToCourse = (courseName) => {
	router.push({
		name: 'CourseDetail',
		params: { courseName },
	})
}

const breadcrumbs = computed(() => [
	{
		label: __('Content Libraries'),
		route: { name: 'ContentLibrary' },
	},
	{
		label: library.value ? library.value.library_name : '...',
		route: {
			name: 'ContentLibraryDetail',
			params: { libraryName: props.libraryName },
		},
	},
])
</script>

<style scoped>
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>
