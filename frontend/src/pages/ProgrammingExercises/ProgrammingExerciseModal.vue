<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Add a programming exercise to your lesson'),
			size: 'xl',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick: () => {
						saveExercise()
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="text-base">
				<Link
					v-model="exercise"
					doctype="LMS Programming Exercise"
					:label="__('Select a Programming Exercise')"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { Dialog } from 'frappe-ui'
import { onMounted, nextTick, ref } from 'vue'
import Link from '@/components/Controls/Link.vue'

const show = ref(false)
const exercise = ref(null)

const props = defineProps({
	onSave: {
		type: Function,
		required: true,
	},
})

onMounted(async () => {
	await nextTick()
	show.value = true
})

const saveExercise = () => {
	props.onSave(exercise.value)
	show.value = false
}
</script>

<style>
[data-dialog='Add a programming exercise to your lesson'] .dialog-content {
	overflow: visible !important;
	border-radius: 12px !important;
}
[data-dialog='Add a programming exercise to your lesson'] .dialog-content > :first-child {
	border-top-left-radius: 12px !important;
	border-top-right-radius: 12px !important;
}
[data-dialog='Add a programming exercise to your lesson'] .dialog-content > :last-child {
	border-bottom-left-radius: 12px !important;
	border-bottom-right-radius: 12px !important;
}
</style>
