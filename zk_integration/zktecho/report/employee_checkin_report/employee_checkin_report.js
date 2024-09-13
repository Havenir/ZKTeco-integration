// Copyright (c) 2024, Daniyal AHmad and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Checkin Report"] = {
    "filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "width": "80",
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "width": "80",
        },
    ],
    
    formatter: function(value, row, column, data, default_formatter) {
        if (data) {
            if (column.fieldname === "select") {
                return `<input type='checkbox' class='row-checkbox' data-name='${data.checkin_date}' ${data.select ? "checked" : ""} onchange="toggle_select('${data.checkin_date}', this.checked)">`;
            } else {
                return default_formatter(value, row, column, data);
            }
        }
    },

    onload: function(report) {
        // Add "Attendance Request" and "Leave Application" buttons to the toolbar
        report.page.add_inner_button(__('Attendance Request'), function() {
            handle_attendance_request();
        }).addClass('attendance-request-btn').hide();

        report.page.add_inner_button(__('Leave Application'), function() {
            handle_leave_application();
        }).addClass('leave-application-btn').hide();
    }
};

// Toggle selection of rows
function toggle_select(checkin_date, is_checked) {
    frappe.query_report.data.forEach(row => {
        if (row.checkin_date === checkin_date) {
            row.select = is_checked ? 1 : 0;
        }
    });
    update_button_visibility();
}

// Update button visibility based on row selection
function update_button_visibility() {
    const selected_rows = frappe.query_report.data.filter(row => row.select === 1);
	console.log(selected_rows);
    if (selected_rows.length > 0) {
        $('.attendance-request-btn').show();
        $('.leave-application-btn').show();
    } else {
        $('.attendance-request-btn').hide();
        $('.leave-application-btn').hide();
    }
}

// Function to handle Attendance Request creation
async function handle_attendance_request() {
    const selected_rows = frappe.query_report.data.filter(row => row.select === 1 && row.checkin_date);
    if (selected_rows.length > 0) {
        frappe.confirm(
            __('Do you want to create Attendance Request for the selected employees?'),
            function() {
                // Create Attendance Request records
                create_records("Attendance Request", selected_rows);
            }
        );
    } else {
        frappe.msgprint(__('Please select at least one row.'));
    }
}

// Function to handle Leave Application creation
async function handle_leave_application() {
    const selected_rows = frappe.query_report.data.filter(row => row.select === 1 && row.checkin_date);
    if (selected_rows.length > 0) {
        frappe.prompt({
            fieldtype: 'Link',
            fieldname: 'leave_type',
            label: __('Leave Type'),
            options: 'Leave Type',
            reqd: true
        },
        function(values) {
            const leave_type = values.leave_type;
            // Create Leave Application records with the selected leave type
            create_records("Leave Application", selected_rows, leave_type);
        },
        __('Select Leave Type'),
        __('Create Leave Application'));
    } else {
        frappe.msgprint(__('Please select at least one row.'));
    }
}

// Function to create records in specified doctype (Attendance Request or Leave Application)
function create_records(doctype, rows, leave_type = null) {
    rows.forEach(row => {
        let doc = {
            doctype: doctype,
            employee: row.employee,
            from_date: row.checkin_date,
            to_date: row.checkin_date,
            // Add more fields here if needed
        };

        if (doctype === "Leave Application" && leave_type) {
            doc.leave_type = leave_type;
        }

        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: doc
            },
            callback: function(response) {
                if (!response.exc) {
                    frappe.msgprint(__('Successfully created {0} for {1}', [doctype, row.employee]));
                }
            }
        });
    });
}
