// E-Signature Button for Forms
// This script adds an e-signature button to forms that have associated esign-enabled web forms

frappe.provide('frappe.esign');

frappe.esign = {
	add_esign_button: function(frm) {
		// Only add button if document exists and is saved
		if (!frm.doc || !frm.doc.name || frm.doc.__islocal) {
			return;
		}

		// Check if there are esign-enabled web forms for this doctype
		frappe.call({
			method: 'frappe.website.doctype.web_form.web_form.get_esign_webforms_for_doctype',
			args: {
				doctype: frm.doc.doctype
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					frappe.esign.create_esign_button(frm, r.message);
				}
			}
		});
	},

	create_esign_button: function(frm, webforms) {
		// Remove existing button if present
		frm.remove_custom_button(__('Send for e-Signature'));

		// Add the e-signature button
		frm.add_custom_button(__('Send for e-Signature'), function() {
			frappe.esign.show_esign_dialog(frm, webforms);
		}, __('Actions'));
	},

	show_esign_dialog: function(frm, webforms) {
		const dialog = new frappe.ui.Dialog({
			title: __('Send Document for e-Signature'),
			fields: [
				{
					fieldname: 'webform',
					fieldtype: 'Select',
					label: __('Select Web Form'),
					options: webforms.map(w => ({ label: w.title, value: w.name })),
					reqd: 1,
					description: __('Choose the web form to use for e-signature')
				},
				{
					fieldname: 'print_format',
					fieldtype: 'Link',
					label: __('Print Format'),
					options: 'Print Format',
					filters: {
						doc_type: frm.doc.doctype
					},
					default: 'Standard',
					description: __('Select print format for the document')
				},
				{
					fieldname: 'recipients',
					fieldtype: 'Table',
					label: __('Recipients'),
					cannot_add_rows: false,
					cannot_delete_rows: false,
					fields: [
						{
							fieldname: 'email',
							fieldtype: 'Data',
							label: __('Email Address'),
							options: 'Email',
							in_list_view: 1,
							reqd: 1
						}
					],
					reqd: 1,
					description: __('Add email addresses of people who need to sign this document')
				},
				{
					fieldname: 'email_message',
					fieldtype: 'Text Editor',
					label: __('Email Message'),
					description: __('Custom message to include in the email (optional). The e-signature link will be automatically added.')
				}
			],
			size: 'large',
			primary_action_label: __('Send e-Signature Email'),
			primary_action: function(values) {
				if (!values.recipients || values.recipients.length === 0) {
					frappe.msgprint(__('Please add at least one recipient'));
					return;
				}

				const recipients = values.recipients.map(r => r.email);

				frappe.call({
					method: 'frappe.website.doctype.web_form.web_form.send_esign_email',
					args: {
						doctype: frm.doc.doctype,
						docname: frm.doc.name,
						webform_name: values.webform,
						print_format: values.print_format || 'Standard',
						email_message: values.email_message || '',
						recipients: recipients
					},
					callback: function(r) {
						if (r.message && r.message.status === 'success') {
							frappe.msgprint({
								title: __('Success'),
								message: r.message.message,
								indicator: 'green'
							});
							dialog.hide();
						}
					}
				});
			}
		});

		// Pre-populate with contact email if available
		const contact_fields = ['email_id', 'email', 'contact_email', 'customer_email'];
		let default_email = null;
		
		for (let field of contact_fields) {
			if (frm.doc[field]) {
				default_email = frm.doc[field];
				break;
			}
		}

		if (default_email) {
			dialog.set_value('recipients', [{ email: default_email }]);
		}

		dialog.show();
	}
};

// Hook into form refresh to add e-signature button
$(document).on('form-refresh', function(e, frm) {
	if (frm && frm.doc) {
		setTimeout(function() {
			frappe.esign.add_esign_button(frm);
		}, 100);
	}
});

// Also hook into form load for immediate execution
frappe.ui.form.on('*', {
	refresh: function(frm) {
		frappe.esign.add_esign_button(frm);
	}
});