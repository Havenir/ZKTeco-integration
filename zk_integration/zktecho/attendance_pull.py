import frappe
from frappe.model.document import Document
from zk import ZK, const
from frappe.utils import get_datetime_str
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def test_connection(**args):
    doc_name = args.get("baseName")
    record = frappe.get_doc("Attendance Sync", doc_name)
    emp_device_list = record.selected_device
    for row in emp_device_list:
        device_name = row.devices
        device_doc = frappe.get_doc("Attendance Devices", device_name)

        if device_doc:
            device_ip = str(device_doc.ip)
            device_port = int(device_doc.port)
            device_password = int(device_doc.password)

            conn = connect_to_device(device_ip, device_port, device_password)
            if conn:
                frappe.msgprint(f"Connected to device {device_name}")
            else:
                frappe.msgprint(f"Failed to connect to device {device_name}")

    return True



def connect_to_device(device_ip, device_port, device_password):
    zk = ZK(device_ip, port=device_port, timeout=5, password=device_password, force_udp=False, ommit_ping=False)
    conn = None
    try:
        conn = zk.connect()
        frappe.msgprint(f"Connection to device {device_ip} successful")
        conn.test_voice(index=10)
        return conn
    except Exception as e:
        frappe.msgprint(f"Failed to connect to device {device_ip}: {str(e)}")
        return None
    finally:
        if conn:
            conn.disable_device()
            conn.disconnect()



@frappe.whitelist(allow_guest=True)
def attendance_pull(**args):
    doc_name = args.get("baseName")
    record = frappe.get_doc("Attendance Sync", doc_name)
    emp_device_list = record.selected_device
    start_date_str = str(record.get("from_date"))
    end_date_str = str(record.get("to_date"))
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    print(start_date)

    if start_date is None or end_date is None:
        frappe.throw("Please provide start and end date")
    else:
        for row in emp_device_list:
            device_name = row.devices
            device_doc = frappe.get_doc("Attendance Devices", device_name)
    
            if device_doc:
                device_ip = str(device_doc.ip)
                device_port = int(device_doc.port)
                device_password = int(device_doc.password)
    
                conn = retrieving_attendance(device_ip, device_port, device_password, start_date, end_date)
                if conn:
                    frappe.msgprint(f"Connected to device {device_name}")
                    device_doc.db_set("last_sync", frappe.utils.now_datetime())
                    device_doc.db_set("sync_status", "Successfull")


                    
                else:
                    frappe.msgprint(f"Failed to connect to device {device_name}")
                    device_doc.db_set("last_sync", frappe.utils.now_datetime())
                    device_doc.db_set("sync_status", "Unuccessfull")

    
        return True

from datetime import datetime

def retrieving_attendance(device_ip, device_port, device_password, start_date, end_date):
    zk = ZK(device_ip, port=device_port, timeout=5, password=device_password, force_udp=False, ommit_ping=False)
    conn = None

    try:
        conn = zk.connect()
        all_logs = conn.get_attendance()
        print('Total attendance logs:', len(all_logs))

        for log in all_logs:
            log_time = log.timestamp
            print(log_time)
            log_type = 'IN' if log.status == 1 else 'OUT'

            if start_date.date() <= log_time.date() <= end_date.date():
                
                formatted_time = log_time.strftime('%Y-%m-%d %H:%M:%S')
                employee = frappe.get_value("Employee", {"attendance_device_id": log.user_id}, "name")

                if employee:
                    existing_checkin = frappe.get_value(
                        "Employee Checkin",
                        {"employee": employee, "time": formatted_time},
                        "name"
                    )
                    
                    if not existing_checkin:
                        check_in = frappe.new_doc("Employee Checkin")
                        check_in.employee = employee
                        check_in.time = formatted_time
                        check_in.log_type = log_type
                        check_in.attendance_device_id = log.user_id

                        try:
                            check_in.insert()
                            frappe.msgprint("Employee Check In created successfully for", employee)
                        except Exception as e:
                            frappe.msgprint("Error creating check-in record:", str(e))
                    else:
                        frappe.msgprint("Duplicate entry found for", employee)
                else:
                    frappe.msgprint("Employee not found for user_id:", log.user_id)
        return True

    except Exception as e:
        frappe.msgprint('Process terminated:', str(e))
        return False

    finally:
        if conn:
            conn.disable_device()
            conn.disconnect()
