from datetime import datetime
import frappe


# Function to calculate the difference in hours between two times
# Function to calculate the difference in hours between two datetime objects
def time_diff_in_hours(out_time, in_time):
    # Calculate the time difference directly (since both are already datetime objects)
    time_diff = out_time - in_time

    # Convert the difference to hours
    total_hours = time_diff.total_seconds() / 3600
    return total_hours


# Main function to execute the query and process the data
def execute(filters=None):
    # Define the columns for the report
    columns = [
        {
            "label": "Select",
            "fieldname": "select",
            "fieldtype": "Check",
            "width": 100,
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee",
        },
        {
            "fieldname": "employee_name",
            "label": "Employee Name",
            "fieldtype": "Data",
        },
        {
            "fieldname": "checkin_date",
            "label": "Checkin Date",
            "fieldtype": "Date",
        },
        {
            "fieldname": "in_time",
            "label": "In Time",
            "fieldtype": "Data",
        },
        {"fieldname": "out_time", "label": "Out Time", "fieldtype": "Data"},
        {"fieldname": "total_hours", "label": "Total Hours", "fieldtype": "Data"},
        {
            "fieldname": "attendance",
            "label": "Attendance",
            "fieldtype": "Data",
        },
    ]

    # Get date filters from the input
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    employee_filter = filters.get("employee")  # Get employee filter from filters

    # Build dynamic conditions
    employee_condition = (
        f"AND ec.employee = '{employee_filter}'" if employee_filter else ""
    )
    date_condition = (
        f"AND ec.time BETWEEN '{from_date}' AND '{to_date}'"
        if from_date and to_date
        else ""
    )

    # Construct the SQL query
    sql_query = f"""
        SELECT 
            ec.employee,
            ec.employee_name as employee_name,
            MIN(ec.time) as in_time,
            MAX(ec.time) as out_time,
            DATE(ec.time) as checkin_date
        FROM 
            `tabEmployee Checkin` ec
        WHERE 
            1 = 1
            {date_condition}
            {employee_condition}
        GROUP BY 
            ec.employee, checkin_date
        ORDER BY 
            ec.employee, checkin_date
    """

    # Execute the SQL query using frappe
    checkin_data = frappe.db.sql(sql_query, as_dict=True)

    # Prepare the final data list
    new_data = []

    for row in checkin_data:
        # Calculate total hours between first check-in and last check-in
        total_hours = time_diff_in_hours(row["out_time"], row["in_time"])

        # Determine attendance based on total hours
        attendance = "Present" if total_hours >= 7 else "Absent"

        # Append the row to new_data
        new_data.append(
            {
                "select": 0,
                "employee": row["employee"],
                "employee_name": row["employee_name"],
                "in_time": row["in_time"].strftime("%H:%M:%S"),
                "out_time": row["out_time"].strftime("%H:%M:%S"),
                "checkin_date": row["checkin_date"].strftime("%Y-%m-%d"),
                "total_hours": round(total_hours, 2),
                "attendance": attendance,
            }
        )

    # Return the columns and the final data
    return columns, new_data
