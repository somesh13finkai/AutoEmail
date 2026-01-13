import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
import pandas as pd
from src.config import get_agent
from src.infra.sqlite_db import SQLiteInvoiceRepository
from src.models import InvoiceStatus

# Page Config must be the first Streamlit command
st.set_page_config(page_title="Auto Invoice Reconciler", layout="wide", page_icon="🤖")

def main():
    st.title("")

    # 1. Dependency Injection (Initialize the Agent)
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = get_agent()
            st.success("System Initialized (Gmail + Gemini 2.0 + Tesseract)")
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            return

    # 2. Database Connection (For Sidebar & Analytics)
    repo = SQLiteInvoiceRepository()

    # --- SIDEBAR: DATABASE VIEW ---
    st.sidebar.header("Database Status")
    if st.sidebar.button("Refresh DB"):
        st.rerun()

    invoices = repo.get_all_invoices()
    
    pending = [i for i in invoices if i.status == InvoiceStatus.PENDING]
    received = [i for i in invoices if i.status == InvoiceStatus.RECEIVED]
    
    st.sidebar.subheader(f"Pending ({len(pending)})")
    # Show top 10 pending to avoid sidebar clutter
    for p in pending[:10]:
        st.sidebar.text(f"{p.invoice_number} - {p.vendor_email}")
    if len(pending) > 10:
        st.sidebar.text(f"...and {len(pending)-10} more")
        
    st.sidebar.divider()
    
    st.sidebar.subheader(f"Received ({len(received)})")
    for r in received[:10]:
        st.sidebar.success(f"{r.invoice_number}")
    if len(received) > 10:
        st.sidebar.text(f"...and {len(received)-10} more")

    # --- MAIN AREA: TABS ---
    tab1, tab2, tab3 = st.tabs(["🚀 Kickoff & Reminders", "🔄 Process Replies", "📊 Analytics Dashboard"])
    
    # --- TAB 1: KICKOFF & REMINDERS ---
    with tab1:
        st.subheader("Manual Kickoff")
        st.info("Start a new conversation by sending the list of missing invoices to a vendor.")
        
        target_email = st.text_input("Vendor Email (Target)", value="orionbee13@gmail.com")
        
        if st.button("Send Initial Request"):
            with st.spinner(f"Gathering pending invoices for {target_email}..."):
                try:
                    result = st.session_state.agent.start_reconciliation_flow(target_email)
                    if "Request sent" in result:
                        st.success(result)
                    else:
                        st.warning(result)
                except Exception as e:
                    st.error(f"Error sending kickoff: {e}")
        
        st.divider()
        st.subheader("Auto-Reminders")
        st.info("Check for vendors with pending invoices who haven't been contacted in 2 days.")
        
        if st.button("Run Daily Reminder Check"):
            with st.spinner("Scanning database for stale threads..."):
                try:
                    reminded = st.session_state.agent.run_daily_reminders()
                    if reminded:
                        st.success(f"✅ Sent reminders to {len(reminded)} vendors: {', '.join(reminded)}")
                    else:
                        st.info("✅ No reminders needed today (all vendors contacted recently).")
                except AttributeError:
                    st.error("Agent missing 'run_daily_reminders' method. Please update agent.py")

    # --- TAB 2: PROCESS REPLIES ---
    with tab2:
        st.subheader("Check for Vendor Replies")
        st.info("Fetch unread emails, process attachments, and draft replies.")
        
        if st.button("Run Reconciliation Loop"):
            with st.spinner("Fetching emails, reading attachments, updating DB..."):
                report = st.session_state.agent.run_reconciliation_cycle()
                st.session_state.report = report
            
            if not report:
                st.warning("No new relevant emails found.")
            else:
                st.success(f"Analysis Complete! Found {len(report)} threads to action.")

        # --- APPROVAL QUEUE ---
        if "report" in st.session_state and st.session_state.report:
            st.divider()
            st.subheader("📝 Approval Queue")
            
            for idx, item in enumerate(st.session_state.report):
                # Handle Manual Review Flags (ZIPs/Links)
                if "status" in item and "MANUAL REVIEW" in item["status"]:
                    st.error(f"{item['status']} - {item['sender']}")
                    st.caption(f"Thread ID: {item['thread_id']}")
                    if st.button("Mark Handled / Clear", key=f"clear_{idx}"):
                        st.rerun()
                    st.divider()
                    continue

                # Handle Simple Logs
                if "status" in item and "Log:" in item["status"]:
                    st.text(item['status'])
                    continue

                # Handle Drafts
                with st.container():
                    st.markdown(f"### Thread: `{item['sender']}`")
                    st.caption(f"Thread ID: {item['thread_id']}")
                    
                    c1, c2 = st.columns(2)
                    received_str = ', '.join(item['received']) if item['received'] else "None"
                    missing_str = ', '.join(item['missing']) if item['missing'] else "None"
                    
                    c1.success(f"✅ Just Received: {received_str}")
                    c2.error(f"❌ Still Missing: {missing_str}")
                    
                    if item.get('poc_update'):
                        st.warning(f"⚠️ POC Update Detected: {item['poc_update']}")

                    draft_text = st.text_area(
                        "Proposed Reply:", 
                        value=item['draft_reply'], 
                        height=200, 
                        key=f"draft_{idx}"
                    )
                    
                    if st.button("Approve & Send Reply", key=f"btn_{idx}"):
                        with st.spinner("Sending email..."):
                            try:
                                st.session_state.agent.send_approved_reply(
                                    item['thread_id'], 
                                    item['sender'], 
                                    draft_text
                                )
                                st.success("Sent!")
                                item['status'] = 'Sent' # Mark visually as sent
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to send: {e}")
                st.divider()

    # --- TAB 3: ANALYTICS DASHBOARD ---
    with tab3:
        st.subheader("📊 Daily Reconciliation Report")
        
        # 1. Fetch Data
        raw_invoices = repo.get_all_invoices()
        
        # 2. Convert to DataFrame
        if not raw_invoices:
            st.warning("Database is empty.")
        else:
            data = []
            for i in raw_invoices:
                data.append({
                    "Invoice No": i.invoice_number,
                    "Status": i.status.value,
                    "Hotel": i.hotel_name,
                    "Client": i.workspace,
                    "Amount": i.amount,
                    "GSTIN": i.gstin,
                    # Fallback for old DB schema compatibility
                    "Received Date": getattr(i, 'received_at', None) 
                })
            
            df = pd.DataFrame(data)
            
            # 3. Filter for Received
            received_df = df[df["Status"] == "RECEIVED"].copy()
            
            # 4. KPI Cards
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Received", len(received_df))
            c2.metric("Total Value", f"${received_df['Amount'].sum():,.2f}")
            c3.metric("Total Pending", len(df[df["Status"] == "PENDING"]))

            st.divider()

            if not received_df.empty:
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("### 🏢 Client Breakdown (Value)")
                    client_stats = received_df.groupby("Client")["Amount"].sum().reset_index()
                    client_stats = client_stats.sort_values(by="Amount", ascending=False)
                    st.dataframe(
                        client_stats.style.format({"Amount": "${:,.2f}"}), 
                        use_container_width=True, 
                        hide_index=True
                    )

                with col_b:
                    st.markdown("### 🏨 Hotel / GST Breakdown")
                    hotel_stats = received_df.groupby(["Hotel", "GSTIN"]).agg(
                        Count=('Invoice No', 'count'),
                        Total_Value=('Amount', 'sum')
                    ).reset_index()
                    st.dataframe(
                        hotel_stats.style.format({"Total_Value": "${:,.2f}"}), 
                        use_container_width=True, 
                        hide_index=True
                    )
                
                st.markdown("### 📜 Recent Transactions")
                st.dataframe(received_df.tail(10), use_container_width=True, hide_index=True)
            else:
                st.info("No invoices received yet. Statistics will appear here once data flows in.")

if __name__ == "__main__":
    main()