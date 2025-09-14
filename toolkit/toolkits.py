import pandas as pd
from typing import  Literal
from langchain_core.tools import tool
from data_models.models import *


@tool
def check_availability_by_doctor(desired_date:DateModel, doctor_name:Literal['kevin anderson','robert martinez','susan davis','daniel miller','sarah wilson','michael green','lisa brown','jane smith','emily johnson','john doe']):
    """
    Checking the database if we have availability for the specific doctor.
    The parameters should be mentioned by the user in the query
    """
    df = pd.read_csv(r"data/doctor_availability.csv")
    
    #print(df)
    
    df['date_slot_time'] = df['date_slot'].apply(lambda input: input.split(' ')[-1])
    
    rows = list(df[(df['date_slot'].apply(lambda input: input.split(' ')[0]) == desired_date.date)&(df['doctor_name'] == doctor_name)&(df['is_available'] == True)]['date_slot_time'])

    if len(rows) == 0:
        output = "No availability in the entire day"
    else:
        output = f'This availability for {desired_date.date}\n'
        output += "Available slots: " + ', '.join(rows)

    return output
@tool
def set_appointment(desired_date:DateTimeModel, id_number:IdentificationNumberModel, doctor_name:Literal['kevin anderson','robert martinez','susan davis','daniel miller','sarah wilson','michael green','lisa brown','jane smith','emily johnson','john doe']):
    """
    Set appointment or slot with the doctor.
    The parameters MUST be mentioned by the user in the query.
    """
    df = pd.read_csv(r"data/doctor_availability.csv")
   
    from datetime import datetime
    def convert_datetime_format(dt_str):
        # Parse the input datetime string
        #dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
        
        # Format the output as 'DD-MM-YYYY HH:MM' (keep colon format to match CSV)
        return dt.strftime("%d-%m-%Y %H:%M")
    
    case = df[(df['date_slot'] == convert_datetime_format(desired_date.date))&(df['doctor_name'] == doctor_name)&(df['is_available'] == True)]
    if len(case) == 0:
        return "No available appointments for that particular case"
    else:
        df.loc[(df['date_slot'] == convert_datetime_format(desired_date.date))&(df['doctor_name'] == doctor_name) & (df['is_available'] == True), ['is_available','patient_to_attend']] = [False, id_number.id]
        df.to_csv(r'data/doctor_availability.csv', index = False)

        return "Successfully done"
@tool
def cancel_appointment(date:DateTimeModel, id_number:IdentificationNumberModel, doctor_name:Literal['kevin anderson','robert martinez','susan davis','daniel miller','sarah wilson','michael green','lisa brown','jane smith','emily johnson','john doe']):
    """
    Canceling an appointment.
    The parameters MUST be mentioned by the user in the query.
    """
    df = pd.read_csv(r"data/doctor_availability.csv")
    case_to_remove = df[(df['date_slot'] == date.date)&(df['patient_to_attend'] == id_number.id)&(df['doctor_name'] == doctor_name)]
    if len(case_to_remove) == 0:
        return "You don´t have any appointment with that specifications"
    else:
        df.loc[(df['date_slot'] == date.date) & (df['patient_to_attend'] == id_number.id) & (df['doctor_name'] == doctor_name), ['is_available', 'patient_to_attend']] = [True, None]
        df.to_csv(r'data/doctor_availability.csv', index = False)

        return "Successfully cancelled"


@tool
def get_user_appointments(id_number: IdentificationNumberModel) -> str:
    """Get all appointments for a specific user including history.
    
    Args:
        id_number: Patient identification number
    """
    try:
        df = pd.read_csv("data/doctor_availability.csv")
        
        # Find all appointments for this user (both active and cancelled)
        appointments = df[df['patient_to_attend'] == id_number.id]
        
        if appointments.empty:
            return f"No appointments found for user {id_number.id}"
        
        def format_datetime(datetime_str):
            """Format datetime string to be more readable"""
            try:
                from datetime import datetime
                # Parse the datetime string (format: DD-MM-YYYY HH:MM)
                dt = datetime.strptime(datetime_str, "%d-%m-%Y %H:%M")
                
                # Format date
                date_formatted = dt.strftime("%A, %B %d, %Y")
                
                # Format time in 12-hour format
                time_formatted = dt.strftime("%I:%M %p")
                
                return f"{date_formatted} at {time_formatted}"
            except:
                return datetime_str  # Return original if parsing fails
        
        def format_doctor_name(name):
            """Format doctor name to be more readable"""
            return name.replace('_', ' ').title()
        
        def format_specialization(spec):
            """Format specialization to be more readable"""
            return spec.replace('_', ' ').title()
        
        def get_appointment_status(row):
            """Determine appointment status based on availability and date"""
            from datetime import datetime
            
            try:
                # Parse appointment date
                appointment_date = datetime.strptime(row['date_slot'], "%d-%m-%Y %H:%M")
                current_date = datetime.now()
                
                if row['is_available'] == True:
                    return "CANCELLED"
                elif appointment_date < current_date:
                    return "COMPLETED"
                else:
                    return "UPCOMING"
            except:
                return "ACTIVE" if row['is_available'] == False else "CANCELLED"
        
        def get_status_emoji(status):
            """Get emoji for appointment status"""
            status_emojis = {
                "UPCOMING": "🟢",
                "COMPLETED": "✅", 
                "CANCELLED": "❌",
                "ACTIVE": "🟢"
            }
            return status_emojis.get(status, "📋")
        
        # Sort appointments by date (newest first)
        appointments = appointments.sort_values('date_slot', ascending=False)
        
        result = f"📋 Appointment History for User {id_number.id}:\n\n"
        
        # Group appointments by status
        upcoming_count = 0
        completed_count = 0
        cancelled_count = 0
        
        for i, (_, row) in enumerate(appointments.iterrows()):
            # Convert index to letter (0=a, 1=b, 2=c, etc.)
            appointment_letter = chr(ord('a') + i)
            formatted_datetime = format_datetime(row['date_slot'])
            formatted_doctor = format_doctor_name(row['doctor_name'])
            formatted_spec = format_specialization(row['specialization'])
            status = get_appointment_status(row)
            status_emoji = get_status_emoji(status)
            
            result += f"{appointment_letter}. {status_emoji} Dr. {formatted_doctor}\n"
            result += f"   📅 Date & Time: {formatted_datetime}\n"
            result += f"   🏥 Specialization: {formatted_spec}\n"
            result += f"   📊 Status: {status}\n\n"
            
            # Count by status
            if status == "UPCOMING":
                upcoming_count += 1
            elif status == "COMPLETED":
                completed_count += 1
            elif status == "CANCELLED":
                cancelled_count += 1
        
        # Add summary
        result += f"📊 Summary:\n"
        result += f"   🟢 Upcoming: {upcoming_count}\n"
        result += f"   ✅ Completed: {completed_count}\n"
        result += f"   ❌ Cancelled: {cancelled_count}\n"
        
        return result
        
    except Exception as e:
        return f"Error getting appointments: {str(e)}"
