<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div class="flex gap-2" v-if="library && canEdit">
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
						<Button variant="solid" size="sm" @click="openAddItemModal()" v-if="canEdit">
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
							:disabled="!canEdit"
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
												<span class="font-medium text-ink-gray-6">{{ formatItemType(item.content_doctype) }}</span>
												<span>•</span>
												<span class="truncate max-w-[150px]" :title="item.content_name">{{ item.content_name }}</span>
											</div>
										</div>
									</div>
									<div class="flex items-center gap-2">
										<Button
											variant="outline"
											size="sm"
											class="text-xs text-indigo-600 border-indigo-200"
											@click="openUpgradeManagement(item)"
											v-if="canEdit"
										>
											<template #prefix>
												<GitBranch class="w-3.5 h-3.5" />
											</template>
											{{ __('Versions') }}
										</Button>
										<Button
											variant="ghost"
											class="text-red-600 hover:bg-red-50 hover:text-red-800 p-1.5 rounded"
											@click="removeItem(index)"
											v-if="canEdit"
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
						<Button variant="outline" size="sm" class="mt-4" @click="openAddItemModal()" v-if="canEdit">
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
						:disabled="!canEdit"
					/>
					<FormControl
						v-model="library.description"
						:label="__('Description')"
						type="textarea"
						rows="3"
						:disabled="!canEdit"
					/>
					<FormControl
						v-model="library.department"
						:label="__('Department')"
						type="text"
						:disabled="!canEdit"
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
						:disabled="!canEdit"
					/>
					<FormControl
						v-model="library.shared"
						:label="__('Shared with other instructors')"
						type="checkbox"
						:disabled="!canEdit"
					/>
					<MultiSelect
						v-slot="scope"
						v-if="library.shared"
						v-model="selectedInstructors"
						doctype="User"
						:label="__('Specific Instructors (Leave blank to share with all)')"
						class="mt-3"
						:disabled="!canEdit"
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
						{ label: __('Course Lesson'), value: 'Course Lesson' },
						{ label: __('Quiz'), value: 'LMS Quiz' },
						{ label: __('Assignment'), value: 'LMS Assignment' },
						{ label: __('Programming Exercise'), value: 'LMS Programming Exercise' },
						{ label: __('Assessment'), value: 'LMS Assessment' },
					]"
					v-model="newItem.doctype"
					:label="__('Content Type')"
				/>

				<div class="flex flex-col space-y-1.5 overflow-visible">
					<Link
						:key="newItem.doctype"
						:doctype="newItem.doctype"
						v-model="newItem.selectedItemName"
						:label="__('Select Content')"
						:placeholder="__('Click to choose or type to search...')"
						class="w-full"
					/>
				</div>

				<!-- Selection Indicator -->
				<div v-if="newItem.selectedItem" class="bg-green-50 border border-green-200 rounded-md p-3 flex items-center justify-between mt-4">
					<div class="flex items-center space-x-2">
						<span class="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></span>
						<div class="text-xs">
							<span class="font-bold text-green-800">{{ __('Selected: ') }}</span>
							<span class="text-green-700 font-semibold">
								{{ newItem.selectedItem.title || newItem.selectedItem.name }}
							</span>
							<span class="text-green-500 ml-1">({{ newItem.selectedItem.name }})</span>
						</div>
					</div>
					<Button
						variant="ghost"
						size="sm"
						class="text-red-500 hover:text-red-700 p-1 text-xs"
						@click="clearSelection()"
					>
						{{ __('Clear') }}
					</Button>
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

	<!-- Upgrade / Version Management Modal -->
	<Dialog
		v-model="showUpgradeModal"
		:options="{
			title: __('Manage Versions & Upgrades'),
			size: 'lg',
		}"
	>
		<template #body-content>
			<div class="space-y-6" v-if="activeManageItem">
				<div>
					<h4 class="text-sm font-semibold text-ink-gray-9 mb-1 flex items-center gap-2">
						<component :is="itemTypeIcon(activeManageItem.content_doctype)" class="w-4 h-4 text-indigo-600" />
						{{ activeManageItem.title || activeManageItem.content_name }}
					</h4>
					<p class="text-xs text-ink-gray-5">
						{{ formatItemType(activeManageItem.content_doctype) }} • {{ activeManageItem.content_name }}
					</p>
				</div>

				<!-- Available Versions -->
				<div class="space-y-2">
					<label class="block text-xs font-bold text-ink-gray-6 uppercase tracking-wider">{{ __('Available Versions') }}</label>
					<div class="border border-outline-gray-2 rounded-md bg-surface-gray-2 divide-y">
						<div
							v-for="ver in manageItemVersions"
							:key="ver.name"
							class="p-3 flex items-center justify-between text-sm bg-white"
						>
							<div class="flex items-center gap-2">
								<span class="font-bold text-ink-gray-9">v{{ ver.version_number }}.0</span>
								<span class="text-xs text-ink-gray-4">({{ ver.name }})</span>
								<Badge v-if="ver.is_current_version" theme="green">{{ __('Current Library') }}</Badge>
							</div>
							<span class="text-xs text-ink-gray-5 italic">
								{{ ver.version_notes || __('No details.') }}
							</span>
						</div>
					</div>
				</div>

				<!-- Course Upgrade Management -->
				<div class="space-y-3">
					<div class="flex items-center justify-between">
						<label class="block text-xs font-bold text-ink-gray-6 uppercase tracking-wider">{{ __('Course Placements & Upgrades') }}</label>
						<div class="flex gap-2" v-if="manageItemUsage.courses && manageItemUsage.courses.length">
							<Button
								variant="solid"
								size="sm"
								class="text-xs"
								@click="upgradeAllCoursesToLatest()"
							>
								{{ __('Upgrade All to Latest') }}
							</Button>
						</div>
					</div>

					<div v-if="loadingManageUsage" class="flex justify-center py-6">
						<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
					</div>

					<div v-else-if="manageItemUsage.courses && manageItemUsage.courses.length" class="space-y-2 max-h-52 overflow-y-auto">
						<div
							v-for="usage in manageItemUsage.courses"
							:key="usage.course + '-' + usage.chapter"
							class="flex items-center justify-between p-3.5 bg-surface-white rounded-md border"
						>
							<div class="min-w-0 text-left">
								<span class="font-semibold text-sm text-ink-gray-9 block truncate">{{ usage.course_title }}</span>
								<span class="text-[10px] text-ink-gray-4">{{ __('Chapter ID: ') }}{{ usage.chapter }}</span>
							</div>
							<div class="flex items-center gap-3">
								<div class="text-xs">
									<span class="text-ink-gray-5">{{ __('Using: ') }}</span>
									<span class="font-bold text-indigo-600">v{{ usage.active_version }}.0</span>
								</div>
								
								<Button
									v-if="hasNewerVersion(usage.active_version)"
									variant="outline"
									size="sm"
									class="text-xs"
									@click="upgradeCourseItem(usage)"
								>
									{{ __('Upgrade') }}
								</Button>
								<Badge v-else theme="green">{{ __('Latest') }}</Badge>
							</div>
						</div>
					</div>

					<div v-else class="text-center text-xs text-ink-gray-4 py-6 border border-dashed rounded-md bg-surface-gray-1">
						{{ __('This library item is not currently linked in any active courses.') }}
					</div>
				</div>
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
	Badge,
} from 'frappe-ui'
import MultiSelect from '@/components/Controls/MultiSelect.vue'
import { usersStore } from '@/stores/user'
import Link from '@/components/Controls/Link.vue'
import { ref, computed, onMounted, watch } from 'vue'
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
	History,
	BarChart2,
	ExternalLink,
	Search as SearchIcon,
	BookOpen,
	CircleHelp,
	Pencil,
	Code,
	Award,
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
const showUpgradeModal = ref(false)
const activeManageItem = ref(null)
const manageItemVersions = ref([])
const manageItemUsage = ref({ courses: [] })
const loadingManageUsage = ref(false)

const { userResource } = usersStore()

const canEdit = computed(() => {
	if (!library.value || !userResource.data) return false
	if (userResource.data.is_moderator || userResource.data.roles?.includes('System Manager')) return true
	if (library.value.owner === userResource.data.name) return true
	if (library.value.shared && selectedInstructors.value && selectedInstructors.value.includes(userResource.data.name)) {
		return true
	}
	return false
})

const newItem = ref({
	doctype: 'Course Lesson',
	selectedItemName: null,
	selectedItem: null,
	searchResults: [],
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

const openUpgradeManagement = (item) => {
	activeManageItem.value = item
	showUpgradeModal.value = true
	loadingManageUsage.value = true
	
	call('lms.lms.api.list_versions', {
		content_doctype: item.content_doctype,
		content_name: item.content_name
	}).then(res => {
		if (res) {
			manageItemVersions.value = res
		}
	})

	call('lms.lms.api.retrieve_usage_information', {
		content_doctype: item.content_doctype,
		name: item.content_name
	}).then(res => {
		if (res) {
			manageItemUsage.value = res
		}
	}).finally(() => {
		loadingManageUsage.value = false
	})
}

const hasNewerVersion = (currentVer) => {
	return manageItemVersions.value.some(v => v.version_number > currentVer)
}

const getLatestVersionDoc = () => {
	if (!manageItemVersions.value.length) return null
	return manageItemVersions.value.reduce((prev, current) => (prev.version_number > current.version_number) ? prev : current)
}

const upgradeCourseItem = (usage) => {
	const latest = getLatestVersionDoc()
	if (!latest) return
	
	call('lms.lms.api.upgrade_course_content', {
		course: usage.course,
		chapter: usage.chapter,
		content_doctype: activeManageItem.value.content_doctype,
		old_name: usage.content_name,
		new_name: latest.name
	}).then(() => {
		toast.success(__('Course upgraded successfully'))
		openUpgradeManagement(activeManageItem.value)
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to upgrade course'))
	})
}

const upgradeAllCoursesToLatest = () => {
	const latest = getLatestVersionDoc()
	if (!latest) return
	
	const outdated = manageItemUsage.value.courses.filter(c => c.active_version < latest.version_number)
	if (!outdated.length) return
	
	call('lms.lms.api.upgrade_multiple_courses', {
		courses: JSON.stringify(outdated),
		content_doctype: activeManageItem.value.content_doctype,
		old_name: outdated[0].content_name,
		new_name: latest.name
	}).then(() => {
		toast.success(__('All courses upgraded successfully'))
		openUpgradeManagement(activeManageItem.value)
	}).catch(err => {
		toast.error(err.messages?.[0] || err.message || __('Failed to upgrade courses'))
	})
}

const openAddItemModal = () => {
	newItem.value = {
		doctype: 'Course Lesson',
		selectedItemName: null,
		selectedItem: null,
		searchResults: [],
		searching: false,
	}
	showAddModal.value = true
}

const clearSelection = () => {
	newItem.value.selectedItemName = null
	newItem.value.selectedItem = null
}

watch(
	() => newItem.value.selectedItemName,
	(val) => {
		if (val) {
			const titleField = newItem.value.doctype === 'LMS Assessment' ? 'name' : 'title'
			call('frappe.client.get_value', {
				doctype: newItem.value.doctype,
				filters: { name: val },
				fieldname: titleField
			}).then((res) => {
				if (res) {
					newItem.value.selectedItem = {
						name: val,
						[titleField]: res[titleField]
					}
				}
			})
		} else {
			newItem.value.selectedItem = null
		}
	}
)

watch(
	() => newItem.value.doctype,
	() => {
		clearSelection()
	}
)

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
	if (doctype === 'LMS Assessment') return 'bg-purple-50 text-purple-600'
	return 'bg-gray-50 text-gray-600'
}

const itemTypeIcon = (doctype) => {
	if (doctype === 'Course Lesson') return BookOpen
	if (doctype === 'LMS Quiz') return CircleHelp
	if (doctype === 'LMS Assignment') return Pencil
	if (doctype === 'LMS Programming Exercise') return Code
	if (doctype === 'LMS Assessment') return Award
	return GitCommit
}

const formatItemType = (doctype) => {
	if (doctype === 'Course Lesson') return __('Course Lesson')
	if (doctype === 'LMS Quiz') return __('Quiz')
	if (doctype === 'LMS Assignment') return __('Assignment')
	if (doctype === 'LMS Programming Exercise') return __('Programming Exercise')
	if (doctype === 'LMS Assessment') return __('Assessment')
	return __(doctype)
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

<style>
[data-dialog='Add Content to Library'] .dialog-content {
	overflow: visible !important;
	border-radius: 12px !important;
}
[data-dialog='Add Content to Library'] .dialog-content > :first-child {
	border-top-left-radius: 12px !important;
	border-top-right-radius: 12px !important;
}
[data-dialog='Add Content to Library'] .dialog-content > :last-child {
	border-bottom-left-radius: 12px !important;
	border-bottom-right-radius: 12px !important;
}
</style>
