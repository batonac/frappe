frappe.listview_settings["Web Form"] = {
	add_fields: ["title", "published"],
	get_indicator: function (doc) {
		if (doc.published) {
			return [__("Published"), "green", "published,=,1"];
		} else {
			return [__("Not Published"), "gray", "published,=,0"];
		}
	},
};

frappe.ui.form.WebFormQuickEntryForm = class WebFormQuickEntryForm extends (
	frappe.ui.form.QuickEntryForm
) {
	open_form_if_not_list() {
		frappe.set_route("Form", this.doc.doctype, this.doc.name);
	}
};
