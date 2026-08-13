import frappe

def execute():
	"""
	Add composite database indexes to speed up analytics logging & metrics calculations.
	"""
	indexes = [
		("LMS Page View Log", "idx_pv_course_member_creation", ["course", "member", "creation"]),
		("LMS Quiz Submission", "idx_qs_course_member_creation", ["course", "member", "creation"]),
		("LMS Quiz Submission", "idx_qs_course_member_pct", ["course", "member", "percentage"]),
		("LMS Enrollment", "idx_env_course_member", ["course", "member"]),
	]

	for doctype, index_name, columns in indexes:
		try:
			table = f"`tab{doctype}`"
			cols_str = ", ".join([f"`{col}`" for col in columns])
			# Check if index already exists
			existing = frappe.db.sql(f"SHOW INDEX FROM {table} WHERE Key_name = %s", (index_name,))
			if not existing:
				frappe.db.sql(f"CREATE INDEX `{index_name}` ON {table} ({cols_str})")
		except Exception as e:
			frappe.log_error(title=f"Failed to create index {index_name}", message=str(e))
