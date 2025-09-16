# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import json
from typing import Optional, TypedDict

import frappe
from frappe import _, cstr
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import escape_html
from frappe.utils.jinja_globals import is_rtl
from frappe.www.printview import (
	get_letter_head,
	get_print_format_doc,
	get_print_style,
	get_rendered_template,
	set_link_titles,
	validate_print_permission,
)

no_cache = 1


class ESignContext(TypedDict):
	body: str
	print_style: str
	comment: str
	title: str
	lang: str
	layout_direction: str
	doctype: str
	name: str
	key: str
	has_signature_fields: bool
	signature_fields: list


def get_context(context) -> ESignContext:
	"""Build context for e-signature page"""
	if not ((frappe.form_dict.doctype and frappe.form_dict.name) or frappe.form_dict.doc):
		return ESignContext(
			print_style="",
			comment="",
			title="Error",
			lang="en",
			layout_direction="ltr",
			doctype="",
			name="",
			key="",
			has_signature_fields=False,
			signature_fields=[],
			body=f"""
<h1>Error</h1>
<p>Parameters doctype and name required</p>
<pre>{escape_html(frappe.as_json(frappe.form_dict, indent=2))}</pre>
""",
		)

	if frappe.form_dict.doc:
		doc = frappe.form_dict.doc
	else:
		doc = frappe.get_lazy_doc(frappe.form_dict.doctype, frappe.form_dict.name)

	set_link_titles(doc)

	settings = frappe.parse_json(frappe.form_dict.settings)
	letterhead = frappe.form_dict.letterhead or None
	meta = frappe.get_meta(doc.doctype)
	print_format = get_print_format_doc(None, meta=meta)

	# Check if document has signature fields and if they're allowed for signing
	signature_fields = get_signature_fields(doc, meta)
	has_signature_fields = bool(signature_fields)

	if not has_signature_fields:
		body = f"""
<h1>No Signature Required</h1>
<p>This document does not have any signature fields available for signing.</p>
"""
	else:
		body = get_rendered_template(
			doc,
			print_format=print_format,
			meta=meta,
			trigger_print=frappe.form_dict.trigger_print,
			no_letterhead=frappe.form_dict.no_letterhead,
			letterhead=letterhead,
			settings=settings,
		)

	# Include selected print format name in access log
	print_format_name = getattr(print_format, "name", "Standard")

	make_access_log(
		doctype=frappe.form_dict.doctype,
		document=frappe.form_dict.name,
		file_type="E-Sign",
		method="E-Sign Portal",
		page=f"Print Format: {print_format_name}",
	)

	return {
		"body": body,
		"print_style": get_print_style(frappe.form_dict.style, print_format),
		"comment": frappe.session.user,
		"title": frappe.utils.strip_html(cstr(doc.get_title() or doc.name)),
		"lang": frappe.local.lang,
		"layout_direction": "rtl" if is_rtl() else "ltr",
		"doctype": frappe.form_dict.doctype,
		"name": frappe.form_dict.name,
		"key": frappe.form_dict.get("key"),
		"print_format": print_format_name,
		"letterhead": letterhead,
		"no_letterhead": frappe.form_dict.no_letterhead,
		"has_signature_fields": has_signature_fields,
		"signature_fields": signature_fields,
	}


def get_signature_fields(doc, meta):
	"""Get list of signature fields that are available for signing"""
	signature_fields = []
	
	for field in meta.fields:
		if field.fieldtype == "Signature":
			# Check if field is empty (needs signature)
			if not doc.get(field.fieldname):
				# If document is submittable, check allow_on_submit
				if meta.is_submittable:
					if field.allow_on_submit:
						signature_fields.append({
							"fieldname": field.fieldname,
							"label": field.label or field.fieldname.title(),
							"description": field.description,
						})
				else:
					# Non-submittable documents allow all signature fields
					signature_fields.append({
						"fieldname": field.fieldname,
						"label": field.label or field.fieldname.title(),
						"description": field.description,
					})
	
	return signature_fields


@frappe.whitelist(allow_guest=True)
def save_signature():
	"""Save signature data to the document field"""
	doctype = frappe.form_dict.get("doctype")
	name = frappe.form_dict.get("name") 
	fieldname = frappe.form_dict.get("fieldname")
	signature_data = frappe.form_dict.get("signature_data")
	key = frappe.form_dict.get("key")

	if not all([doctype, name, fieldname, signature_data]):
		frappe.throw(_("Missing required parameters"))

	# Validate signature data format (should be data:image/png;base64,...)
	if not signature_data.startswith("data:image/"):
		frappe.throw(_("Invalid signature data format"))

	# Limit signature data size (max 1MB)
	if len(signature_data) > 1024 * 1024:
		frappe.throw(_("Signature data too large"))

	try:
		doc = frappe.get_doc(doctype, name)
		
		# Validate permissions
		validate_signature_permission(doc, key)
		
		# Validate that the field exists and is a signature field
		meta = frappe.get_meta(doctype)
		field = meta.get_field(fieldname)
		
		if not field or field.fieldtype != "Signature":
			frappe.throw(_("Invalid signature field"))
			
		# Check if field is empty
		if doc.get(fieldname):
			frappe.throw(_("Signature field already has a value"))
			
		# For submittable documents, check allow_on_submit
		if meta.is_submittable and not field.allow_on_submit:
			frappe.throw(_("Signature field does not allow modification after submission"))
			
		# Validate that this field should be available for signing
		available_fields = get_signature_fields(doc, meta)
		field_available = any(f["fieldname"] == fieldname for f in available_fields)
		
		if not field_available:
			frappe.throw(_("Signature field is not available for signing"))
		
		# Set the signature value
		doc.set(fieldname, signature_data)
		
		# Use flags to bypass some validations during signature save
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_permissions = True
		doc.flags.in_signature_capture = True
		
		doc.save()
		
		frappe.db.commit()
		
		# Log the signature capture for audit trail
		frappe.logger("esign").info(f"Signature captured for {doctype} {name} field {fieldname}")
		
		return {"status": "success", "message": _("Signature saved successfully")}
		
	except frappe.ValidationError as e:
		frappe.db.rollback()
		frappe.throw(_("Validation Error: {0}").format(str(e)))
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "E-Signature Save Error")
		frappe.throw(_("Failed to save signature: {0}").format(str(e)))


def validate_signature_permission(doc, key):
	"""Validate if user has permission to sign the document"""
	# Try normal print permissions first
	try:
		validate_print_permission(doc)
		return
	except:
		pass
	
	# If normal permissions fail, check for valid key
	if not key:
		frappe.throw(_("Access denied. No valid key provided."))
		
	from frappe.www.printview import validate_key
	if validate_key(key, doc) is False:
		frappe.throw(_("Access denied. Invalid or expired key."))