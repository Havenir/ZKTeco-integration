// Copyright (c) 2023, Daniyal AHmad and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Sync', {
    check: function(frm) {
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
    },
	sync_attendance: function(frm) {
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
});

		
		
		
		
