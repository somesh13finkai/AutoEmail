import time
import schedule
from src.config import get_agent

def job_process_replies():
    print("⏰ Running Scheduled Reply Check...")
    agent = get_agent()
    # Use the logic from agent to check emails and draft replies
    # Note: In a headless script, you might want to auto-approve drafts 
    # OR just flag them. For now, we'll run the cycle to update DB.
    report = agent.run_reconciliation_cycle()
    if report:
        print(f"✅ Processed {len(report)} threads.")

def job_send_reminders():
    print("⏰ Running Daily Reminder Check...")
    agent = get_agent()
    reminded = agent.run_daily_reminders()
    if reminded:
        print(f"📨 Sent reminders to: {reminded}")

# Schedule
schedule.every(10).minutes.do(job_process_replies) # Check email every 10 mins
schedule.every().day.at("09:00").do(job_send_reminders) # Remind at 9 AM

print("🚀 System started. Waiting for schedule...")
while True:
    schedule.run_pending()
    time.sleep(1)