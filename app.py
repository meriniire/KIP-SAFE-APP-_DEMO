import streamlit as st # type: ignore
from datetime import datetime
from PIL import Image
import csv
import bcrypt
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from twilio.rest import Client



# Constants
USER_FILE = 'users.csv'
RESET_TOKENS_FILE = 'reset_tokens.csv'
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$")

# Custom CSS
def load_css():
    st.markdown("""
    <style>
    .stApp {
        background-color: #f0f2f6;
        font-family: 'Helvetica', sans-serif;
    }
    .big-font {
        font-size: 2.5rem !important;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 1rem;
    }
    .date-time {
        font-size: 1rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        color: #ffffff;
        background-color: #3B82F6;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 0.375rem;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #2563EB;
    }
    .sign-up {
        background-color: #10B981 !important;
    }
    .sign-up:hover {
        background-color: #059669 !important;
    }
    .feature-box {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# User management functions
def load_users():
    users = {}
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                users[row[0]] = {
                    'password': row[1],
                    'email': row[2],
                    'created_at': row[3],
                    'last_login': row[4]
                }
    return users

def save_users(users):
    with open(USER_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'password', 'email', 'created_at', 'last_login'])
        for username, data in users.items():
            writer.writerow([username, data['password'], data['email'], data['created_at'], data['last_login']])

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

def sanitize_input(input_string):
    return re.sub(r'[<>&\'"]/g', '', input_string)

def validate_email(email):
    return EMAIL_REGEX.match(email)

def validate_username(username):
    return USERNAME_REGEX.match(username)

def validate_password(password):
    return PASSWORD_REGEX.match(password)

def create_user(username, password, email):
    users = load_users()
    if username not in users:
        if not validate_username(username):
            return False, "Invalid username format. Use 3-20 alphanumeric characters or underscores."
        if not validate_email(email):
            return False, "Invalid email format."
        if not validate_password(password):
            return False, "Password must be at least 8 characters long and contain both letters and numbers."
        
        hashed_password = hash_password(password)
        current_time = datetime.now().isoformat()
        users[username] = {
            'password': hashed_password,
            'email': email,
            'created_at': current_time,
            'last_login': ''
        }
        save_users(users)
        return True, "Account created successfully!"
    return False, "Username already exists."

def authenticate_user(username, password):
    users = load_users()
    if username in users and verify_password(users[username]['password'], password):
        users[username]['last_login'] = datetime.now().isoformat()
        save_users(users)
        return True
    return False


# KIP SAFE APP functionality
def kip_safe_app():
    # Input fields for users to enter their Twilio credentials
    st.subheader("Enter Your Twilio Credentials")
    twilio_account_sid = st.text_input("Twilio Account SID")
    twilio_auth_token = st.text_input("Twilio Auth Token", type="password")
    twilio_phone_number = st.text_input("Your Twilio Phone Number")
    recipient_phone_number = st.text_input("Recipient Phone Number")

    # Initialize session state for user input
    if 'vehicle_no' not in st.session_state:
        st.session_state.vehicle_no = ""

    # Function to send audio file via SMS
    def send_audio(audio_url, vehicle_no, alert_title, location_url=None):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_body = (
            f"Alert: {alert_title}\n"
            f"Audio alert for Vehicle No: {vehicle_no}\n"
            f"Audio message link: {audio_url}\n"
            f"Date and Time: {current_time}"
        )
        if location_url:
            message_body += f"\nLocation: {location_url}"

        try:
            client = Client(twilio_account_sid, twilio_auth_token)
            message = client.messages.create(
                body=message_body,
                from_=twilio_phone_number,
                to=recipient_phone_number,
                media_url=audio_url
            )
            return True, "Audio sent successfully!"
        except Exception as e:
            return False, f"Error sending audio: {e}"

    # Function to send a text message
    def send_text_message(text_message):
        try:
            client = Client(twilio_account_sid, twilio_auth_token)
            message = client.messages.create(
                body=text_message,
                from_=twilio_phone_number,
                to=recipient_phone_number
            )
            return True, "Text message sent successfully!"
        except Exception as e:
            return False, f"Error sending text message: {e}"

    # Function to get the current location
    def get_location():
        response = requests.get('https://ipinfo.io/loc')
        lat_long = response.text.strip().split(',')
        if len(lat_long) == 2:
            latitude, longitude = lat_long
            location_url = f"https://maps.google.com/?q={latitude},{longitude}"
            return location_url
        return None

    # Header
    st.markdown('<div class="header">KIP SAFE APP</div>', unsafe_allow_html=True)

    # Button to get current location
    location_url = None
    if st.button("Get Current Location", key="get_location"):
        location_url = get_location()
        if location_url:
            st.success(f"Location detected: {location_url}")
        else:
            st.error("Could not detect location.")

    # Input fields organized in a container
    with st.container():
        st.subheader("Select Category", anchor="category")
        vehicle_no_input = st.text_input("Vehicle No.", value=st.session_state.vehicle_no, key="vehicle_no_input")

    # Audio alert buttons
    st.subheader("Audio Alerts")
    audio_cols = st.columns(3)

    audio_buttons = [
        ("Voice Kidnappers", "https://drive.google.com/uc?id=1VoQzrEC6sgH9aB1JyPLeXOMI-kLqtB5J"),
        ("Voice Armed Robbers", "https://drive.google.com/uc?id=1LWu6VkL6VNA-hmnugXRQ6OOtSMIJEbYv"),
        ("Voice Gun Shot", "https://drive.google.com/uc?id=1Ke_1pHV8LzCS_gVd0er4kwwqs2aaRXRy")
    ]

    for col, (label, url) in zip(audio_cols, audio_buttons):
        with col:
            if st.button(label, key=label):
                success, message = send_audio(url, vehicle_no_input, label, location_url)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    # Section for sending a normal text message
    st.subheader("Send a Normal Text Message")
    text_message_input = st.text_area("Type your message here", height=100, key="text_message", placeholder="Enter your message...", help="Please keep your message concise.")

    if st.button("Send Text Message"):
        if text_message_input.strip():  # Validate input is not empty
            success, message = send_text_message(text_message_input)
            if success:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error("Please enter a message before sending.")

    # Refresh button to reload the page
    if st.button("Refresh"):
        st.session_state.clear()  # Clear session state to reset inputs
        st.stop()  # Stop the script to refresh

    if st.button("Sign Out"):
        del st.session_state.user
        st.session_state.page = 'home'
        st.success("Signed out successfully!")
        
# Streamlit UI functions
def main():
    load_css()

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        # Display logo
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        logo = Image.open("logo.png")
        st.image(logo, use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<p class="big-font">Welcome</p>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">The Security Alert System for Taxi Rides</p>', unsafe_allow_html=True)

        # Display current date and time
        now = datetime.now()
        st.markdown(f'<p class="date-time">{now.strftime("%B %d, %Y %H:%M:%S")}</p>', unsafe_allow_html=True)

        if 'page' not in st.session_state:
            st.session_state.page = 'home'

        # Call the appropriate page function based on the session state
        if st.session_state.page == 'home':
            home_page()
        elif st.session_state.page == 'signin':
            signin_page()
        elif st.session_state.page == 'signup':
            signup_page()
        elif st.session_state.page == 'forgot_password':
            forgot_password_page()
        elif st.session_state.page == 'reset_password':
            reset_password_page()
        elif 'user' in st.session_state:
            if st.session_state.page == 'kip_safe_app':
                kip_safe_app()  # Call the KIP SAFE APP functionality
            else:
                user_dashboard()
        elif st.session_state.page == 'change_password':
            change_password_page()

def home_page():
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("Sign In"):
            st.session_state.page = 'signin'

    with col_btn2:
        if st.button("Sign Up", key="sign_up"):
            st.session_state.page = 'signup'

    st.write("")
    st.write("")

    # Feature highlights
    st.subheader("Why Choose KIP SAFE?")

    col_feat1, col_feat2 = st.columns(2)

    with col_feat1:
        st.markdown('<div class="feature-box"><span class="feature-icon">🚀</span><br><strong>Real-time Alerts</strong><br>Instant notifications for enhanced safety</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-box"><span class="feature-icon">🔒</span><br><strong>Secure Rides</strong><br>Advanced encryption for data protection</div>', unsafe_allow_html=True)

    with col_feat2:
        st.markdown('<div class="feature-box"><span class="feature-icon">📍</span><br><strong>GPS Tracking</strong><br>Accurate location monitoring for peace of mind</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-box"><span class="feature-icon">🌟</span><br><strong>24/7 Support</strong><br>Round-the-clock assistance for users</div>', unsafe_allow_html=True)

def signin_page():
    st.subheader("Sign In")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign In", key="signin_button"):
        if authenticate_user(sanitize_input(username), password):
            st.success("Signed in successfully!")
            st.session_state.user = username
            st.session_state.page = 'user_dashboard'  # Redirect to dashboard
        else:
            st.error("Invalid username or password")

    if st.button("Back to Home"):
        st.session_state.page = 'home'

def signup_page():
    st.subheader("Sign Up")
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Sign Up"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, message = create_user(sanitize_input(username), password, sanitize_input(email))
            if success:
                st.success(message)
                st.session_state.page = 'signin'  # Redirect to dashboard
            else:
                st.error(message)
    if st.button("Back to Home"):
        st.session_state.page = 'home'


def user_dashboard():
    st.subheader(f"Welcome, {st.session_state.user}!")
    st.markdown("You can access your dashboard from here:")
    
     # Add a link to the KIP SAFE APP
    if st.button("Access KIP SAFE APP"):
        st.session_state.page = 'kip_safe_app'

    if st.button("Sign Out"):
        del st.session_state.user
        st.session_state.page = 'home'
        st.success("Signed out successfully!")

    # Placeholder for user dashboard content
    st.write("This is your KIP SAFE dashboard. More features will be added here.")

if __name__ == "__main__":
    main()