"""
MCP (Model Context Protocol) Tools for Doctor Appointment System
Separate tools for booking and cancellation to avoid confusion
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from data_models.models import *
from toolkit.toolkits import *

class ActionType(Enum):
    BOOK = "book"
    CANCEL = "cancel"
    VIEW = "view"
    RESCHEDULE = "reschedule"

@dataclass
class AppointmentContext:
    """Context for appointment operations"""
    user_id: int
    doctor_name: str = None
    date_slot: str = None
    time_slot: str = None
    appointment_letter: str = None
    action_type: ActionType = None

class MCPAppointmentManager:
    """MCP-based appointment management system"""
    
    def __init__(self):
        self.df = pd.read_csv("data/doctor_availability.csv")
        self.contexts: Dict[str, AppointmentContext] = {}
    
    def create_context(self, session_id: str, user_id: int) -> str:
        """Create a new context for a session"""
        context = AppointmentContext(user_id=user_id)
        self.contexts[session_id] = context
        return session_id
    
    def get_context(self, session_id: str) -> AppointmentContext:
        """Get context for a session"""
        return self.contexts.get(session_id, None)
    
    def update_context(self, session_id: str, **kwargs) -> None:
        """Update context for a session"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)
    
    def clear_context(self, session_id: str) -> None:
        """Clear context for a session"""
        if session_id in self.contexts:
            del self.contexts[session_id]

class MCPBookingTool:
    """MCP Tool for appointment booking"""
    
    def __init__(self, manager: MCPAppointmentManager):
        self.manager = manager
    
    def book_appointment(self, session_id: str, doctor_name: str, date_slot: str, time_slot: str) -> Dict[str, Any]:
        """Book an appointment using MCP context"""
        try:
            context = self.manager.get_context(session_id)
            if not context:
                return {"success": False, "message": "No active session context"}
            
            # Update context
            self.manager.update_context(session_id, 
                                     doctor_name=doctor_name,
                                     date_slot=date_slot,
                                     time_slot=time_slot,
                                     action_type=ActionType.BOOK)
            
            # Use existing booking tool
            datetime_model = DateTimeModel(date=f"{date_slot} {time_slot}")
            id_model = IdentificationNumberModel(id=context.user_id)
            
            result = set_appointment.invoke({
                "desired_date": datetime_model,
                "id_number": id_model,
                "doctor_name": doctor_name
            })
            
            if "Successfully done" in result:
                return {
                    "success": True,
                    "message": "Appointment booked successfully!",
                    "appointment_details": {
                        "doctor": doctor_name,
                        "date": date_slot,
                        "time": time_slot,
                        "patient_id": context.user_id
                    }
                }
            else:
                return {"success": False, "message": result}
                
        except Exception as e:
            return {"success": False, "message": f"Error booking appointment: {str(e)}"}
    
    def request_booking_confirmation(self, session_id: str, doctor_name: str, date_slot: str, time_slot: str) -> str:
        """Request confirmation for booking"""
        context = self.manager.get_context(session_id)
        if not context:
            return "No active session context"
        
        self.manager.update_context(session_id,
                                 doctor_name=doctor_name,
                                 date_slot=date_slot,
                                 time_slot=time_slot,
                                 action_type=ActionType.BOOK)
        
        return f"""**🛡️ Booking Confirmation Required**

**Appointment Details:**
• Doctor: {doctor_name}
• Date: {date_slot}
• Time: {time_slot}
• Patient ID: {context.user_id}

**Do you want to book this appointment?**

**Please respond:**
• **'yes'** to confirm booking
• **'no'** to cancel booking"""

class MCPCancellationTool:
    """MCP Tool for appointment cancellation"""
    
    def __init__(self, manager: MCPAppointmentManager):
        self.manager = manager
    
    def get_user_appointments_with_letters(self, session_id: str) -> Dict[str, Any]:
        """Get user appointments with letter system"""
        try:
            context = self.manager.get_context(session_id)
            if not context:
                return {"success": False, "message": "No active session context"}
            
            # Use existing tool
            result = get_user_appointments.invoke({
                "id_number": IdentificationNumberModel(id=context.user_id)
            })
            
            return {"success": True, "appointments": result}
            
        except Exception as e:
            return {"success": False, "message": f"Error getting appointments: {str(e)}"}
    
    def cancel_appointment_by_letter(self, session_id: str, appointment_letter: str) -> Dict[str, Any]:
        """Cancel appointment by letter (a, b, c, etc.)"""
        try:
            context = self.manager.get_context(session_id)
            if not context:
                return {"success": False, "message": "No active session context"}
            
            # Convert letter to number
            appointment_num = ord(appointment_letter.lower()) - ord('a') + 1
            
            # Get appointments to find the specific one
            appointments_result = self.get_user_appointments_with_letters(session_id)
            if not appointments_result["success"]:
                return appointments_result
            
            # Parse appointments to find the specific one
            appointments_text = appointments_result["appointments"]
            lines = appointments_text.split('\n')
            appointment_lines = [line for line in lines if line.strip() and line.strip()[0].isalpha() and '. 🟢' in line]
            
            if appointment_num < 1 or appointment_num > len(appointment_lines):
                return {
                    "success": False, 
                    "message": f"Invalid appointment letter. Please select between a and {chr(ord('a') + len(appointment_lines) - 1)}"
                }
            
            # Extract appointment details
            appointment_line = appointment_lines[appointment_num - 1]
            doctor_name = appointment_line.split('. 🟢 Dr. ')[1].split('\n')[0] if '. 🟢 Dr. ' in appointment_line else "Unknown Doctor"
            
            # Convert to lowercase for validation
            doctor_name_lower = doctor_name.lower()
            
            # Find corresponding date
            appointment_index = lines.index(appointment_line)
            date_line = None
            for i in range(appointment_index + 1, min(appointment_index + 5, len(lines))):
                if '📅 Date & Time:' in lines[i]:
                    date_line = lines[i]
                    break
            
            if date_line:
                import re
                date_match = re.search(r'(\w+day, \w+ \d+, \d+) at (\d+:\d+ [AP]M)', date_line)
                if date_match:
                    date_str = date_match.group(1)
                    time_str = date_match.group(2)
                    from datetime import datetime
                    try:
                        dt = datetime.strptime(f"{date_str} {time_str}", "%A, %B %d, %Y %I:%M %p")
                        formatted_date = dt.strftime("%d-%m-%Y %H:%M")
                    except:
                        formatted_date = "Unknown Date"
                else:
                    formatted_date = "Unknown Date"
            else:
                formatted_date = "Unknown Date"
            
            # Update context
            self.manager.update_context(session_id,
                                     doctor_name=doctor_name_lower,
                                     date_slot=formatted_date,
                                     appointment_letter=appointment_letter,
                                     action_type=ActionType.CANCEL)
            
            return {
                "success": True,
                "appointment_details": {
                    "doctor": doctor_name,
                    "date": formatted_date,
                    "letter": appointment_letter,
                    "patient_id": context.user_id
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error cancelling appointment: {str(e)}"}
    
    def execute_cancellation(self, session_id: str) -> Dict[str, Any]:
        """Execute the actual cancellation"""
        try:
            context = self.manager.get_context(session_id)
            if not context:
                return {"success": False, "message": "No active session context"}
            
            if context.action_type != ActionType.CANCEL:
                return {"success": False, "message": "No pending cancellation"}
            
            # Use existing cancellation tool
            datetime_model = DateTimeModel(date=context.date_slot)
            id_model = IdentificationNumberModel(id=context.user_id)
            
            result = cancel_appointment.invoke({
                "date": datetime_model,
                "id_number": id_model,
                "doctor_name": context.doctor_name
            })
            
            if "Successfully cancelled" in result:
                # Clear context after successful cancellation
                self.manager.clear_context(session_id)
                return {
                    "success": True,
                    "message": "Appointment cancelled successfully!",
                    "cancelled_appointment": {
                        "doctor": context.doctor_name,
                        "date": context.date_slot,
                        "patient_id": context.user_id
                    }
                }
            else:
                return {"success": False, "message": result}
                
        except Exception as e:
            return {"success": False, "message": f"Error executing cancellation: {str(e)}"}
    
    def request_cancellation_confirmation(self, session_id: str, appointment_letter: str) -> str:
        """Request confirmation for cancellation"""
        result = self.cancel_appointment_by_letter(session_id, appointment_letter)
        
        if not result["success"]:
            return f"**❌ Error:** {result['message']}"
        
        appointment_details = result["appointment_details"]
        context = self.manager.get_context(session_id)
        
        return f"""**🛡️ Cancellation Confirmation Required**

**Appointment Details:**
• Doctor: {appointment_details['doctor']}
• Date: {appointment_details['date']}
• Patient ID: {context.user_id}

**Do you want to cancel this appointment?**

**Please respond:**
• **'yes'** to confirm cancellation
• **'no'** to keep the appointment"""

class MCPAgent:
    """Main MCP Agent that coordinates all tools"""
    
    def __init__(self):
        self.manager = MCPAppointmentManager()
        self.booking_tool = MCPBookingTool(self.manager)
        self.cancellation_tool = MCPCancellationTool(self.manager)
    
    def process_request(self, session_id: str, user_id: int, message: str) -> Dict[str, Any]:
        """Process user request using MCP tools"""
        import re
        
        # Create context if it doesn't exist
        if session_id not in self.manager.contexts:
            self.manager.create_context(session_id, user_id)
        
        message_lower = message.lower()
        
        # Handle cancellation requests
        if 'cancel' in message_lower and 'appointment' in message_lower:
            # Extract appointment letter
            appointment_match = re.search(r'appointment #?([a-z]|\d+)', message_lower)
            if appointment_match:
                appointment_ref = appointment_match.group(1)
                if appointment_ref.isalpha():
                    # Letter-based cancellation
                    confirmation_message = self.cancellation_tool.request_cancellation_confirmation(session_id, appointment_ref)
                    return {
                        "action": "cancellation_confirmation",
                        "message": confirmation_message,
                        "requires_confirmation": True
                    }
                else:
                    # Number-based cancellation (convert to letter)
                    appointment_letter = chr(ord('a') + int(appointment_ref) - 1)
                    confirmation_message = self.cancellation_tool.request_cancellation_confirmation(session_id, appointment_letter)
                    return {
                        "action": "cancellation_confirmation",
                        "message": confirmation_message,
                        "requires_confirmation": True
                    }
            else:
                # Show appointments for cancellation
                appointments_result = self.cancellation_tool.get_user_appointments_with_letters(session_id)
                if appointments_result["success"]:
                    return {
                        "action": "show_appointments",
                        "message": f"**Your Appointments:**\n\n{appointments_result['appointments']}\n\n**To cancel an appointment, please tell me which one (a, b, c, etc.)**"
                    }
                else:
                    return {
                        "action": "error",
                        "message": appointments_result["message"]
                    }
        
        # Handle confirmation responses
        elif any(word in message_lower for word in ['yes', 'confirm', 'proceed']):
            context = self.manager.get_context(session_id)
            if context and context.action_type == ActionType.CANCEL:
                # Execute cancellation
                result = self.cancellation_tool.execute_cancellation(session_id)
                if result["success"]:
                    return {
                        "action": "cancellation_completed",
                        "message": f"**✅ {result['message']}**\n\n**Cancelled Appointment:**\n• Doctor: {result['cancelled_appointment']['doctor']}\n• Date: {result['cancelled_appointment']['date']}\n• Patient ID: {result['cancelled_appointment']['patient_id']}"
                    }
                else:
                    return {
                        "action": "error",
                        "message": f"**❌ Cancellation Failed:** {result['message']}"
                    }
            elif context and context.action_type == ActionType.BOOK:
                # Execute booking
                result = self.booking_tool.book_appointment(session_id, context.doctor_name, context.date_slot, context.time_slot)
                if result["success"]:
                    return {
                        "action": "booking_completed",
                        "message": f"**✅ {result['message']}**\n\n**Booked Appointment:**\n• Doctor: {result['appointment_details']['doctor']}\n• Date: {result['appointment_details']['date']}\n• Time: {result['appointment_details']['time']}\n• Patient ID: {result['appointment_details']['patient_id']}"
                    }
                else:
                    return {
                        "action": "error",
                        "message": f"**❌ Booking Failed:** {result['message']}"
                    }
            else:
                return {
                    "action": "error",
                    "message": "No pending action to confirm"
                }
        
        # Handle decline responses
        elif any(word in message_lower for word in ['no', 'cancel', 'abort']):
            context = self.manager.get_context(session_id)
            if context and context.action_type == ActionType.CANCEL:
                self.manager.clear_context(session_id)
                return {
                    "action": "cancellation_cancelled",
                    "message": "**✅ Cancellation Cancelled**\n\nYour appointment has been kept. Is there anything else I can help you with?"
                }
            elif context and context.action_type == ActionType.BOOK:
                self.manager.clear_context(session_id)
                return {
                    "action": "booking_cancelled",
                    "message": "**✅ Booking Cancelled**\n\nNo appointment was booked. Is there anything else I can help you with?"
                }
            else:
                return {
                    "action": "error",
                    "message": "No pending action to cancel"
                }
        
        # Handle booking requests
        elif any(word in message_lower for word in ['book', 'schedule', 'appointment']) and any(word in message_lower for word in ['slot', 'dr.', 'doctor']):
            import re
            
            # Extract booking details from query - handle multiple formats
            doctor_match = None
            
            # Try "Doctor: Name (Specialization)" format first
            doctor_match = re.search(r'doctor:\s*([a-zA-Z\s]+)(?:\s*\([^)]+\))?', message_lower)
            if not doctor_match:
                # Try "Dr. Name" format
                doctor_match = re.search(r'dr\.?\s*([a-zA-Z\s]+?)(?:\s+\([^)]+\))?', message_lower)
            if not doctor_match:
                # Try "doctor Name" format
                doctor_match = re.search(r'doctor\s+([a-zA-Z\s]+?)(?:\s+\([^)]+\))?', message_lower)
            
            # Look for date patterns
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', message)
            
            # Look for slot number
            slot_match = re.search(r'slot\s*(\d+)', message_lower)
            
            if doctor_match and date_match and slot_match:
                doctor_name = doctor_match.group(1).strip().lower()
                date_str = date_match.group(1)
                slot_number = int(slot_match.group(1))
                
                # Get available slots to find the time
                try:
                    from data_models.models import DateModel
                    result = check_availability_by_doctor.invoke({
                        "desired_date": DateModel(date=date_str),
                        "doctor_name": doctor_name
                    })
                    
                    if "Available slots:" in result:
                        slots_text = result.split("Available slots:")[1].strip()
                        available_slots = [slot.strip() for slot in slots_text.split(',') if slot.strip()]
                        
                        if 1 <= slot_number <= len(available_slots):
                            time_slot = available_slots[slot_number - 1]
                            
                            # Request booking confirmation
                            confirmation_message = self.booking_tool.request_booking_confirmation(session_id, doctor_name, date_str, time_slot)
                            return {
                                "action": "booking_confirmation",
                                "message": confirmation_message,
                                "requires_confirmation": True
                            }
                        else:
                            return {
                                "action": "error",
                                "message": f"Invalid slot number. Please select between 1 and {len(available_slots)}"
                            }
                    else:
                        return {
                            "action": "error",
                            "message": f"No availability found for Dr. {doctor_name.title()} on {date_str}"
                        }
                except Exception as e:
                    return {
                        "action": "error",
                        "message": f"Error checking availability: {str(e)}"
                    }
            else:
                return {
                    "action": "error",
                    "message": "I need doctor name, date, and slot number to book an appointment.\n\nExample: 'Book slot 1 with Dr. John Doe on 15-09-2025'"
                }
        
        # Handle availability checking
        elif any(word in message_lower for word in ['check', 'availability', 'available']) and any(word in message_lower for word in ['dr.', 'doctor']):
            import re
            
            # Extract doctor name and date from query
            doctor_match = re.search(r'dr\.?\s*([a-zA-Z\s]+?)(?:\s+on|\s+\d{2}-\d{2}-\d{4})', message_lower)
            if not doctor_match:
                doctor_match = re.search(r'doctor\s+([a-zA-Z\s]+?)(?:\s+on|\s+\d{2}-\d{2}-\d{4})', message_lower)
            
            # Look for date patterns
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', message)
            
            if doctor_match and date_match:
                doctor_name = doctor_match.group(1).strip()
                date_str = date_match.group(1)
                
                # Use the tool to check availability
                try:
                    from data_models.models import DateModel
                    result = check_availability_by_doctor.invoke({
                        "desired_date": DateModel(date=date_str),
                        "doctor_name": doctor_name
                    })
                    
                    if "Available slots:" in result:
                        response = f"**📅 Available time slots for {doctor_name.title()} on {date_str}:**\n\n{result}"
                    else:
                        response = f"**❌ No availability found for Dr. {doctor_name.title()} on {date_str}**\n\nPlease try a different date or doctor."
                    
                    return {
                        "action": "show_availability",
                        "message": response
                    }
                except Exception as e:
                    return {
                        "action": "error",
                        "message": f"**❌ Error checking availability:** {str(e)}"
                    }
            else:
                return {
                    "action": "error",
                    "message": "I need both the doctor name and date to check availability. Please try again.\n\nExample: 'Check availability for Dr. John Doe on 18-09-2025'"
                }
        
        # Handle view appointments
        elif any(word in message_lower for word in ['my appointments', 'show appointments', 'view appointments']):
            appointments_result = self.cancellation_tool.get_user_appointments_with_letters(session_id)
            if appointments_result["success"]:
                return {
                    "action": "show_appointments",
                    "message": appointments_result["appointments"]
                }
            else:
                return {
                    "action": "error",
                    "message": appointments_result["message"]
                }
        
        # Default response
        else:
            return {
                "action": "general",
                "message": "I'm here to help you with appointment booking and cancellation. What would you like to do?"
            }

# Global MCP Agent instance
mcp_agent = MCPAgent()
