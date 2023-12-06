from zk import ZK, const
import frappe

def create_zkteco_user(doc, method):
    emp_name = doc.employee_name
    if doc.sync_in_zk_device == 1:
        emp_id = doc.attendance_device_id
        emp_privileges = doc.role_this_user_will_have
        emp_device_list = doc.device_list

        for row in emp_device_list:
            device_name = row.devices
            device_doc = frappe.get_doc("Attendance Devices", device_name) 

            if device_doc:
                device_ip = str(device_doc.ip)
                print(device_ip)
                device_port = int(device_doc.port)
                print(device_port)
                device_password = int(device_doc.password)
                print(device_password)

                if connect_to_zkteco_device(emp_name, emp_id, emp_privileges, device_name, device_ip, device_port, device_password):
                    frappe.msgprint(f"Successfully connected to {device_name} for employee {emp_name}")
                else:
                    frappe.msgprint(f"Failed to connect to {device_name} for employee {emp_name}")
    else:
        frappe.msgprint(f"Employee {emp_name} will not sync in ZK device")

def connect_to_zkteco_device(emp_name, emp_id, emp_privileges, device_name, device_ip, device_port, device_password):
    conn = None
    try:
        zk = ZK(device_ip, port=device_port, timeout=5, password=device_password, force_udp=False, ommit_ping=False)
        conn = zk.connect()
        print(f"Connection to {device_name} successful for employee {emp_name}")
        conn.test_voice(index=10) 

        # Use the provided parameters for setting the user
        user_info = conn.set_user(
            uid=int(emp_id),
            
            name=emp_name,
            privilege=emp_privileges,
            password='123',
            group_id='',
            user_id=emp_id,
            card=0
        )

        users = conn.get_users()
        print(users)
        desired_uid = int(emp_id)
        user_found = False  
        
        for user in users:
            print(f"Checking User ID: {user.uid}")

            if user.uid == desired_uid:
                frappe.msgprint(f"User ID: {user.uid}, Name: {user.name}, Successfully Sync in Attendance Device: {device_name}")
                user_found = True  
                break 
        
        if not user_found:
            frappe.msgprint(f"Failed To Create in Attendnace Device User ID: {desired_uid} ")

        


        return True
    except Exception as e:
        frappe.msgprint(f"Process failed for employee {emp_name}: {str(e)}")
        return False
    finally:
        if conn:
            conn.disable_device()
            conn.disconnect()

def delete_zkteco_user(doc, method):
    original_doc = doc.get_doc_before_save()
    if original_doc and original_doc.sync_in_zk_device == 1:
        previous_device_list = original_doc.device_list
        current_device_list = doc.device_list
        emp_uid=int(doc.attendance_device_id)
        emp_name=doc.employee_name

        for prev_row in previous_device_list:
            prev_device = prev_row.devices
            found = False
            for curr_row in current_device_list:
                curr_device = curr_row.devices
                if prev_device == curr_device:
                    found = True
                    break

            if not found:
                frappe.msgprint(f"User From Devices {prev_device} Will be deleted ")
                device_name = prev_device
                device_doc = frappe.get_doc("Attendance Devices", device_name) 

                if device_doc:
                    device_ip = str(device_doc.ip)
                    print(device_ip)
                    device_port = int(device_doc.port)
                    print(device_port)
                    device_password = int(device_doc.password)
                    print(device_password)

                    if delete_user(emp_uid, device_name, device_ip, device_port, device_password,emp_name):
                        frappe.msgprint(f"Successfully Deleted employee {device_name} from {emp_name}")
                    else:
                        frappe.msgprint(f"Failed to connect to {device_name} for employee {emp_name}")
            


def delete_user(emp_uid, device_name, device_ip, device_port, device_password,emp_name):
    conn = None
    try:
        zk = ZK(device_ip, port=device_port, timeout=5, password=device_password, force_udp=False, ommit_ping=False)
        conn = zk.connect()
        print(f"Connection to {device_name} successful for employee {emp_name}")
        conn.delete_user(uid=emp_uid)
        conn.test_voice(index=11) 


        return True
    except Exception as e:
        frappe.msgprint(f"Process failed for employee {emp_name}: {str(e)}")
        return False
    finally:
        if conn:
            conn.disable_device()
            conn.disconnect()
