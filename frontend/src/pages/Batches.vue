<template>
	<header
		class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div v-if="user.data">
			<!-- Batches Tab: Create Button -->
			<router-link
				v-if="currentTopTab === 'batches' && canCreateBatch()"
				:to="{
					name: 'BatchForm',
					params: { batchName: 'new' },
				}"
			>
				<Button variant="solid">
					<template #prefix>
						<Plus class="h-4 w-4 stroke-1.5" />
					</template>
					{{ __('Create') }}
				</Button>
			</router-link>

			<!-- Students Tab: New Button Dropdown -->
			<Dropdown
				v-else-if="currentTopTab === 'students'"
				:options="[
					{
						label: __('Add Manually'),
						icon: 'plus',
						onClick() {
							showManualModal = true
						},
					},
					{
						label: __('Import CSV'),
						icon: 'upload',
						onClick() {
							showImportModal = true
						},
					},
				]"
			>
				<template v-slot="{ open }">
					<Button variant="solid">
						<template #prefix>
							<Plus class="h-4 w-4 stroke-1.5" />
						</template>
						{{ __('New') }}
						<template #suffix>
							<ChevronDown
								:class="[
									'w-4 h-4 stroke-1.5 ml-1 transform transition-transform',
									open ? 'rotate-180' : '',
								]"
							/>
						</template>
					</Button>
				</template>
			</Dropdown>
		</div>
	</header>
	<div class="p-5 pb-10">
		<!-- Top level tab switcher (Batches / Students) -->
		<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6" v-if="showTopTabs">
			<TabButtons :buttons="topTabs" v-model="currentTopTab" class="w-fit" />
		</div>

		<!-- Batches sub-navigation & filters (only visible when Batches top tab is active) -->
		<div
			v-if="currentTopTab === 'batches'"
			class="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:items-center justify-between mb-5"
		>
			<div class="text-lg text-ink-gray-9 font-semibold">
				{{ __('All Batches') }}
			</div>
			<div
				class="flex flex-col space-y-3 lg:space-y-0 lg:flex-row lg:items-center lg:space-x-4"
			>
				<TabButtons
					v-if="user.data"
					:buttons="batchTabs"
					v-model="currentTab"
					class="w-fit"
				/>
				<div class="grid grid-cols-2 gap-2">
					<FormControl
						v-model="title"
						:placeholder="__('Search by Title')"
						type="text"
						class="min-w-40 lg:min-w-0 lg:w-32 xl:w-40"
						@input="updateBatches()"
					/>
					<div class="min-w-40 lg:min-w-0 lg:w-32 xl:w-40">
						<Select
							v-if="categories.length"
							v-model="currentCategory"
							:options="categories"
							:placeholder="__('Category')"
							@update:modelValue="updateBatches()"
						/>
					</div>
				</div>

				<FormControl
					v-model="certification"
					:label="__('Certification')"
					type="checkbox"
					@change="updateBatches()"
				/>
			</div>
		</div>

		<!-- Students filter dropdowns (only visible when Students top tab is active) -->
		<div
			v-if="currentTopTab === 'students'"
			class="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:items-center justify-between mb-5 gap-4"
		>
			<div class="text-lg text-ink-gray-9 font-semibold">
				{{ __('All Students') }}
			</div>
			<div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full lg:w-auto justify-end lg:ml-auto">
				<FormControl
					v-model="studentSearch"
					type="text"
					:placeholder="__('Search Student...')"
					class="w-full sm:w-64"
				>
					<template #prefix>
						<FeatherIcon name="search" class="size-4 text-ink-gray-5" />
					</template>
				</FormControl>
				<div class="min-w-40 sm:w-48 xl:w-56">
					<Select
						v-model="studentBatchFilter"
						:options="studentBatchFilterOptions"
						:placeholder="__('All Batches')"
					/>
				</div>
			</div>
		</div>

		<!-- Top level tab contents -->
		<div v-if="currentTopTab === 'students'">
			<div v-if="studentList.loading && !studentListItems.length" class="flex justify-center items-center py-12">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
			</div>
			<template v-else>
				<ListViewStudents
					v-if="studentListItems.length"
					:columns="studentColumns"
					:rows="studentListItems"
					row-key="name"
					:options="{ showTooltip: false, selectable: true }"
				>
					<ListHeader
						class="mb-2 grid items-center space-x-4 rounded bg-surface-gray-2 p-2"
					>
						<ListHeaderItem
							:item="column"
							v-for="column in studentColumns"
							:key="column.key"
							@click="toggleSort(column.key)"
							class="cursor-pointer hover:bg-surface-gray-3/50 px-2 py-1 rounded transition-colors select-none"
						>
							<div class="flex items-center space-x-1.5" :class="column.align === 'center' ? 'justify-center w-full' : ''">
								<FeatherIcon v-if="column.icon" :name="column.icon" class="h-3.5 w-3.5 text-ink-gray-5 stroke-1.5" />
								<span>{{ column.label }}</span>
								<span class="text-xs text-ink-gray-5 ml-1" v-if="studentSortBy.startsWith(column.key)">
									{{ studentSortBy.endsWith('desc') ? ' ↓' : ' ↑' }}
								</span>
							</div>
						</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow
						v-for="row in studentListItems"
						:key="row.name"
						:row="row"
						:class="{ 'opacity-50': row.enabled === 0 }"
					>
						<template #default="{ column }">
							<ListRowItem :item="row[column.key]" :align="column.align">
								<div v-if="column.key === 'member_name'" class="flex items-center gap-3 w-full">
									<div
										v-if="!row.user_image"
										:style="getAvatarStyle(row.member_name)"
										class="h-8 w-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 select-none border border-outline-gray-2"
									>
										{{ row.member_name ? row.member_name.charAt(0).toUpperCase() : '?' }}
									</div>
									<img
										v-else
										:src="row.user_image"
										class="h-8 w-8 rounded-full object-cover flex-shrink-0 border border-outline-gray-2"
									/>
									<div class="flex flex-col min-w-0 flex-1">
										<span class="font-semibold text-ink-gray-9 truncate">{{ row.member_name }}</span>
										<span class="text-xs text-ink-gray-5 truncate">{{ row.email }}</span>
									</div>
								</div>
								<div v-else-if="column.key === 'batch_title'" class="min-w-0 w-full">
									<router-link
										v-if="row.batch"
										:to="{ name: 'BatchDetail', params: { batchName: row.batch } }"
										class="font-medium text-blue-600 hover:text-blue-800 hover:underline truncate block"
									>
										{{ row.batch_title }}
									</router-link>
									<button
										v-else
										@click.stop="openManualModalForStudent(row)"
										class="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md border border-outline-gray-3 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9 transition-colors"
										:title="__('Assign to a batch')"
									>
										<FeatherIcon name="plus" class="h-3 w-3" />
										{{ __('Assign Batch') }}
									</button>
								</div>
								<div v-else-if="column.key === 'creation'" class="text-ink-gray-7 text-sm">
									{{ dayjs(row.creation).format('DD MMM YYYY') }}
								</div>
								<div v-else-if="column.key === 'progress'" class="flex items-center gap-3 w-full justify-start">
									<div class="w-full bg-outline-gray-2 rounded-full h-1.5 overflow-hidden max-w-[100px]">
										<div
											:class="[
												'h-full rounded-full transition-all duration-500',
												row.progress >= 90
													? 'bg-green-500'
													: row.progress >= 50
													? 'bg-blue-500'
													: 'bg-amber-500',
											]"
											:style="{ width: `${row.progress}%` }"
										></div>
									</div>
									<span class="text-xs font-semibold text-ink-gray-7 whitespace-nowrap">{{ Math.round(row.progress) }}%</span>
								</div>
								<div v-else-if="column.key === 'last_active'" class="text-ink-gray-6 text-sm text-left w-full">
									{{ row.last_active }}
								</div>
							</ListRowItem>
						</template>
					</ListRow>
				</ListRows>
				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex items-center gap-4">
							<Switch
								size="sm"
								:label="__('Disable Account')"
								labelClasses="!text-red-600 text-sm font-medium"
								:modelValue="areAllSelectedStudentsDisabled(selections)"
								@update:modelValue="val => handleBulkToggleStudentAccounts(selections, val, unselectAll)"
								class="hover:!bg-red-50 py-1.5 px-3 rounded cursor-pointer"
							/>
							<Tooltip :text="__('Unenroll from Batch')">
								<Button
									variant="ghost"
									:loading="unenrollStudentResource.loading"
									@click="handleUnenrollStudents(selections, unselectAll)"
									class="text-red-600 hover:bg-red-50"
								>
									<template #icon>
										<FeatherIcon name="log-out" class="h-4 w-4 stroke-1.5" />
									</template>
								</Button>
							</Tooltip>
						</div>
					</template>
				</ListSelectBanner>
				</ListViewStudents>
				<div v-else class="text-center py-12 text-ink-gray-5">
					{{ __('No students found matching the filters.') }}
				</div>
				<div v-if="studentList.data?.has_next_page" class="flex justify-center mt-6">
					<Button @click="loadMoreStudents" :loading="studentList.loading">
						{{ __('Load More') }}
					</Button>
				</div>
			</template>

			<Dialog
				v-model="showImportModal"
				:options="{
					title: __('Import Students'),
					size: 'lg',
				}"
			>
				<template #body-content>
					<div class="space-y-4">
						<!-- Step 1: Upload CSV -->
						<div v-if="!importResults && !importError" class="space-y-4">
							<p class="text-sm text-ink-gray-6">
								{{ __('Upload a CSV file containing student emails and names. Unregistered users will be onboarded and sent a welcome email.') }}
							</p>
							<div class="p-3 bg-surface-gray-2 border border-outline-gray-2 rounded-lg text-xs text-ink-gray-7">
								<strong>{{ __('Expected format:') }}</strong>
								<pre class="mt-1 font-mono">email,full_name
student1@example.com,Student One
student2@example.com,Student Two</pre>
							</div>
							<div class="space-y-2">
								<label class="text-xs font-semibold text-ink-gray-7">{{ __('CSV File') }}</label>
								<input
									:key="inputKey"
									type="file"
									accept=".csv"
									@change="handleCSVFileChange"
									class="w-full text-sm text-ink-gray-7 border border-outline-gray-2 rounded-md p-2 bg-surface-white"
								/>
							</div>
						</div>

						<!-- Global Import Error State -->
						<div v-else-if="importError" class="space-y-4">
							<div class="p-4 rounded-lg bg-red-50 text-red-900 border border-red-200 text-sm">
								<div class="font-semibold text-red-800">{{ __('Failed to import students') }}</div>
								<div class="mt-1 text-xs font-mono whitespace-pre-wrap">{{ importError }}</div>
							</div>
						</div>

						<!-- Step 2: Show Checklist, Metrics, & Logs -->
						<div v-else-if="importResults" class="space-y-4">
							<!-- Import Success/Skipped/Error log metrics -->
							<div class="grid grid-cols-3 gap-3 p-3 bg-surface-gray-2 border border-outline-gray-2 rounded-lg text-xs font-semibold">
								<div class="text-green-700">
									{{ __('Created:') }} {{ importResults.created || 0 }}
								</div>
								<div class="text-amber-700">
									{{ __('Skipped:') }} {{ importResults.skipped || 0 }}
								</div>
								<div class="text-red-700">
									{{ __('Errors:') }} {{ importResults.errors?.length || 0 }}
								</div>
							</div>

							<!-- Import Logs & Checklist Container -->
							<div class="space-y-2">
								<label class="text-xs font-semibold text-ink-gray-7">{{ __('Import Logs') }}</label>
								<div class="border border-outline-gray-2 rounded-lg overflow-hidden bg-surface-white">
									<!-- Header with Select All -->
									<div v-if="importResults.imported_users && importResults.imported_users.length" class="flex items-center gap-2 p-2.5 bg-surface-gray-2 border-b border-outline-gray-2">
										<input
											type="checkbox"
											id="selectAllImported"
											:checked="selectedImportedEmails.length === importResults.imported_users.length"
											@change="toggleSelectAllImported"
											class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
										/>
										<label for="selectAllImported" class="text-xs font-semibold text-ink-gray-9 cursor-pointer select-none">
											{{ __('Select All for Batch Assignment') }} ({{ selectedImportedEmails.length }}/{{ importResults.imported_users.length }})
										</label>
									</div>
									<div v-else class="p-2.5 bg-surface-gray-2 border-b border-outline-gray-2 text-xs font-semibold text-ink-gray-7">
										{{ __('Import Details') }}
									</div>

									<!-- Scrollable logs list -->
									<div class="max-h-60 overflow-y-auto divide-y divide-outline-gray-2">
										<!-- Successful/Skipped Users -->
										<div
											v-for="user in importResults.imported_users"
											:key="user.email"
											class="flex items-center justify-between p-2.5 hover:bg-surface-gray-1 transition-colors text-xs"
										>
											<div class="flex items-center gap-2 min-w-0">
												<input
													type="checkbox"
													:id="'imported-' + user.email"
													v-model="selectedImportedEmails"
													:value="user.email"
													class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
												/>
												<label :for="'imported-' + user.email" class="cursor-pointer select-none font-medium text-ink-gray-9 truncate">
													{{ user.full_name }} <span class="text-ink-gray-5">({{ user.email }})</span>
												</label>
											</div>
											<div class="flex-shrink-0 ml-2">
												<span
													v-if="user.is_new"
													class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 text-green-800 border border-green-200"
												>
													{{ __('Created') }}
												</span>
												<span
													v-else
													class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200"
												>
													{{ __('Skipped (Exists)') }}
												</span>
											</div>
										</div>

										<!-- Errors -->
										<div
											v-for="(err, idx) in importResults.errors"
											:key="'err-' + idx"
											class="flex items-start justify-between p-2.5 bg-red-50/50 hover:bg-red-50 transition-colors text-xs"
										>
											<div class="flex items-start gap-2 text-red-700 min-w-0">
												<FeatherIcon name="alert-circle" class="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
												<span class="font-mono break-all">{{ err }}</span>
											</div>
											<div class="flex-shrink-0 ml-2">
												<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-100 text-red-800 border border-red-200">
													{{ __('Failed') }}
												</span>
											</div>
										</div>

										<!-- Empty State inside list -->
										<div v-if="(!importResults.imported_users || !importResults.imported_users.length) && (!importResults.errors || !importResults.errors.length)" class="p-4 text-center text-ink-gray-5">
											{{ __('No logs recorded.') }}
										</div>
									</div>
								</div>
							</div>

							<!-- Batch Assignment section (only if there are imported users) -->
							<div v-if="importResults.imported_users && importResults.imported_users.length" class="space-y-3">
								<p class="text-sm text-ink-gray-6">
									{{ __('Select the onboarded/found students you want to assign to a batch.') }}
								</p>
								<div class="space-y-2 pt-2">
									<label class="text-xs font-semibold text-ink-gray-7">{{ __('Assign to Batch') }}</label>
									<Select
										v-model="importBatchAssignment"
										:options="batchOptionsForImport"
										:placeholder="__('Select a Batch')"
									/>
								</div>
							</div>
						</div>
					</div>
				</template>
				<template #actions>
					<div class="flex justify-end gap-2">
						<Button
							v-if="importResults || importError"
							variant="outline"
							@click="resetImportWizard"
						>
							{{ __('Reupload File') }}
						</Button>
						<Button variant="ghost" @click="closeImportModal">
							{{ !(importResults || importError) ? __('Cancel') : __('Close') }}
						</Button>
						<Button
							v-if="!(importResults || importError)"
							variant="solid"
							:loading="importResource.loading"
							:disabled="!csvFile"
							@click="triggerImport"
						>
							{{ __('Import & Onboard') }}
						</Button>
						<Button
							v-else-if="importResults && importResults.imported_users && importResults.imported_users.length"
							variant="solid"
							:loading="assignResource.loading"
							:disabled="!selectedImportedEmails.length || !importBatchAssignment"
							@click="triggerAssign"
						>
							{{ __('Assign to Batch') }}
						</Button>
					</div>
				</template>
			</Dialog>

			<!-- Add Student Manually Modal -->
			<Dialog
				v-model="showManualModal"
				:options="{
					title: manualModalTitle,
					size: 'lg',
				}"
			>
				<template #body-content>
					<div class="space-y-4">
						<p class="text-sm text-ink-gray-6">
							{{ __('Onboard a new student by entering their details. If they do not have an account, they will be registered and sent a welcome email to complete registration.') }}
						</p>
						
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div class="space-y-2">
								<label class="text-xs font-semibold text-ink-gray-7">{{ __('Full Name') }} <span class="text-red-500">*</span></label>
								<FormControl
									v-model="manualFullName"
									type="text"
									:placeholder="__('John Doe')"
									required
								/>
							</div>
							<div class="space-y-2">
								<label class="text-xs font-semibold text-ink-gray-7">{{ __('Email Address') }} <span class="text-red-500">*</span></label>
								<FormControl
									v-model="manualEmail"
									type="email"
									:placeholder="__('john@example.com')"
									required
								/>
							</div>
						</div>

						<div class="space-y-2">
							<label class="text-xs font-semibold text-ink-gray-7">{{ __('Assign to Batch (Optional)') }}</label>
							<Select
								v-model="manualBatch"
								:options="batchOptionsForImport"
								:placeholder="__('Select a Batch')"
							/>
						</div>

						<div v-if="manualError" class="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
							{{ manualError }}
						</div>
					</div>
				</template>
				<template #actions>
					<div class="flex justify-end gap-2">
						<Button variant="ghost" @click="closeManualModal">
							{{ __('Cancel') }}
						</Button>
						<Button
							variant="solid"
							:loading="manualResource.loading"
							:disabled="!manualEmail || !manualFullName"
							@click="triggerManualAdd"
						>
							{{ __('Add Student') }}
						</Button>
					</div>
				</template>
			</Dialog>
		</div>
		<div v-else>
			<div
				v-if="batches.data?.length"
				class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
			>
				<router-link
					v-for="batch in batches.data"
					:to="{ name: 'BatchDetail', params: { batchName: batch.name } }"
				>
					<BatchCard :batch="batch" />
				</router-link>
			</div>
			<EmptyState v-else-if="!batches.list.loading" type="Batches" />

			<div
				v-if="!batches.list.loading && batches.hasNextPage"
				class="flex justify-center mt-5"
			>
				<Button @click="batches.next()">
					{{ __('Load More') }}
				</Button>
			</div>
		</div>
	</div>
</template>
<script setup>
import {
	Avatar,
	Badge,
	Breadcrumbs,
	Button,
	call,
	Checkbox,
	createListResource,
	createResource,
	Dialog,
	Dropdown,
	FeatherIcon,
	FormControl,
	ListView as ListViewStudents,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	ListSelectBanner,
	Select,
	Switch,
	TabButtons,
	toast,
	Tooltip,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import BatchCard from '@/components/BatchCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const user = inject('$user')
const dayjs = inject('$dayjs')
const { brand } = sessionStore()
const start = ref(0)
const pageLength = ref(20)
const categories = ref([])
const currentCategory = ref(null)
const title = ref('')
const certification = ref(false)
const filters = ref({})
const is_student = computed(() => user.data?.is_student)
const currentTab = ref('all')
const orderBy = ref('start_date')
const readOnlyMode = window.read_only_mode
const router = useRouter()

const showTopTabs = computed(() => {
	return !!user.data?.is_moderator
})

const topTabs = computed(() => {
	return [
		{ label: __('Batches'), value: 'batches' },
		{ label: __('Students'), value: 'students' },
	]
})

const currentTopTab = ref('batches')

const studentColumns = computed(() => {
	return [
		{
			label: __('Student'),
			key: 'member_name',
			width: 2,
			icon: 'user',
			align: 'left',
		},
		{
			label: __('Assigned Batch'),
			key: 'batch_title',
			width: 1.5,
			icon: 'book',
			align: 'left',
		},
		{
			label: __('Date of Enrolment'),
			key: 'creation',
			width: 1.2,
			icon: 'calendar',
			align: 'left',
		},
		{
			label: __('Last Active'),
			key: 'last_active',
			width: 1.2,
			icon: 'clock',
			align: 'left',
		},
		{
			label: __('Overall Completion'),
			key: 'progress',
			width: 1.5,
			icon: 'percent',
			align: 'left',
		},
	]
})

const studentSearch = ref('')
const studentBatchFilter = ref('')
const studentSortBy = ref('creation desc')
const studentStart = ref(0)
const studentPageLength = ref(20)
const studentListItems = ref([])

const studentList = createResource({
	url: 'lms.lms.api.get_all_students_across_batches',
	makeParams() {
		return {
			search_term: studentSearch.value,
			batch_filter: studentBatchFilter.value,
			order_by: studentSortBy.value,
			start: studentStart.value,
			page_length: studentPageLength.value,
		}
	},
	auto: false,
	transform(data) {
		if (studentStart.value === 0) {
			studentListItems.value = data.data
		} else {
			studentListItems.value = [...studentListItems.value, ...data.data]
		}
		return data
	}
})

const loadMoreStudents = () => {
	studentStart.value += studentPageLength.value
	studentList.reload()
}

const showImportModal = ref(false)
const csvFile = ref(null)
const importBatchAssignment = ref('')
const importResults = ref(null)
const selectedImportedEmails = ref([])
const importError = ref('')
const inputKey = ref(0)

const handleCSVFileChange = (e) => {
	const file = e.target.files[0]
	if (file) {
		csvFile.value = file
	}
}

const batchOptionsForImport = computed(() => {
	const options = studentList.data?.batch_options || []
	return options.filter(o => o.value !== '' && o.value !== '__without_batch__')
})

const studentBatchFilterOptions = computed(() => {
	const options = studentList.data?.batch_options || []
	// Inject "Without Batch" after the first (All Batches) entry
	const base = options.filter(o => o.value !== '__without_batch__')
	const insertAt = base.length > 0 ? 1 : base.length
	return [
		...base.slice(0, insertAt),
		{ label: __('Without Batch'), value: '__without_batch__' },
		...base.slice(insertAt),
	]
})

const toggleSelectAllImported = (e) => {
	if (e.target.checked) {
		selectedImportedEmails.value = (importResults.value?.imported_users || []).map(u => u.email)
	} else {
		selectedImportedEmails.value = []
	}
}

const importResource = createResource({
	url: 'lms.lms.api.import_students_csv',
	onSuccess(data) {
		importResults.value = data
		if (data.imported_users) {
			selectedImportedEmails.value = data.imported_users.map(u => u.email)
		} else {
			selectedImportedEmails.value = []
		}
	},
	onError(err) {
		importError.value = err.messages ? err.messages.join('\n') : err.message || __('Failed to import students.')
	}
})

const assignResource = createResource({
	url: 'lms.lms.api.assign_students_to_batch',
	onSuccess(data) {
		closeImportModal()
		studentStart.value = 0
		studentList.reload()
		toast.success(__('Students assigned to batch successfully.'))
	}
})

const triggerImport = () => {
	if (!csvFile.value) return
	importError.value = ''
	if (importResource) {
		importResource.error = null
	}
	
	const reader = new FileReader()
	reader.onload = (e) => {
		const text = e.target.result
		importResource.submit({
			file_content: text
		})
	}
	reader.readAsText(csvFile.value)
}

const triggerAssign = () => {
	if (!selectedImportedEmails.value.length || !importBatchAssignment.value) return
	assignResource.submit({
		students: selectedImportedEmails.value,
		batch: importBatchAssignment.value
	})
}

const resetImportWizard = () => {
	csvFile.value = null
	importResults.value = null
	importBatchAssignment.value = ''
	selectedImportedEmails.value = []
	importError.value = ''
	inputKey.value++
	if (importResource) {
		importResource.error = null
	}
}

const closeImportModal = () => {
	showImportModal.value = false
	resetImportWizard()
}

const showManualModal = ref(false)
const manualEmail = ref('')
const manualFullName = ref('')
const manualBatch = ref('')
const manualError = ref('')
const manualModalTitle = ref(__('Add Student Manually'))

const openManualModalForStudent = (row) => {
	manualEmail.value = row.email || ''
	manualFullName.value = row.member_name || ''
	manualBatch.value = ''
	manualError.value = ''
	manualModalTitle.value = __('Assign Student to Batch')
	showManualModal.value = true
}

const manualResource = createResource({
	url: 'lms.lms.api.add_student_manually',
	onSuccess(data) {
		closeManualModal()
		studentStart.value = 0
		studentList.reload()
		toast.success(__('Student assigned to batch successfully.'))
	},
	onError(err) {
		manualError.value = err.messages ? err.messages.join('\n') : err.message || __('Failed to add student.')
	}
})

const triggerManualAdd = () => {
	if (!manualEmail.value || !manualFullName.value) return
	manualError.value = ''
	manualResource.submit({
		email: manualEmail.value,
		full_name: manualFullName.value,
		batch: manualBatch.value
	})
}

const closeManualModal = () => {
	showManualModal.value = false
	manualEmail.value = ''
	manualFullName.value = ''
	manualBatch.value = ''
	manualError.value = ''
	manualModalTitle.value = __('Add Student Manually')
}

const getAvatarStyle = (name) => {
	if (!name) return { backgroundColor: '#f3f4f6', color: '#1f2937' }
	
	let hash = 0
	for (let i = 0; i < name.length; i++) {
		hash = name.charCodeAt(i) + ((hash << 5) - hash)
	}
	
	const palettes = [
		{ bg: '#fee2e2', text: '#991b1b' }, // red
		{ bg: '#fef3c7', text: '#92400e' }, // amber
		{ bg: '#dcfce7', text: '#166534' }, // green
		{ bg: '#ccfbf1', text: '#115e59' }, // teal
		{ bg: '#e0f2fe', text: '#075985' }, // sky
		{ bg: '#e0e7ff', text: '#3730a3' }, // indigo
		{ bg: '#f3e8ff', text: '#6b21a8' }, // purple
		{ bg: '#fce7f3', text: '#9d174d' }, // pink
	]
	
	const index = Math.abs(hash) % palettes.length
	return {
		backgroundColor: palettes[index].bg,
		color: palettes[index].text
	}
}

const toggleSort = (field) => {
	let currentField = studentSortBy.value.split(' ')[0]
	let currentDir = studentSortBy.value.split(' ')[1] || 'asc'
	
	if (currentField === field) {
		studentSortBy.value = `${field} ${currentDir === 'asc' ? 'desc' : 'asc'}`
	} else {
		studentSortBy.value = `${field} desc`
	}
}

watch([studentSearch, studentBatchFilter, studentSortBy], () => {
	if (currentTopTab.value === 'students') {
		studentStart.value = 0
		studentList.reload()
	}
})

const disableStudentResource = createResource({
	url: 'lms.lms.api.bulk_toggle_student_accounts',
	onSuccess() {
		studentStart.value = 0
		studentList.reload()
		toast.success(__('Student accounts updated successfully.'))
	},
	onError(err) {
		toast.error(err.messages?.[0] || err.message || __('Failed to update accounts.'))
	},
})

const unenrollStudentResource = createResource({
	url: 'lms.lms.api.bulk_unenroll_students_from_batch',
	onSuccess() {
		studentStart.value = 0
		studentList.reload()
		toast.success(__('Students unenrolled successfully.'))
	},
	onError(err) {
		toast.error(err.messages?.[0] || err.message || __('Failed to unenroll students.'))
	},
})

const areAllSelectedStudentsDisabled = (selections) => {
	if (!selections || !selections.size) return false
	const enrollmentNames = Array.from(selections)
	return enrollmentNames.every(n => {
		const student = studentListItems.value.find(s => s.name === n)
		return student && student.enabled === 0
	})
}

const handleBulkToggleStudentAccounts = (selections, isChecked, unselectAll) => {
	if (!selections.size) return
	const enrollmentNames = Array.from(selections)
	const emails = enrollmentNames
		.map(n => studentListItems.value.find(s => s.name === n)?.email)
		.filter(Boolean)
	if (!emails.length) return

	const targetEnabled = isChecked ? 0 : 1
	disableStudentResource.submit({ emails, enabled: targetEnabled })
	unselectAll()
}

const handleUnenrollStudents = (selections, unselectAll) => {
	if (!selections.size) return
	const enrollmentNames = Array.from(selections)
	unenrollStudentResource.submit({ enrollment_names: enrollmentNames })
	unselectAll()
}

const toggleStudentAccountResource = createResource({
	url: 'lms.lms.api.toggle_student_account',
	onSuccess(data) {
		const status = data.enabled ? __('enabled') : __('disabled')
		toast.success(__('Student account has been {0}.').format(status))
	},
	onError(err) {
		toast.error(err.messages?.[0] || err.message || __('Failed to update account status.'))
		// revert the local change on error
		studentStart.value = 0
		studentList.reload()
	},
})

const handleToggleStudentAccount = (row, isChecked) => {
	const newEnabled = isChecked ? 0 : 1
	// optimistic update
	row.enabled = newEnabled
	toggleStudentAccountResource.submit({ email: row.email, enabled: newEnabled })
}

onMounted(() => {
	setFiltersFromQuery()
	updateBatches()
	categories.value = [
		{
			label: '',
			value: null,
		},
	]
})

const setFiltersFromQuery = () => {
	let queries = new URLSearchParams(location.search)
	title.value = queries.get('title') || ''
	currentCategory.value = queries.get('category') || null
	certification.value = queries.get('certification') || false
}

const batches = createListResource({
	doctype: 'LMS Batch',
	url: 'lms.lms.utils.get_batches',
	cache: ['batches', user.data?.name],
	pageLength: pageLength.value,
	start: start.value,
})

const setCategories = (data) => {
	let allCategories = data.map((batch) => batch.category)
	allCategories = allCategories.filter(
		(category, index) => allCategories.indexOf(category) === index && category
	)
	if (categories.value.length <= allCategories.length) {
		updateCategories(data)
	}
}

const updateBatches = () => {
	if (currentTopTab.value === 'students') return
	updateFilters()
	batches.update({
		filters: filters.value,
		orderBy: orderBy.value,
	})
	batches.reload().then((data) => {
		setCategories(data)
	})
}

const updateFilters = () => {
	updateCategoryFilter()
	updateTitleFilter()
	updateCertificationFilter()
	updateTabFilter()
	updateStudentFilter()
	setQueryParams()
}

const updateCategoryFilter = () => {
	if (currentCategory.value) {
		filters.value['category'] = currentCategory.value
	} else {
		delete filters.value['category']
	}
}

const updateTitleFilter = () => {
	if (title.value) {
		filters.value['title'] = ['like', `%${title.value}%`]
	} else {
		delete filters.value['title']
	}
}

const updateCertificationFilter = () => {
	if (certification.value) {
		filters.value['certification'] = 1
	} else {
		delete filters.value['certification']
	}
}

const updateTabFilter = () => {
	orderBy.value = 'start_date'
	if (!user.data) {
		return
	}
	if (currentTab.value == 'enrolled' && is_student.value) {
		filters.value['enrolled'] = 1
		delete filters.value['start_date']
		delete filters.value['published']
		orderBy.value = 'start_date desc'
	} else if (is_student.value) {
		delete filters.value['enrolled']
	} else {
		delete filters.value['start_date']
		delete filters.value['published']
		orderBy.value = 'start_date desc'
		if (currentTab.value == 'upcoming') {
			filters.value['start_date'] = ['>=', dayjs().format('YYYY-MM-DD')]
			filters.value['published'] = 1
			orderBy.value = 'start_date'
		} else if (currentTab.value == 'archived') {
			filters.value['start_date'] = ['<=', dayjs().format('YYYY-MM-DD')]
		} else if (currentTab.value == 'unpublished') {
			filters.value['published'] = 0
		}
	}
}

const updateStudentFilter = () => {
	if (!user.data || (is_student.value && currentTab.value != 'enrolled')) {
		filters.value['start_date'] = ['>=', dayjs().format('YYYY-MM-DD')]
		filters.value['published'] = 1
	}
}

const setQueryParams = () => {
	let queries = new URLSearchParams(location.search)
	let filterKeys = {
		title: title.value,
		category: currentCategory.value,
		certification: certification.value,
	}

	Object.keys(filterKeys).forEach((key) => {
		if (filterKeys[key]) {
			queries.set(key, filterKeys[key])
		} else {
			queries.delete(key)
		}
	})

	history.replaceState(
		{},
		'',
		`${location.pathname}${queries.size > 0 ? `?${queries.toString()}` : ''}`
	)
}

const updateCategories = (data) => {
	data.forEach((batch) => {
		if (
			batch.category &&
			!categories.value.find((category) => category.value === batch.category)
		)
			categories.value.push({
				label: batch.category,
				value: batch.category,
			})
	})
}

watch(currentTab, () => {
	updateBatches()
})

watch(currentTopTab, () => {
	if (currentTopTab.value === 'students') {
		studentStart.value = 0
		studentList.reload()
	} else {
		updateBatches()
	}
})

const batchTabs = computed(() => {
	let tabs = [
		{
			label: __('All'),
			value: 'all',
		},
	]

	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	) {
		tabs.push({ label: __('Upcoming'), value: 'upcoming' })
		tabs.push({ label: __('Archived'), value: 'archived' })
		tabs.push({ label: __('Unpublished'), value: 'unpublished' })
	} else if (user.data) {
		tabs.push({ label: __('Enrolled'), value: 'enrolled' })
	}
	return tabs
})

const canCreateBatch = () => {
	if (readOnlyMode) return false
	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
		return true
	return false
}

const breadcrumbs = computed(() => [
	{
		label: __('Batches'),
		route: { name: 'Batches' },
	},
])

usePageMeta(() => {
	return {
		title: __('Batches'),
		icon: brand.favicon,
	}
})
</script>
