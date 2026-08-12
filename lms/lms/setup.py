import frappe

def setup_signature_custom_field():
	if not frappe.db.exists("Custom Field", {"dt": "User", "fieldname": "signature"}):
		custom_field = frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "User",
			"fieldname": "signature",
			"fieldtype": "Attach Image",
			"label": "Signature",
			"insert_after": "user_image"
		})
		custom_field.insert(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def ensure_user_signature_field():
	setup_signature_custom_field()
	return "User signature field is ready."
