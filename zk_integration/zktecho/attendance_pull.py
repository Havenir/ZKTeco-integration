import frappe
from zk import ZK
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
    zk = ZK(
        device_ip,
        port=device_port,
        timeout=5,
        password=device_password,
        force_udp=False,
        ommit_ping=False,
    )
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
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

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
                record.db_set("status", "Initiated")

                frappe.enqueue(
                    "zk_integration.zktecho.attendance_pull.retrieving_attendance",  # noqa
                    queue="long",
                    device_ip=device_ip,
                    device_port=device_port,
                    device_password=device_password,
                    start_date=start_date,
                    end_date=end_date,
                    record_name=record.name,
                    device_doc_name=device_doc.name,
                )

        return True


def retrieving_attendance(
    device_ip,
    device_port,
    device_password,
    start_date,
    end_date,
    record_name,
    device_doc_name,
):
    record = frappe.get_doc("Attendance Sync", record_name)
    device_doc = frappe.get_doc("Attendance Devices", device_doc_name)
    record.db_set("status", "In-Progress")
    zk = ZK(
        device_ip,
        port=device_port,
        timeout=5,
        password=device_password,
        force_udp=False,
        ommit_ping=False,
    )
    conn = None

    try:
        conn = zk.connect()
        all_logs = conn.get_attendance()

        for log in all_logs:
            log_time = log.timestamp
            log_type = "IN" if log.status == 1 else "OUT"

            if start_date.date() <= log_time.date() <= end_date.date():
                formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")
                employee = frappe.get_value(
                    "Employee", {"attendance_device_id": log.user_id}, "name"
                )

                if employee:
                    existing_checkin = frappe.get_value(
                        "Employee Checkin",
                        {"employee": employee, "time": formatted_time},
                        "name",
                    )

                    if not existing_checkin:
                        check_in = frappe.new_doc("Employee Checkin")
                        check_in.employee = employee
                        check_in.time = formatted_time
                        check_in.log_type = log_type
                        check_in.attendance_device_id = log.user_id

                        try:
                            check_in.insert()
                            record.db_set("status", "Completed")
                            device_doc.db_set("last_sync", frappe.utils.now_datetime())  # noqa
                            device_doc.db_set("sync_status", "Successfull")

                        except Exception as e:
                            frappe.msgprint("Error creating check-in record:", str(e))  # noqa
                            record.db_set("status", "Failed")
                            device_doc.db_set("last_sync", frappe.utils.now_datetime())  # noqa
                            device_doc.db_set("sync_status", "Unuccessfull")

                    else:
                        frappe.msgprint("Duplicate entry found for", employee)
                        record.db_set("status", "Failed")

                else:
                    frappe.msgprint("Employee not found for user_id:", log.user_id)  # noqa
                    record.db_set("status", "Failed")

    except Exception as e:
        frappe.msgprint("Process terminated:", str(e))
        record.db_set("status", "Failed")
        device_doc.db_set("last_sync", frappe.utils.now_datetime())  # noqa
        device_doc.db_set("sync_status", "Unuccessfull")

        return False
