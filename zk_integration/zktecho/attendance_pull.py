
""" ZKTeco attendance pull """
import frappe
from zk import ZK
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def test_connection(baseName):
    """
    Tests the connection to attendance devices.

    Parameters:
    baseName (str): The name of the attendance sync document.

    Returns:
    bool: True if the function completes successfully.
    """  # noqa
    doc_name = baseName
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
    """
    Connects to a device using the provided IP address, port, and password.

    Args:
        device_ip (str): The IP address of the device.
        device_port (int): The port number of the device.
        device_password (int): The password for the device.

    Returns:
        conn (ZK or None): The connection object if successful, None otherwise.

    Raises:
        Exception: If there is an error connecting to the device.

    This function establishes a connection to a device using the provided IP address, port, and password. It creates a ZK object with the provided parameters and attempts to connect to the device. If the connection is successful, it prints a success message and returns the connection object. If there is an error connecting to the device, it logs the error and returns None. Finally, if a connection object is returned, it disables the device and disconnects from it.
    """  # noqa
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
        frappe.log_error(f"Failed to connect to device {device_ip}: {str(e)}", "Device Connection Error")  # noqa
        return None
    finally:
        if conn:
            conn.disable_device()
            conn.disconnect()


@frappe.whitelist(allow_guest=True)
def attendance_pull(baseName):
    """
    Retrieves attendance data for a given base name within a specified date range.

    Args:
        baseName (str): The name of the attendance sync document.

    Returns:
        bool: True if the function completes successfully.

    This function retrieves attendance data for a given base name within a specified date range. It first retrieves the attendance sync document with the provided base name and retrieves the list of selected devices. It then retrieves the start and end dates from the attendance sync document. If either the start or end date is None, it throws an exception. Otherwise, it iterates over each selected device and retrieves the device document. If the device document exists, it retrieves the device IP, port, and password. It then sets the status of the attendance sync document to "Initiated" and enqueues the retrieval of attendance data for the device. Finally, it returns True.
    """  # noqa
    doc_name = baseName
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
    """
    Retrieves attendance records from a ZK device, processes the data, and 
    updates the corresponding records in the system.

    Parameters:
        device_ip (str): The IP address of the ZK device.
        device_port (int): The port number of the ZK device.
        device_password (int): The password of the ZK device.
        start_date (datetime): The start date of the attendance records to be retrieved.
        end_date (datetime): The end date of the attendance records to be retrieved.
        record_name (str): The name of the attendance sync record.
        device_doc_name (str): The name of the attendance device document.

    Returns:
        bool: True if the attendance records are successfully retrieved and updated, False otherwise.
    """  # noqa
    record = frappe.get_doc("Attendance Sync", record_name)
    device_doc = frappe.get_doc("Attendance Devices", device_doc_name)
    record.db_set("status", "In-Progress")
    
    # Initiate connection to the device
    zk = ZK(
        device_ip,
        port=device_port,
        timeout=5,
        password=device_password,
        force_udp=False,
        ommit_ping=False,
    )
    conn = None
    new_checkins = []
    duplicate_entries = set()
    missing_employees = set()

    try:
        conn = zk.connect()
        all_logs = conn.get_attendance()
        users = conn.get_users()  # Get user list from the device
        
        # Create a dictionary to map UID to user information from the device
        user_mapping = {user.uid: user.name for user in users}
        print(user_mapping)

        for log in all_logs:
            log_time = log.timestamp
            log_type = "IN" if log.status == 1 else "OUT"

            # Check if the log falls within the date range
            if start_date.date() <= log_time.date() <= end_date.date():
                formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")
                employee = frappe.get_value(
                    "Employee", {"attendance_device_id": log.user_id}, "name"
                )

                if employee:
                    # Check for existing check-in entries
                    existing_checkin = frappe.get_value(
                        "Employee Checkin",
                        {"employee": employee, "time": formatted_time},
                        "name",
                    )

                    if not existing_checkin:
                        # Create new check-in, don't insert yet
                        check_in = frappe.new_doc("Employee Checkin")
                        check_in.employee = employee
                        check_in.time = formatted_time
                        check_in.log_type = log_type
                        check_in.attendance_device_id = log.user_id
                        new_checkins.append(check_in)
                    else:
                        # Add to the duplicate entries set
                        employee_name = frappe.get_value("Employee", employee, "employee_name")  # noqa
                        duplicate_entries.add((employee, employee_name))

                else:
                    # If employee is missing, try to find them in the device user list  # noqa
                    device_user_name = user_mapping.get(int(log.user_id), "Name Not in Device")  # noqa
                    missing_employees.add((log.user_id, device_user_name))

        # Insert new check-ins in bulk
        for checkin in new_checkins:
            checkin.insert()

        # Commit the transaction in one go
        frappe.db.commit()

        # Prepare HTML report for missing and duplicate entries
        html_report = generate_html_report(duplicate_entries, missing_employees)  # noqa

        # Set the status of the record and device document
        record.db_set("status", "Completed")
        record.db_set("last_sync", frappe.utils.now_datetime())
        device_doc.db_set("last_sync", frappe.utils.now_datetime())
        record.db_set("latest_remarks", html_report)  # Save remarks HTML in a custom field for logs  # noqa
        device_doc.db_set("sync_status", "Successful")
        record.notify_update()
        device_doc.notify_update()

        return True

    except Exception as e:
        error_message = f"Process terminated: {str(e)}"
        frappe.log_error(error_message, "Attendance Pull Error")
        record.db_set("status", "Failed")
        device_doc.db_set("last_sync", frappe.utils.now_datetime())
        device_doc.db_set("sync_status", "Unsuccessful")
        return False


def generate_html_report(duplicate_entries, missing_employees):
    """
    Generate HTML content for the remarks, listing duplicate entries and missing employees with totals.
    
    Args:
        duplicate_entries (set): A set of tuples containing employee ID and name for duplicate entries.
        missing_employees (set): A set of tuples containing user ID and employee name for missing employees.
    
    Returns:
        str: The HTML content for the remarks.
    """  # noqa

    html = "<h3>Attendance Sync Report</h3><h4>Time: " + frappe.utils.now() + "</h4>"  # noqa

    if duplicate_entries:
        html += f"<h4>Duplicate Entries ({len(duplicate_entries)} Total)</h4><ul>"  # noqa
        for emp_id, emp_name in duplicate_entries:
            html += f"<li>Employee ID: {emp_id}, Name: {emp_name}</li>"
        html += "</ul>"

    if missing_employees:
        html += f"<h4>Missing Employee User IDs ({len(missing_employees)} Total)</h4><ul>"  # noqa
        for user_id, emp_name in missing_employees:
            html += f"<li>User ID: {user_id}, Employee Name: {emp_name}</li>"
        html += "</ul>"

    if not duplicate_entries and not missing_employees:
        html += "<p>No issues found during sync.</p>"

    return html