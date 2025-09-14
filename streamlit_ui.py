import streamlit as st
import requests
import json
import time
from datetime import datetime

API_URL = "http://127.0.0.1:8000/execute" 
DEBUG_URL = "http://127.0.0.1:8003"

# Initialize session state for conversation memory
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'debug_data' not in st.session_state:
    st.session_state.debug_data = {}

# Page configuration
st.set_page_config(
    page_title="Doctor Appointment System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("Doctor Appointment System")
st.markdown("**Simple appointment booking: Select doctor → Check availability → Book appointment**")

# Create tabs
tab1, tab2 = st.tabs(["Book Appointment", "My Appointments"])

# Helper function to extract appointment details from appointment content
def _extract_appointment_details(appointment_content):
    """Extract doctor name, date, and time from appointment content"""
    import re
    
    # Extract doctor name (look for "Dr. Name" pattern)
    doctor_match = re.search(r'Dr\.\s+([^<]+)', appointment_content)
    doctor_name = doctor_match.group(1).strip() if doctor_match else "Unknown Doctor"
    
    # Extract date and time
    date_time_match = re.search(r'Date & Time:\s*([^<]+)', appointment_content)
    date_time = date_time_match.group(1).strip() if date_time_match else "Unknown Date"
    
    # Extract specialization
    specialization_match = re.search(r'Specialization:\s*([^<]+)', appointment_content)
    specialization = specialization_match.group(1).strip() if specialization_match else "Unknown Specialization"
    
    return {
        'doctor': doctor_name,
        'date_time': date_time,
        'specialization': specialization
    }

# Helper function to handle direct cancellation
def _handle_direct_cancellation(appointment_num, appointment_details, user_id):
    """Handle direct cancellation by calling the API with specific appointment details"""
    try:
        # Use simple cancellation message that matches the MCP agent pattern
        cancellation_message = f"Cancel appointment #{appointment_num}"
        
        request_data = {
            'messages': cancellation_message,
            'id_number': int(user_id)
        }
        if st.session_state.session_id:
            request_data['session_id'] = st.session_state.session_id
        
        response = requests.post(API_URL, json=request_data, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.session_id = result.get('session_id')
            
            # Update conversation history with the cancellation response
            if 'conversation_history' not in st.session_state:
                st.session_state.conversation_history = []
            
            # Add the cancellation request and response to conversation history
            st.session_state.conversation_history.append({
                'content': f"Cancel appointment #{appointment_num}",
                'type': 'human'
            })
            
            # Add the AI response
            if result.get('messages'):
                for msg in result.get('messages', []):
                    if msg.get('type') == 'ai':
                        st.session_state.conversation_history.append(msg)
                        break
            
            st.success(f"✅ Cancellation request sent for appointment #{appointment_num}")
        else:
            st.error(f"Error cancelling appointment: {response.status_code}")
    except Exception as e:
        st.error(f"Exception occurred during cancellation: {e}")

# Helper function to format messages nicely

# Sidebar with quick actions
with st.sidebar:
    st.header("Quick Actions")
    
    # Load data from CSV
    import pandas as pd
    df = pd.read_csv("data/doctor_availability.csv")
    
    # Get unique doctors with their specializations
    doctor_specs = df.groupby(['doctor_name', 'specialization']).size().reset_index()
    doctor_specs['display_name'] = doctor_specs['doctor_name'].str.replace('_', ' ').str.title()
    doctor_specs['spec_display'] = doctor_specs['specialization'].str.replace('_', ' ').str.title()
    
    # Available doctors with specializations
    st.subheader("Available Doctors")
    doctor_options = ["Choose a doctor..."]
    for _, row in doctor_specs.iterrows():
        doctor_options.append(f"{row['display_name']} ({row['spec_display']})")
    
    selected_doctor_display = st.selectbox("Select a doctor:", doctor_options)
    
    # Extract doctor name for processing
    selected_doctor = None
    if selected_doctor_display != "Choose a doctor...":
        # Get the original doctor name from the CSV data
        display_name = selected_doctor_display.split(" (")[0]
        # Find the matching doctor name in the CSV
        matching_doctor = doctor_specs[doctor_specs['display_name'] == display_name]['doctor_name'].iloc[0]
        selected_doctor = matching_doctor
    
    # Available dates from CSV
    st.subheader("Available Dates")
    available_dates = sorted(df['date_slot'].str.split(' ').str[0].unique())
    date_options = ["Choose a date..."] + available_dates
    selected_date = st.selectbox("Select a date:", date_options)
    
    # Quick query buttons
    st.subheader("Quick Start")
    
    # Auto-check availability when both doctor and date are selected
    if selected_doctor and selected_date != "Choose a date...":
        # Check if we need to fetch availability
        cache_key = f"{selected_doctor}_{selected_date}"
        if st.session_state.get('last_availability_check') != cache_key:
            # Clear any previous slots when checking new combination
            if 'available_slots' in st.session_state:
                del st.session_state['available_slots']
            with st.spinner("🔍 Checking availability..."):
                try:
                    # Simple tool call for availability
                    request_data = {
                        'messages': f"Check availability for Dr. {selected_doctor.replace('_', ' ').title()} on {selected_date}", 
                        'id_number': 1234567
                    }
                    
                    response = requests.post(API_URL, json=request_data, verify=False)
                    
                    if response.status_code == 200:
                        result = response.json()
                        # Extract available slots from AI response
                        available_slots = []
                        for msg in result.get('messages', []):
                            if msg.get('type') == 'ai':
                                content = msg.get('content', '')
                                if 'Available slots:' in content:
                                    # Parse the slots from the response
                                    slots_text = content.split("Available slots:")[1].strip()
                                    # Split by comma and clean up each slot
                                    available_slots = [slot.strip() for slot in slots_text.split(',') if slot.strip()]
                                    break
                                elif 'Available Time Slots:' in content:
                                    # Parse the formatted response
                                    lines = content.split('\n')
                                    for line in lines:
                                        if line.strip() and line.strip()[0].isdigit():
                                            # Extract time slot from lines like "1. 08:00"
                                            time_part = line.split('.', 1)[1].strip()
                                            available_slots.append(time_part)
                                    break
                        
                        st.session_state.available_slots = available_slots
                        st.session_state.last_availability_check = cache_key
                        if available_slots:
                            st.success(f"Found {len(available_slots)} available slots!")
                        else:
                            st.warning("No available slots found")
                            # Debug: show the raw response
                            st.text(f"Debug - Raw response: {result.get('messages', [{}])[0].get('content', 'No content')[:200]}...")
                    else:
                        st.error(f"Error checking availability: {response.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    if st.button("Clear Chat", key="clear_chat_2"):
        st.session_state.conversation_history = []
        st.session_state.session_id = None
        st.session_state.availability_result = None
        st.session_state.last_availability_check = None
        st.rerun()
    
    # Show simple availability display
    if selected_doctor and selected_date != "Choose a date..." and st.session_state.get('available_slots'):
        st.subheader("Available Time Slots")
        available_slots = st.session_state.available_slots
        
        if available_slots:
            st.success(f"{len(available_slots)} slots available!")
            for i, slot in enumerate(available_slots, 1):
                st.write(f"{i}. {slot}")
        else:
            st.warning("No available slots")
    
    # Simple booking section
    if selected_doctor and selected_date != "Choose a date..." and st.session_state.get('available_slots'):
        st.markdown("---")
        st.subheader("Quick Book")
        
        available_slots = st.session_state.available_slots
        if available_slots:
            # Simple number selection
            slot_options = [f"{i}. {slot}" for i, slot in enumerate(available_slots, 1)]
            selected_slot = st.selectbox("Select time slot:", ["Choose a time..."] + slot_options)
            
            if selected_slot != "Choose a time...":
                # Extract the actual time from selection
                slot_number = int(selected_slot.split('.')[0])
                selected_time = available_slots[slot_number - 1]
                
                if st.button("Book This Slot", type="primary"):
                    with st.spinner("Booking appointment..."):
                        try:
                            # Simple booking message
                            booking_message = f"Book appointment with {selected_doctor_display} on {selected_date} at {selected_time}"
                            
                            request_data = {
                                'messages': booking_message, 
                                'id_number': int(user_id) if user_id else 1234567
                            }
                            
                            response = requests.post(API_URL, json=request_data, verify=False)
                            
                            if response.status_code == 200:
                                result = response.json()
                                st.session_state.session_id = result.get('session_id')
                                
                                # Replace conversation history with full history from backend
                                st.session_state.conversation_history = result.get('messages', [])
                                
                                st.success("✅ Appointment booked successfully!")
                                st.rerun()
                            else:
                                st.error(f"Error booking: {response.status_code}")
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    st.markdown("---")
    st.markdown("**Simple Steps:**")
    st.markdown("1. **Select doctor & date** → Availability loads automatically")
    st.markdown("2. **Choose time slot** → Click 'Book This Slot' or type in chat")
    st.markdown("3. **Done!** → Appointment booked")

# TAB 1: BOOK APPOINTMENT
with tab1:
    # User ID input
    user_id = st.text_input("Patient ID:", value="1234567", help="Enter your patient ID number")
    
    # Display conversation history will be shown after availability slots

    # Simple chat area
    st.subheader("💭 Chat with Assistant")
    
    # Show available slots if selected
    if selected_doctor and selected_date != "Choose a date..." and st.session_state.get('available_slots'):
        st.info(f"**Available slots for {selected_doctor_display} on {selected_date}:**")
        for i, slot in enumerate(st.session_state.available_slots, 1):
            st.write(f"{i}. {slot}")
        st.write("**You can say:** 'Book slot 1' or 'I want 08:00'")
    
    # Display conversation history after availability slots
    if st.session_state.conversation_history:
        st.subheader("Conversation History")
        
        # Create a scrollable container for the conversation
        conversation_container = st.container()
        
        with conversation_container:
            for i, msg in enumerate(st.session_state.conversation_history):
                # Skip system messages and focus on user/assistant messages
                if msg.get('type') == 'human' and not msg.get('content', '').startswith('User ID:'):
                    # Extract just the user query from the message
                    user_content = msg.get('content', '')
                    
                    # User message - right aligned
                    st.markdown(f"""
                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #2196F3; margin-left: 20%;">
                        <strong>You:</strong> {user_content}
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif msg.get('type') == 'ai':
                    # AI response
                    content = msg.get('content', '')
                    
                    # Handle different content formats
                    if isinstance(content, list):
                        # Extract text from structured content
                        text_content = ""
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_content += item.get('text', '')
                            elif isinstance(item, str):
                                text_content += item
                        content = text_content if text_content else str(content)
                    else:
                        content = str(content)
                    
                    # AI message - left aligned
                    st.markdown(f"""
                    <div style="background-color: #f3e5f5; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #9c27b0; margin-right: 20%;">
                        <strong>Assistant:</strong> {content}
                    </div>
                    """, unsafe_allow_html=True)
    
    # Handle redirected messages from My Appointments tab
    if st.session_state.get('redirect_message'):
        redirected_message = st.session_state.redirect_message
        st.info(f"**Redirected from My Appointments:** {redirected_message}")
        
        # Auto-send the redirected message
        if user_id:
            with st.spinner("Processing your request..."):
                try:
                    request_data = {
                        'messages': redirected_message, 
                        'id_number': int(user_id)
                    }
                    if st.session_state.session_id:
                        request_data['session_id'] = st.session_state.session_id
                    
                    response = requests.post(API_URL, json=request_data, verify=False)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.session_id = result.get('session_id')
                        
                        # Replace conversation history with full history from backend
                        st.session_state.conversation_history = result.get('messages', [])
                        
                        st.success("Request processed!")
                        
                        # Check if this was a cancellation or reschedule
                        if redirected_message and ('cancel' in redirected_message.lower() or 'reschedule' in redirected_message.lower()):
                            st.info("**Please go back to 'My Appointments' tab to see the updated list.**")
                        
                        # Clear the redirected message
                        st.session_state.redirect_message = None
                        st.rerun()
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Exception occurred: {e}")
        else:
            st.warning("Please enter your Patient ID above.")
        
        # Clear the redirected message after processing
        if 'redirect_message' in st.session_state:
            del st.session_state.redirect_message

    query = st.text_area(
        "Tell me what you need:", 
        height=100,
        placeholder="Example: 'Book slot 1' or 'I want 08:00' or 'Cancel my appointment'",
        help="Use the available slots above or ask anything about appointments!"
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Send Message", type="primary"):
            if user_id and query:
                with st.spinner("🤔 Processing..."):
                    try:
                        # Add context from sidebar selections and store in session
                        context_message = query
                        if selected_doctor and selected_date != "Choose a date...":
                            # Store the selected doctor and date in session state
                            st.session_state.selected_doctor = selected_doctor
                            st.session_state.selected_date = selected_date
                            context_message = f"Doctor: {selected_doctor_display}, Date: {selected_date}. {query}"
                        
                        request_data = {
                            'messages': context_message, 
                            'id_number': int(user_id)
                        }
                        if st.session_state.session_id:
                            request_data['session_id'] = st.session_state.session_id
                        
                        response = requests.post(API_URL, json=request_data, verify=False)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.session_id = result.get('session_id')
                            
                            # Replace conversation history with full history from backend
                            # (Backend now returns full conversation history)
                            st.session_state.conversation_history = result.get('messages', [])
                            
                            st.success("Response received!")
                            st.rerun()
                        else:
                            st.error(f"Error {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"Exception occurred: {e}")
            else:
                st.warning("Please enter both ID and query.")
    
    with col2:
        if st.button("Clear Chat", key="clear_chat_1"):
            st.session_state.session_id = None
            st.session_state.conversation_history = []
            st.success("Chat cleared! Starting fresh conversation.")
            st.rerun()

    # Clear the quick query after use
    if 'quick_query' in st.session_state:
        del st.session_state.quick_query

# TAB 2: MY APPOINTMENTS
with tab2:
    st.header("My Appointments")
    
    # User ID input for cancellation
    cancel_user_id = st.text_input("Patient ID:", value="1234567", help="Enter your patient ID number to view and cancel appointments")
    
    if st.button("Check My Appointments", type="primary"):
        if cancel_user_id:
            with st.spinner("Checking your appointments..."):
                try:
                    request_data = {
                        'messages': 'show my appointments', 
                        'id_number': int(cancel_user_id)
                    }
                    if st.session_state.session_id:
                        request_data['session_id'] = st.session_state.session_id
                    
                    response = requests.post(API_URL, json=request_data, verify=False)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.session_id = result.get('session_id')
                        # Store appointments data separately for this page
                        st.session_state.my_appointments_data = result.get('messages', [])
                        st.session_state.current_patient_id = int(cancel_user_id)
                        st.success("Appointments retrieved!")
                        st.rerun()
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Exception occurred: {e}")
        else:
            st.warning("Please enter your ID number.")
    
    # Display appointments directly on this page
    if hasattr(st.session_state, 'my_appointments_data') and st.session_state.my_appointments_data:
        st.subheader("Your Appointments")
        
        for i, msg in enumerate(st.session_state.my_appointments_data):
            content = msg.get('content', '')
            
            # Handle different content formats
            if isinstance(content, list):
                # Extract text from structured content
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_content += item.get('text', '')
                    elif isinstance(item, str):
                        text_content += item
                content_str = text_content if text_content else str(content)
            else:
                content_str = str(content)
            
            # Check if this message contains appointment data (AI message with appointment history)
            if (msg.get('type') == 'ai' and 'Appointment History for User' in content_str) or (msg.get('type') == 'tool' and 'get_user_appointments' in msg.get('name', '')):
                # This is the raw appointment data from the tool
                appointment_data = content_str
                
                # Parse and format the appointment data
                if "Appointments for User" in appointment_data or "Appointment History for User" in appointment_data:
                    # Check if this is history or current appointments
                    if "Appointment History for User" in appointment_data:
                        st.markdown("""
                        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #4caf50;">
                            <strong>Your Complete Appointment History:</strong><br><br>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #4caf50;">
                            <strong>Your Current Appointments:</strong><br><br>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Extract appointment lines and format them nicely
                    lines = appointment_data.split('\n')
                    current_appointment = []
                    appointment_counter = 0  # Initialize counter for unique keys
                    raw_appointments = []  # Store raw appointment data for cancellation
                    
                    for line in lines:
                        if line.strip() and not line.startswith(('Appointments for User', 'Appointment History for User', 'Summary:')):
                            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                                # This is an appointment line - display previous appointment if exists
                                if current_appointment:
                                    appointment_content = ''.join(current_appointment)
                                    appointment_counter += 1  # Increment counter for each appointment
                                    appointment_num = appointment_counter
                                    
                                    # Determine appointment status and color
                                    status = "ACTIVE"
                                    border_color = "#2196f3"
                                    bg_color = "#f9f9f9"
                                    
                                    if "❌" in appointment_content:
                                        status = "CANCELLED"
                                        border_color = "#f44336"
                                        bg_color = "#ffebee"
                                    elif "✅" in appointment_content:
                                        status = "COMPLETED"
                                        border_color = "#4caf50"
                                        bg_color = "#e8f5e8"
                                    elif "🟢" in appointment_content:
                                        status = "UPCOMING"
                                        border_color = "#2196f3"
                                        bg_color = "#f9f9f9"
                                    
                                    st.markdown(f"""
                                    <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                        {appointment_content}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Add action buttons only for upcoming appointments
                                    if status == "UPCOMING":
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("❌ Cancel", key=f"cancel_{appointment_num}", type="secondary"):
                                                # Extract appointment details for direct cancellation
                                                appointment_details = _extract_appointment_details(appointment_content)
                                                
                                                # Directly call cancellation API
                                                _handle_direct_cancellation(appointment_num, appointment_details, cancel_user_id)
                                                
                                                # Refresh appointments
                                                st.rerun()
                                        
                                        with col2:
                                            if st.button("Reschedule", key=f"reschedule_{appointment_num}", type="secondary"):
                                                # Preserve conversation history and redirect to Book Appointment tab
                                                if hasattr(st.session_state, 'my_appointments_data'):
                                                    # Merge appointment data with existing conversation history
                                                    if hasattr(st.session_state, 'conversation_history'):
                                                        st.session_state.conversation_history.extend(st.session_state.my_appointments_data)
                                                    else:
                                                        st.session_state.conversation_history = st.session_state.my_appointments_data
                                                
                                                st.session_state.active_tab = 0
                                                st.session_state.redirect_message = f"reschedule my appointment number {appointment_num}"
                                                st.rerun()
                                    
                                    current_appointment = []
                                
                                # Start new appointment
                                current_appointment.append(f"<strong>{line.strip()}</strong><br>")
                            elif (line.strip().startswith('   ') or 
                                  line.strip().startswith('Date & Time:') or 
                                  line.strip().startswith('Specialization:') or
                                  'Date & Time:' in line or
                                  'Specialization:' in line):
                                # This is appointment details (with spaces or emoji prefixes)
                                clean_line = line.strip()
                                if 'Date & Time:' in clean_line:
                                    current_appointment.append(f"<span style='color: #1976d2; font-weight: bold;'>{clean_line}</span><br>")
                                elif 'Specialization:' in clean_line:
                                    current_appointment.append(f"<span style='color: #388e3c;'>{clean_line}</span><br>")
                                else:
                                    current_appointment.append(f"{clean_line}<br>")
                    
                    # Display the last appointment if exists
                    if current_appointment:
                        appointment_content = ''.join(current_appointment)
                        appointment_counter += 1  # Increment counter for the last appointment
                        appointment_num = appointment_counter
                        
                        # Determine appointment status and color for last appointment
                        status = "ACTIVE"
                        border_color = "#2196f3"
                        bg_color = "#f9f9f9"
                        
                        if "❌" in appointment_content:
                            status = "CANCELLED"
                            border_color = "#f44336"
                            bg_color = "#ffebee"
                        elif "✅" in appointment_content:
                            status = "COMPLETED"
                            border_color = "#4caf50"
                            bg_color = "#e8f5e8"
                        elif "🟢" in appointment_content:
                            status = "UPCOMING"
                            border_color = "#2196f3"
                            bg_color = "#f9f9f9"
                        
                        st.markdown(f"""
                        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            {appointment_content}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add action buttons only for upcoming appointments
                        if status == "UPCOMING":
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("❌ Cancel", key=f"cancel_last_{appointment_num}", type="secondary"):
                                    # Extract appointment details for direct cancellation
                                    appointment_details = _extract_appointment_details(appointment_content)
                                    
                                    # Directly call cancellation API
                                    _handle_direct_cancellation(appointment_num, appointment_details, cancel_user_id)
                                    
                                    # Refresh appointments
                                    st.rerun()
                            
                            with col2:
                                if st.button("Reschedule", key=f"reschedule_last_{appointment_num}", type="secondary"):
                                    # Preserve conversation history and redirect to Book Appointment tab
                                    if hasattr(st.session_state, 'my_appointments_data'):
                                        # Merge appointment data with existing conversation history
                                        if hasattr(st.session_state, 'conversation_history'):
                                            st.session_state.conversation_history.extend(st.session_state.my_appointments_data)
                                        else:
                                            st.session_state.conversation_history = st.session_state.my_appointments_data
                                    
                                    st.session_state.active_tab = 0
                                    st.session_state.redirect_message = f"reschedule my appointment number {appointment_num}"
                                    st.rerun()
                    
                    # Display summary if available
                    summary_lines = [line for line in lines if line.strip().startswith('Summary:') or line.strip().startswith('   ✓') or line.strip().startswith('   ✗')]
                    if summary_lines:
                        
                        summary_content = ""
                        for line in summary_lines:
                            if line.strip().startswith('Summary:'):
                                continue  # Skip the header
                            clean_line = line.strip()
                            summary_content += f"{clean_line}<br>"
                        
                        st.markdown(f"""
                        <div style="background-color: #fafafa; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #9c27b0;">
                            {summary_content}
                        </div>
                        """, unsafe_allow_html=True)
            
            elif msg.get('type') == 'ai' and 'appointments' in content_str.lower() and 'Here are all your current appointments' in content_str:
                # This is the formatted response from the AI
                st.markdown("""
                <div style="background-color: #fff3e0; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #ff9800;">
                    <strong>Assistant Response:</strong><br><br>
                </div>
                """, unsafe_allow_html=True)
                
                # Display the AI's formatted response
                st.markdown(f"""
                <div style="background-color: #f3e5f5; padding: 15px; border-radius: 15px; margin: 10px 0; border-left: 4px solid #9c27b0;">
                    {content_str}
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
