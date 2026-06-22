<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div class="flex gap-2">
			<Button variant="outline" @click="showConvertModal = true">
				<template #prefix>
					<Shuffle class="w-4 h-4" />
				</template>
				{{ __('Convert Course to Library') }}
			</Button>
			<Button variant="solid" @click="showCreateModal = true">
				<template #prefix>
					<Plus class="w-4 h-4" />
				</template>
				{{ __('Create Library') }}
			</Button>
		</div>
	</header>

	<div class="py-5 mx-5">
		<!-- Tabs and Search -->
		<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
			<TabButtons :buttons="libraryTabs" v-model="currentTab" class="w-fit" />
			<FormControl v-model="search" type="text" :placeholder="__('Search Libraries')" class="w-full sm:w-72">
				<template #prefix>
					<SearchIcon class="size-4 text-ink-gray-5" />
				</template>
			</FormControl>
		</div>

		<!-- Loading State -->
		<div v-if="loading" class="flex justify-center items-center py-24">
			<div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-indigo"></div>
		</div>

		<!-- Library Cards Grid -->
		<div v-else-if="filteredLibraries.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<div
				v-for="lib in filteredLibraries"
				:key="lib.name"
				@click="openLibrary(lib.name)"
				class="cursor-pointer bg-white border border-outline-gray-2 rounded-md p-5 flex flex-col justify-between"
			>
				<div>
					<div class="flex items-start justify-between gap-4 mb-4">
						<div class="bg-surface-gray-2 text-ink-gray-7 p-2 rounded-md">
							<Library class="w-5 h-5 stroke-1.5" />
						</div>
						<span
							class="text-xs font-semibold px-2.5 py-1 rounded-md border"
							:class="statusClass(lib.status)"
						>
							{{ lib.status }}
						</span>
					</div>

					<h3 class="font-semibold text-ink-gray-9 text-base line-clamp-1 mb-1">
						{{ lib.library_name }}
					</h3>
					
					<p class="text-sm text-ink-gray-5 line-clamp-2 min-h-[2.5rem] mb-4">
						{{ lib.description || __('No description provided.') }}
					</p>
				</div>

				<div class="border-t border-gray-100 pt-4 mt-2 flex items-center justify-between text-xs text-ink-gray-4">
					<div class="flex items-center gap-1.5">
						<User class="w-3.5 h-3.5" />
						<span class="truncate max-w-[100px]">{{ lib.owner }}</span>
					</div>
					<div class="flex items-center gap-3">
						<span v-if="lib.department" class="bg-gray-100 px-2 py-0.5 rounded text-ink-gray-6">
							{{ lib.department }}
						</span>
						<span class="font-medium">
							v{{ lib.version || 1 }}
						</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Empty State -->
		<div v-else class="flex flex-col items-center justify-center py-20 bg-surface-gray-2 rounded-md border border-dashed border-outline-gray-3">
			<div class="bg-white p-4 rounded-full border border-outline-gray-2 mb-4 text-ink-gray-4">
				<Library class="w-12 h-12 stroke-1" />
			</div>
			<h3 class="text-ink-gray-7 font-bold text-lg mb-1">{{ __('No Content Libraries') }}</h3>
			<p class="text-ink-gray-5 text-sm text-center max-w-md px-4">
				{{ __('Create a new content library to build reusable lessons, quizzes, and exercises that can be easily shared across multiple courses.') }}
			</p>
			<div class="mt-6 flex gap-3">
				<Button variant="outline" @click="showConvertModal = true">
					{{ __('Convert Course') }}
				</Button>
				<Button variant="solid" @click="showCreateModal = true">
					{{ __('Create New') }}
				</Button>
			</div>
		</div>
	</div>

	<!-- Create Library Dialog -->
	<Dialog
		v-model="showCreateModal"
		:options="{
			title: __('Create Content Library'),
			size: 'md',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: () => handleCreateLibrary(),
					loading: creating
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="newLib.title"
					:label="__('Library Name')"
					type="text"
					:required="true"
					placeholder="e.g. Standard Math Quizzes"
				/>
				<FormControl
					v-model="newLib.description"
					:label="__('Description')"
					type="textarea"
					placeholder="Describe the purpose of this content library..."
				/>
				<FormControl
					v-model="newLib.department"
					:label="__('Department')"
					type="text"
					placeholder="e.g. Science, Mathematics"
				/>
				<FormControl
					v-model="newLib.shared"
					:label="__('Shared with other instructors')"
					type="checkbox"
				/>
				<MultiSelect
					v-if="newLib.shared"
					v-model="selectedInstructors"
					doctype="User"
					:label="__('Specific Instructors (Leave blank to share with all)')"
					class="mt-3"
				/>
			</div>
		</template>
	</Dialog>

	<!-- Convert Course Dialog -->
	<Dialog
		v-model="showConvertModal"
		:options="{
			title: __('Convert Course to Library'),
			size: 'md',
			actions: [
				{
					label: __('Convert'),
					variant: 'solid',
					onClick: () => handleConvertCourse(),
					loading: converting
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div class="flex flex-col">
					<label class="block text-sm font-medium text-ink-gray-5 mb-1.5">{{ __('Select Course') }}</label>
					<select
						v-model="convertLib.course"
						class="w-full border rounded-md p-2 text-sm bg-surface-white focus:ring-1 focus:ring-brand-indigo"
					>
						<option value="" disabled>{{ __('Choose a course...') }}</option>
						<option v-for="c in courses" :key="c.name" :value="c.name">
							{{ c.title }}
						</option>
					</select>
				</div>
				<FormControl
					v-model="convertLib.title"
					:label="__('New Library Name')"
					type="text"
					:required="true"
					placeholder="e.g. Advanced Physics Library"
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
	TabButtons,
	toast,
	usePageMeta,
	call,
} from 'frappe-ui'
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { Library, Plus, Shuffle, Search as SearchIcon, User } from 'lucide-vue-next'
import MultiSelect from '@/components/Controls/MultiSelect.vue'

const { brand } = sessionStore()
const router = useRouter()

const search = ref('')
const currentTab = ref('my')
const loading = ref(false)
const librariesData = ref({
	my_libraries: [],
	department_libraries: [],
	shared_libraries: [],
	most_used_libraries: [],
})

const libraryTabs = computed(() => [
	{ label: __('My Libraries'), value: 'my' },
	{ label: __('Department'), value: 'department' },
	{ label: __('Shared'), value: 'shared' },
	{ label: __('Most Used'), value: 'most_used' },
])

// Create library states
const showCreateModal = ref(false)
const creating = ref(false)
const newLib = ref({
	title: '',
	description: '',
	department: '',
	shared: false,
})
const selectedInstructors = ref([])

// Convert course states
const showConvertModal = ref(false)
const converting = ref(false)
const courses = ref([])
const convertLib = ref({
	course: '',
	title: '',
})

onMounted(() => {
	fetchLibraries()
	fetchCourses()
})

const fetchLibraries = () => {
	loading.value = true
	call('lms.lms.api.get_content_libraries')
		.then((res) => {
			if (res) {
				librariesData.value = res
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to fetch content libraries'))
		})
		.finally(() => {
			loading.value = false
		})
}

const fetchCourses = () => {
	call('frappe.client.get_list', {
		doctype: 'LMS Course',
		fields: ['name', 'title'],
		limit: 1000,
	}).then((res) => {
		if (res) {
			courses.value = res
		}
	})
}

const currentLibrariesList = computed(() => {
	if (currentTab.value === 'my') return librariesData.value.my_libraries || []
	if (currentTab.value === 'department') return librariesData.value.department_libraries || []
	if (currentTab.value === 'shared') return librariesData.value.shared_libraries || []
	if (currentTab.value === 'most_used') return librariesData.value.most_used_libraries || []
	return []
})

const filteredLibraries = computed(() => {
	const list = currentLibrariesList.value
	const q = search.value.toLowerCase().trim()
	if (!q) return list
	return list.filter(
		(l) =>
			(l.library_name && l.library_name.toLowerCase().includes(q)) ||
			(l.description && l.description.toLowerCase().includes(q)) ||
			(l.department && l.department.toLowerCase().includes(q))
	)
})

const openLibrary = (libraryName) => {
	router.push({
		name: 'ContentLibraryDetail',
		params: { libraryName },
	})
}

const handleCreateLibrary = () => {
	const title = newLib.value.title.trim()
	if (!title) {
		toast.error(__('Please enter a library name'))
		return
	}
	creating.value = true
	call('lms.lms.api.create_content_library', {
		title,
		description: newLib.value.description,
		department: newLib.value.department,
		shared: newLib.value.shared ? 1 : 0,
		shared_instructors: newLib.value.shared ? selectedInstructors.value : [],
	})
		.then((res) => {
			toast.success(__('Content Library created successfully'))
			showCreateModal.value = false
			// reset form
			newLib.value = { title: '', description: '', department: '', shared: false }
			selectedInstructors.value = []
			fetchLibraries()
			if (res && res.name) {
				openLibrary(res.name)
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to create content library'))
		})
		.finally(() => {
			creating.value = false
		})
}

const handleConvertCourse = () => {
	const course = convertLib.value.course
	const title = convertLib.value.title.trim()
	if (!course) {
		toast.error(__('Please select a course'))
		return
	}
	if (!title) {
		toast.error(__('Please enter a library name'))
		return
	}
	converting.value = true
	call('lms.lms.api.convert_course_to_library', {
		course_name: course,
		library_title: title,
	})
		.then((res) => {
			toast.success(__('Course converted to library successfully'))
			showConvertModal.value = false
			convertLib.value = { course: '', title: '' }
			fetchLibraries()
			if (res && res.name) {
				openLibrary(res.name)
			}
		})
		.catch((err) => {
			toast.error(err.messages?.[0] || err.message || __('Failed to convert course'))
		})
		.finally(() => {
			converting.value = false
		})
}

const statusClass = (status) => {
	if (status === 'Draft') return 'bg-amber-50 text-amber-700 border-amber-200'
	if (status === 'Published') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
	return 'bg-gray-50 text-gray-700 border-gray-200'
}

const breadcrumbs = computed(() => [
	{
		label: __('Content Libraries'),
		route: { name: 'ContentLibrary' },
	},
])

usePageMeta(() => ({
	title: __('Content Library'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
.line-clamp-1 {
	display: -webkit-box;
	-webkit-line-clamp: 1;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>
