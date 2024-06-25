frappe.ui.form.on('Attendance Sync', {
    refresh: function(frm) {
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'zk_integration.zktecho.attendance_pull.test_connection',
                args: {
                    baseName: frm.doc.name,
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                }
            });
        }, __('Actions'));

        frm.add_custom_button(__('Sync Attendance'), function() {
            if (frm.doc.select_frequency === "Manually") {
                if (!frm.doc.from_date || !frm.doc.to_date) {
                    frappe.throw(__('Please provide both From Date and To Date.'));
                } else {
                    frappe.call({
                        method: 'zk_integration.zktecho.attendance_pull.attendance_pull',
                        args: {
                            baseName: frm.doc.name,
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint(r.message);
                            }
                        }
                    });
                }
            } else {
                frappe.throw(__('Frequency must be set to Manually to sync attendance.'));
            }
        }, __('Actions'));
    }
});
