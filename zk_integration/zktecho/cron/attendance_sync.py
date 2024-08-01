import frappe
from frappe.utils import today, add_days, get_first_day, get_last_day
from datetime import datetime
from zk_integration.zktecho.attendance_pull import attendance_pull


def process_attendance_sync():
    date = today()
    print(date)
    try:
        attendance_sync_docs = frappe.get_all(
            'Attendance Sync',
            filters={'select_frequency': ['!=', 'Manually'], 'posting_date': ['<=', today()]},  # noqa
            fields=['name']
        )
        print(attendance_sync_docs)
        for doc in attendance_sync_docs:
            try:
                attendance_sync_doc = frappe.get_doc('Attendance Sync', doc.name)  # noqa
                if attendance_sync_doc.select_frequency == 'Daily':
                    process_daily(attendance_sync_doc)
                elif attendance_sync_doc.select_frequency == 'Monthly':
                    process_monthly(attendance_sync_doc)  # noqa
            except Exception:
                frappe.log_error(message=frappe.get_traceback(), title=f"Error processing attendance sync for {doc.name}")  # noqa
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title="Error fetching attendance sync docs")  # noqa


def process_daily(attendance_sync_doc):
    print(f"Processing daily attendance for {attendance_sync_doc.name}")
    try:
        last_sync = attendance_sync_doc.last_sync
        posting_date = attendance_sync_doc.posting_date
        today_date = datetime.today().date()  # This will extract the date part from datetime

        sync_date = last_sync or posting_date
        new_date = add_day(sync_date)
        start_date, end_date = get_start_end_dates(sync_date)
        if today_date == new_date:
            attendance_sync_doc.db_set('from_date', start_date)
            attendance_sync_doc.db_set('to_date', end_date)
            attendance_pull(attendance_sync_doc.name)
        elif today_date > new_date:
            attendance_sync_doc.db_set('from_date', sync_date)
            attendance_sync_doc.db_set('to_date', today_date)
            attendance_pull(attendance_sync_doc.name)
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title=f"Error processing daily attendance for {attendance_sync_doc.name}")  # noqa


def process_monthly(attendance_sync_doc):
    print(f"Processing monthly attendance for {attendance_sync_doc.name}")
    try:
        last_sync = attendance_sync_doc.last_sync
        posting_date = attendance_sync_doc.posting_date
        today_date = datetime.today().date()  # This will extract the date part from datetime
        sync_date = last_sync or posting_date
        new_date = add_day(sync_date)
        start_date, end_date = get_start_end_dates_of_month(sync_date)
        if today_date == new_date:
            attendance_sync_doc.db_set('from_date', start_date)
            attendance_sync_doc.db_set('to_date', end_date)
            attendance_pull(attendance_sync_doc.name)
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title=f"Error processing monthly attendance for {attendance_sync_doc.name}")  # noqa


def add_day(source_date):
    if isinstance(source_date, str):
        source_date = datetime.strptime(source_date, '%Y-%m-%d')
    return add_days(source_date, 1)


def get_start_end_dates_of_month(date_obj):
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d')

    start_date = get_first_day(date_obj)
    end_date = get_last_day(date_obj)
    return start_date, end_date


def get_start_end_dates(date_obj):
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d')

    start_date = date_obj
    end_date = date_obj
    return start_date, end_date
