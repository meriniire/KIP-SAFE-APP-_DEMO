# KIP SAFE App

## Overview

KIP SAFE is a security alert system designed for taxi rides. The app allows users to send alerts via SMS, including audio messages, to designated contacts. It also provides real-time GPS location tracking for enhanced safety.

## Features

- User authentication (sign up and sign in)
- Send SMS alerts using Twilio
- Send audio alerts
- Retrieve current GPS location
- User-friendly interface

## Requirements

To run this application, you need to have the following Python packages installed:

- streamlit
- Pillow
- bcrypt
- requests
- twilio

You can install the requirements using:

```bash

pip install -r requirements.txt


Twilio Credentials: You need to input your own Twilio credentials to use the SMS functionality. Update the following fields within the app:
Twilio Account SID
Twilio Auth Token
Your Twilio Phone Number
Recipient Phone Number (the number you want to send alerts to)
These fields can be found in your [Twilio account dashboard]. You will be prompted to enter them when you run the app.

Run the application
streamlit run app.py


