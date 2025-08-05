from app.services.email_service import send_summary_email

if __name__ == "__main__":
    send_summary_email(
        to_email="info@coachintel.ai",
        summary="This is a test summary.",
        action_items=["Action 1", "Action 2"],
        progress_notes="These are your progress notes."
    )
    print("Test email sent!")