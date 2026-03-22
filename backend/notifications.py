import os
import math
from dotenv import load_dotenv

load_dotenv()

# ── Haversine Distance ─────────────────────────────────────────────────────────
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── Find Nearest Doctor ────────────────────────────────────────────────────────
def find_nearest_doctor(db, patient_lat, patient_lon):
    from database import Doctor

    doctors = db.query(Doctor).filter(
        Doctor.is_available == True,
        Doctor.latitude != None,
        Doctor.longitude != None
    ).all()

    if not doctors:
        return None

    nearest      = None
    min_distance = float("inf")

    for doctor in doctors:
        distance = haversine_distance(
            patient_lat, patient_lon,
            doctor.latitude, doctor.longitude
        )
        if distance < min_distance:
            min_distance = distance
            nearest      = doctor

    if nearest:
        nearest.distance_km = round(min_distance, 2)

    return nearest

# ── Send SMS ───────────────────────────────────────────────────────────────────
def send_sms_notification(doctor, patient_summary):
    try:
        from twilio.rest import Client

        SID   = os.getenv("TWILIO_ACCOUNT_SID")
        TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        FROM  = os.getenv("TWILIO_PHONE")

        if not all([SID, TOKEN, FROM]):
            print("Twilio credentials missing in .env")
            return False

        if not doctor.phone:
            print(f"Doctor {doctor.name} has no phone number")
            return False

        client = Client(SID, TOKEN)

        message = (
            f"MEDICATE-IT URGENT ALERT\n"
            f"High risk patient nearby.\n"
            f"Risk Score: {patient_summary['score']}/100\n"
            f"Urgency: {patient_summary['urgency']}\n"
            f"Symptoms: {patient_summary['symptoms']}\n"
            f"Distance: {getattr(doctor, 'distance_km', '?')} km\n"
            f"Please attend immediately."
        )

        client.messages.create(
            body=message,
            from_=FROM,
            to=doctor.phone
        )

        print(f"SMS sent to {doctor.phone}")
        return True

    except Exception as e:
        print(f"SMS failed: {str(e)}")
        return False

# ── Main Function ──────────────────────────────────────────────────────────────
def notify_nearest_doctor(db, patient_lat, patient_lon, patient_summary):
    doctor = find_nearest_doctor(db, patient_lat, patient_lon)

    if not doctor:
        return {
            "notified":  False,
            "reason":    "No available doctors found in database",
            "doctor":    None
        }

    sms_sent = send_sms_notification(doctor, patient_summary)

    return {
        "notified":              sms_sent,
        "doctor_name":           doctor.name,
        "doctor_phone":          doctor.phone,
        "doctor_hospital":       doctor.hospital or "Unknown",
        "doctor_specialization": doctor.specialization or "General",
        "distance_km":           getattr(doctor, "distance_km", None),
        "sms_sent":              sms_sent,
        "reason":                None if sms_sent else "SMS delivery failed"
    }