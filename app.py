import streamlit as st
import re
import dns.resolver
import smtplib
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from streamlit_modal import Modal
# Data -------------------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    url: str = st.secrets['supabase_url']
    key: str = st.secrets['supabase_key']
    client: Client = create_client(url,key)
    return client

supabase = init_connection()
@st.cache_resource(ttl=3)
def run_query():
    return supabase.table('liveMails').select('*').execute()
rows = run_query()
df = pd.DataFrame(rows.data)

#-------------------------------------------------------------------------------------------------
now = datetime.now()
def is_valid_syntax(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

def check_domain(email):
    domain = email.split('@')[1]
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False

def check_smtp(email):
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(mx_records[0].exchange)

        server = smtplib.SMTP(mx_record)
        server.set_debuglevel(0)
        server.helo(server.local_hostname)  # server.local_hostname(Get local server hostname)
        server.mail('your_email@example.com')
        code, message = server.rcpt(email)
        server.quit()

        if code == 250:
            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def verify_email(email):
    if not is_valid_syntax(email):
        return "Invalid email syntax"
    if not check_domain(email):
        return "Domain does not exist"
    if not check_smtp(email):
        return "Email does not exist"
    return "Email is valid"
def read_txt():
  try:
    with open('emails.txt', 'r', encoding='utf-8') as file:
      content = file.read()
      print(content)
  except FileNotFoundError:
      print("Tệp không tồn tại.")
  except IOError:
      print("Có lỗi khi đọc tệp.")
def liveMails():
    df = pd.json_normalize(rows.data)
    if not df.empty:
        st.write(df)
if __name__ == "__main__":
    mails = st.text_area("Mails")
    btn = st.button('Check mails')
    valid, invalidSyntax, domainNotEx, emailNotEx, record = [],[],[],[],[]
    save_path = 'data/liveMails.csv'
    df = pd.DataFrame(valid, columns=["Mails"])
    df['Date'] = now.strftime('%Y-%m-%d %H:%M:%S')
    csv = df.to_csv(index=False)
    if btn:
        liveMails()
        if mails:
            lines = mails.split('\n')
            for i, line in enumerate(lines, start=1):
                result = verify_email(line.strip())
                if result =='Email is valid':
                    valid.append(line)
                elif result == 'Email does not exist':
                    emailNotEx.append(line)
                elif result == 'Domain does not exist':
                    domainNotEx.append(line)
                elif result == 'Invalid email syntax':
                    invalidSyntax.append(line)
        if valid:
            st.subheader('Email is valid')
            for i in valid:
                st.text(i)
                record = {
                    "Mails": i,
                    "Date": now.strftime('%Y-%m-%d %H:%M:%S')
                }
                response = supabase.table("liveMails").upsert(record).execute()
        if emailNotEx:
            st.subheader('Email does not exist')
            for i in emailNotEx:
                st.text(i)
        if domainNotEx:
            st.subheader('Domain does not exist')
            for i in domainNotEx:
                st.text(i)
        if invalidSyntax:
            st.subheader('Invalid email syntax')
            for i in invalidSyntax:
                st.text(i)

st.sidebar.title("---Live Mails---")
with st.sidebar:
    liveMails()
    delete = st.button('Delete All')
    if delete:
        response = supabase.table("liveMails").delete().neq("Mails", 0).execute()
