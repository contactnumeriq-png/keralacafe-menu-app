import streamlit as st
import json
import os
import qrcode
from io import BytesIO
import time
import firebase_admin
from firebase_admin import credentials, db

st.set_page_config(page_title="Kerala Cafe Menu", page_icon="🍔", layout="centered")

# ==========================================
# ഫയർബേസ് കണക്ഷൻ 
# ==========================================
DATABASE_URL = "https://keralacafe-menu-default-rtdb.asia-southeast1.firebasedatabase.app/" # താങ്കളുടെ ഡാറ്റാബേസ് ലിങ്ക് ഇവിടെ നൽകുക

try:
    firebase_app = firebase_admin.get_app()
except ValueError:
    key_dict = json.loads(st.secrets["firebase_secret"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })

def get_orders():
    orders_ref = db.reference('orders')
    data = orders_ref.get()
    if data:
        return [val for key, val in data.items()]
    return []

def save_order(order_data):
    orders_ref = db.reference('orders')
    orders_ref.child(str(order_data['id'])).set(order_data)

def update_order_status(order_id, status, end_time, manual_time):
    order_ref = db.reference(f'orders/{order_id}')
    order_ref.update({'status': status, 'end_time': end_time, 'manual_time': manual_time})

def update_payment(order_id, payment_status):
    order_ref = db.reference(f'orders/{order_id}')
    order_ref.update({'payment': payment_status})

MENU_FILE = "menu_data.json"

def load_menu():
    if os.path.exists(MENU_FILE):
        with open(MENU_FILE, "r") as f:
            return json.load(f)
    return {
        "പ്രധാന വിഭവങ്ങൾ (Main Course)": [
            {"name": "ചിക്കൻ ബിരിയാണി", "price": 150, "prep_time": 900, "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=200"},
            {"name": "പൊറോട്ട", "price": 15, "prep_time": 600, "image": "https://images.unsplash.com/photo-1628128362678-75c61dff6e9d?w=200"}
        ],
        "പാനീയങ്ങൾ (Drinks)": [
            {"name": "ഫ്രഷ് ലൈം", "price": 30, "prep_time": 300, "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=200"}
        ]
    }

def save_menu(menu_data):
    with open(MENU_FILE, "w") as f:
        json.dump(menu_data, f)

menu_data = load_menu()

if 'cart' not in st.session_state: st.session_state.cart = {} 
if 'show_bill_page' not in st.session_state: st.session_state.show_bill_page = False
if 'my_table' not in st.session_state: st.session_state.my_table = 1 

all_orders = get_orders()

query_params = st.query_params
role = query_params.get("role", "demo")

if role == "customer":
    mode = "📱 കസ്റ്റമർ മെനു"
    st.session_state.my_table = int(query_params.get("table", 1))
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;} [data-testid="collapsedControl"] {display: none;} .stButton>button {border-radius: 8px;} </style>""", unsafe_allow_html=True)
else:
    st.sidebar.title("നിയന്ത്രണ പാനൽ")
    mode = st.sidebar.radio("സ്ക്രീൻ തിരഞ്ഞെടുക്കുക:", ["📱 കസ്റ്റമർ മെനു", "👨‍🍳 കിച്ചൺ & ക്യാഷിയർ", "⚙️ അഡ്മിൻ പാനൽ"])

# ==========================================
# 1. കസ്റ്റമർ മെനു (MOBILE OPTIMIZED VIEW)
# ==========================================
if mode == "📱 കസ്റ്റമർ മെനു":
    
    if st.session_state.show_bill_page:
        st.title("💳 ബിൽ പേയ്മെന്റ്")
        my_table = st.session_state.my_table
        my_unpaid_orders = [o for o in all_orders if o.get('table') == my_table and o.get('payment') == 'Unpaid']
        
        if not my_unpaid_orders:
            st.info("ഈ ടേബിളിൽ നിലവിൽ അടക്കാൻ ബാക്കിയുള്ള ബില്ലുകൾ ഒന്നുമില്ല.")
            if st.button("← മെനുവിലേക്ക് മടങ്ങുക"):
                st.session_state.show_bill_page = False
                st.rerun()
        else:
            st.write("### 🧾 കഴിച്ച വിഭവങ്ങൾ:")
            total_bill = 0
            for o in my_unpaid_orders:
                for item in o.get('items', []):
                    item_total = item['price'] * item['qty']
                    total_bill += item_total
                    st.write(f"🔹 {item['qty']} x {item['name']} (₹{item_total})")
                    
            st.markdown(f"## 💰 ആകെ: ₹{total_bill}")
            st.divider()
            
            pay_method = st.radio("പേയ്മെന്റ് രീതി:", ["📱 UPI (GPay, PhonePe)", "💵 Pay at Counter (ക്യാഷ്)"])
            
            if "UPI" in pay_method:
                upi_link = f"upi://pay?pa=keralacafe@upi&pn=KeralaCafe&am={total_bill}&cu=INR"
                qr = qrcode.QRCode(box_size=6, border=2)
                qr.add_data(upi_link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=200)
                
            confirm_text = "Pay at Counter & Close Bill" if "Counter" in pay_method else f"Pay ₹{total_bill} & Close Bill"
            
            if st.button(confirm_text, type="primary", use_container_width=True):
                payment_status = "Cash Pending" if "Counter" in pay_method else "PAID via UPI"
                for o in my_unpaid_orders:
                    update_payment(o['id'], payment_status)
                st.success("✅ പേയ്മെന്റ് വിജയകരം! നന്ദി.")
                time.sleep(2)
                st.session_state.show_bill_page = False
                st.rerun()
                
            if st.button("← കൂടുതൽ ഓർഡർ ചെയ്യാൻ മടങ്ങുക"):
                st.session_state.show_bill_page = False
                st.rerun()

    else:
        st.markdown(f"<h2 style='text-align: center;'>🍽️ Table {st.session_state.my_table}</h2>", unsafe_allow_html=True)
        
        if role != "customer":
            st.session_state.my_table = st.sidebar.number_input("ടേബിൾ നമ്പർ മാറ്റുക:", min_value=1, value=st.session_state.my_table)
        
        # 1. ലൈവ് ഓർഡർ സ്റ്റാറ്റസ്
        my_orders = [o for o in all_orders if o.get('table') == st.session_state.my_table and o.get('payment') == 'Unpaid']
        if my_orders:
            with st.expander("🔔 ഓർഡർ സ്റ്റാറ്റസ് (Live)", expanded=True):
                for order in my_orders:
                    if order['status'] == 'Pending':
                        st.warning(f"#{order['id']} - ⏳ കിച്ചൺ കാത്തിരിക്കുന്നു...")
                    elif order['status'] == 'Accepted':
                        rem_time = int(order['end_time'] - time.time())
                        if rem_time > 0:
                            mins, secs = divmod(rem_time, 60)
                            st.info(f"#{order['id']} - 👨‍🍳 തയ്യാറാകുന്നു! ({mins:02d}:{secs:02d})")
                        else:
                            st.success(f"#{order['id']} - ✅ ഭക്ഷണം തയ്യാറാണ്!")
                if st.button("🔄 റീഫ്രഷ് ചെയ്യുക", use_container_width=True):
                    st.rerun()

        # 2. സ്മാർട്ട് കാർട്ട് (ഏറ്റവും മുകളിൽ)
        cart_items = sum(d['qty'] for d in st.session_state.cart.values())
        cart_title = f"🛒 നിങ്ങളുടെ കാർട്ട് ({cart_items} items)" if cart_items > 0 else "🛒 കാർട്ട് കാലിയാണ്"
        
        with st.expander(cart_title, expanded=(cart_items > 0)):
            if not st.session_state.cart:
                st.write("താഴെ നിന്നും ഭക്ഷണം തിരഞ്ഞെടുക്കുക.")
            else:
                total = sum(d['price'] * d['qty'] for d in st.session_state.cart.values())
                for item_name, data in st.session_state.cart.items():
                    st.write(f"**{data['qty']} x {data['name']}** (₹{data['price'] * data['qty']})")
                
                st.markdown(f"### ആകെ: ₹{total}")
                
                if st.button("👨‍🍳 Send Order to Kitchen", type="primary", use_container_width=True):
                    max_time = max([i['prep_time'] for i in st.session_state.cart.values()])
                    order_id = int(time.time()) % 100000
                    new_order = {
                        "id": order_id, 
                        "table": st.session_state.my_table,
                        "status": "Pending",
                        "items": list(st.session_state.cart.values()),
                        "suggested_time": max_time,
                        "end_time": 0,
                        "manual_time": 0,
                        "total_bill": total,
                        "payment": "Unpaid" 
                    }
                    save_order(new_order)
                    st.session_state.cart = {} 
                    st.success("✅ ഓർഡർ കിച്ചണിലേക്ക് അയച്ചു!")
                    st.rerun()

        st.divider()

        # 3. വിഭവങ്ങൾ (Mobile Optimized App-Style Cards)
        for category, items in menu_data.items():
            if items:
                st.markdown(f"#### {category}")
                for item in items:
                    with st.container(border=True): # മൊബൈൽ ആപ്പിലെ പോലെ ബോക്സ്
                        col1, col2 = st.columns([3, 2]) # വലതുവശത്ത് ഫോട്ടോ, ഇടതുവശത്ത് വിവരങ്ങൾ
                        
                        with col1:
                            st.markdown(f"**{item['name']}**")
                            st.caption(f"₹{item['price']} | ⏱️ {item.get('prep_time', 300)//60} mins")
                            
                            qty_col, add_col = st.columns([1, 1])
                            with qty_col:
                                qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{item['name']}", label_visibility="collapsed")
                            with add_col:
                                if st.button("Add", key=f"add_{item['name']}", type="secondary", use_container_width=True):
                                    st.session_state.cart[item['name']] = {
                                        "name": item['name'], "price": item['price'], 
                                        "qty": qty, "prep_time": item.get('prep_time', 300)
                                    }
                                    st.rerun() # കാർട്ട് അപ്ഡേറ്റ് ആകാൻ അപ്പോൾ തന്നെ റീഫ്രഷ് ചെയ്യുന്നു
                                    
                        with col2:
                            if item.get('image'): st.image(item['image'], use_column_width=True)
                            else: st.write("🍽️") 

        # 4. ബിൽ പേയ്മെന്റ് ബട്ടൺ (ഏറ്റവും താഴെ)
        st.write("")
        st.write("")
        if st.button("💳 ബിൽ പണമടക്കുക (Pay Bill)", use_container_width=True, type="primary"):
            st.session_state.show_bill_page = True
            st.rerun()

# ==========================================
# 2. കിച്ചൺ & ക്യാഷിയർ പാനൽ
# ==========================================
elif mode == "👨‍🍳 കിച്ചൺ & ക്യാഷിയർ":
    st.title("👨‍🍳 കിച്ചൺ ലൈവ് ഡാഷ്ബോർഡ്")
    
    if st.button("🔄 പുതിയ ഓർഡറുകൾ പരിശോധിക്കുക (Refresh)", type="primary"):
        st.rerun()
        
    pending_orders = [o for o in all_orders if o.get('status') == 'Pending']
    
    if not pending_orders:
        st.info("പുതിയ ഓർഡറുകൾ ഒന്നുമില്ല.")
    else:
        for order in pending_orders:
            st.error(f"🚨 ടേബിൾ {order['table']} - പുതിയ ഓർഡർ! (#{order['id']})")
            for item in order.get('items', []):
                st.write(f"- **{item['qty']} x {item['name']}**")
                
            manual_mins = st.number_input("സമയം (മിനിറ്റിൽ):", value=order.get('suggested_time', 300)//60, key=f"time_{order['id']}")
            
            if st.button("✅ Accept Order", key=f"acc_{order['id']}", type="primary"):
                end_time = time.time() + (manual_mins * 60)
                update_order_status(order['id'], 'Accepted', end_time, manual_mins)
                st.toast(f"ഓർഡർ സ്വീകരിച്ചു!")
                time.sleep(1)
                st.rerun()
            st.divider()
            
    st.subheader("💰 ക്യാഷ് സ്റ്റാറ്റസ് (ക്യാഷിയർക്ക് വേണ്ടി)")
    all_unpaid = [o for o in all_orders if o.get('payment') != 'Unpaid']
    if all_unpaid:
        for o in all_unpaid[-5:]: 
            if "PAID" in o.get('payment', ''):
                st.success(f"ടേബിൾ {o['table']}: {o['payment']} (₹{o['total_bill']})")
            else:
                st.warning(f"ടേബിൾ {o['table']}: {o['payment']} (₹{o['total_bill']})")
    else:
        st.write("പുതിയ പേയ്മെന്റുകൾ നടന്നിട്ടില്ല.")

# ==========================================
# 3. അഡ്മിൻ പാനൽ
# ==========================================
elif mode == "⚙️ അഡ്മിൻ പാനൽ":
    st.title("⚙️ ഹോട്ടൽ അഡ്മിൻ ഡാഷ്ബോർഡ്")
    
    with st.expander("➕ പുതിയ വിഭവം ചേർക്കുക"):
        cat_input = st.selectbox("വിഭാഗം", ["പ്രധാന വിഭവങ്ങൾ", "പാനീയങ്ങൾ", "മധുരപലഹാരങ്ങൾ"])
        item_name = st.text_input("പേര്")
        item_price = st.number_input("വില (₹)", min_value=1)
        item_time_mins = st.number_input("സമയം (മിനിറ്റിൽ)", min_value=1, value=15)
        item_image = st.text_input("ഫോട്ടോ ലിങ്ക് (URL)")
        
        if st.button("ചേർക്കുക"):
            if item_name:
                if cat_input not in menu_data: menu_data[cat_input] = []
                menu_data[cat_input].append({"name": item_name, "price": item_price, "prep_time": item_time_mins * 60, "image": item_image})
                save_menu(menu_data)
                st.success("ചേർത്തു!")
                st.rerun()
                
    st.divider()
    st.subheader("🖨️ ടേബിൾ QR കോഡ് നിർമ്മിക്കുക")
    t_no = st.number_input("ഏത് ടേബിളിലേക്കാണ് QR വേണ്ടത്?", min_value=1, value=1)
    if st.button("Generate QR Code", type="primary"):
        app_url = f"https://keralacafe-menu-app.streamlit.app/?role=customer&table={t_no}"
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(app_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        st.image(byte_im, width=300)
        st.download_button("📥 ഡൗൺലോഡ് ചെയ്യുക", byte_im, file_name=f"Table_{t_no}_QR.png", mime="image/png")

    st.divider()
    st.subheader("🗑️ നിലവിലെ മെനു")
    for category, items in menu_data.items():
        if items:
            st.write(f"**{category}**")
            for item in items:
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"{item['name']}")
                col2.write(f"₹{item['price']}")
                if col3.button("Remove", key=f"del_{item['name']}"):
                    menu_data[category].remove(item)
                    save_menu(menu_data)
                    st.rerun()