import streamlit as st
import json
import os
import qrcode
from io import BytesIO
import time

st.set_page_config(page_title="Smart QR Menu", page_icon="🍔", layout="wide")

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

# --- സ്റ്റേറ്റ് വേരിയബിളുകൾ ---
if 'cart' not in st.session_state: st.session_state.cart = {} 
if 'orders' not in st.session_state: st.session_state.orders = [] 
if 'show_bill_page' not in st.session_state: st.session_state.show_bill_page = False
if 'my_table' not in st.session_state: st.session_state.my_table = 1 # ടേബിൾ നമ്പർ ഓർമ്മിക്കാൻ

st.sidebar.title("നിയന്ത്രണ പാനൽ")
mode = st.sidebar.radio("സ്ക്രീൻ തിരഞ്ഞെടുക്കുക:", [
    "📱 കസ്റ്റമർ മെനു", 
    "👨‍🍳 കിച്ചൺ & ക്യാഷിയർ", 
    "⚙️ അഡ്മിൻ പാനൽ"
])

# ==========================================
# 1. കസ്റ്റമർ മെനു (CUSTOMER VIEW)
# ==========================================
if mode == "📱 കസ്റ്റമർ മെനു":
    
    # ---------------- ബില്ലിംഗ് & പേയ്മെന്റ് സ്ക്രീൻ ----------------
    if st.session_state.show_bill_page:
        st.title("💳 ബിൽ പേയ്മെന്റ്")
        
        my_table = st.number_input("നിങ്ങളുടെ ടേബിൾ നമ്പർ ഉറപ്പുവരുത്തുക:", min_value=1, value=st.session_state.my_table)
        
        # ഈ ടേബിളിലെ പണമടക്കാത്ത (Unpaid) മുഴുവൻ ഓർഡറുകളും കണ്ടുപിടിക്കുന്നു
        my_unpaid_orders = [o for o in st.session_state.orders if o['table'] == my_table and o['payment'] == 'Unpaid']
        
        if not my_unpaid_orders:
            st.info("ഈ ടേബിളിൽ നിലവിൽ അടക്കാൻ ബാക്കിയുള്ള ബില്ലുകൾ ഒന്നുമില്ല.")
            if st.button("← മെനുവിലേക്ക് മടങ്ങുക"):
                st.session_state.show_bill_page = False
                st.rerun()
        else:
            st.write("### 🧾 കഴിച്ച വിഭവങ്ങൾ (Total Items):")
            total_bill = 0
            
            for o in my_unpaid_orders:
                for item in o['items']:
                    item_total = item['price'] * item['qty']
                    total_bill += item_total
                    st.write(f"🔹 {item['qty']} x {item['name']} (₹{item_total})")
                    
            st.markdown(f"## 💰 ആകെ അടക്കേണ്ട തുക: ₹{total_bill}")
            st.divider()
            
            st.subheader("പേയ്മെന്റ് രീതി തിരഞ്ഞെടുക്കുക:")
            pay_method = st.radio("", ["📱 UPI (GPay, PhonePe, Paytm)", "💵 Pay at Counter (ക്യാഷ് കൗണ്ടറിൽ നൽകാം)"])
            
            if pay_method == "📱 UPI (GPay, PhonePe, Paytm)":
                st.info("താഴെ കാണുന്ന QR സ്കാൻ ചെയ്ത് പണമടക്കുക (ഡെമോ)")
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
                # പണമടച്ച ശേഷം ഈ ടേബിളിലെ എല്ലാ ഓർഡറുകളും 'PAID' ആക്കുന്നു
                payment_status = "Cash Pending" if "Counter" in pay_method else "PAID via UPI"
                for o in st.session_state.orders:
                    if o['table'] == my_table and o['payment'] == 'Unpaid':
                        o['payment'] = payment_status
                        
                st.success("✅ പേയ്മെന്റ് വിജയകരം! ഞങ്ങളുടെ ഹോട്ടൽ സന്ദർശിച്ചതിന് നന്ദി.")
                time.sleep(2)
                st.session_state.show_bill_page = False
                st.rerun()
                
            if st.button("← കൂടുതൽ ഓർഡർ ചെയ്യാൻ മടങ്ങുക"):
                st.session_state.show_bill_page = False
                st.rerun()

    # ---------------- സാധാരണ മെനു സ്ക്രീൻ (ഓർഡർ ചെയ്യാൻ) ----------------
    else:
        st.title("🍽️ Kerala Cafe - Smart Menu")
        
        # ടേബിൾ നമ്പർ സൈഡ്ബാറിൽ ആദ്യം ചോദിക്കുന്നു
        st.session_state.my_table = st.sidebar.number_input("ടേബിൾ നമ്പർ (Table No):", min_value=1, value=st.session_state.my_table)
        
        # ലൈവ് ഓർഡർ സ്റ്റാറ്റസ് (ഈ ടേബിളിന്റെ മാത്രം)
        my_orders = [o for o in st.session_state.orders if o['table'] == st.session_state.my_table and o['payment'] == 'Unpaid']
        if my_orders:
            with st.expander("🔔 നിങ്ങളുടെ മുൻപത്തെ ഓർഡറുകൾ (Live Status)", expanded=True):
                for order in my_orders:
                    if order['status'] == 'Pending':
                        st.warning(f"ഓർഡർ #{order['id']} - ⏳ കിച്ചൺ സ്വീകരിക്കാൻ കാത്തിരിക്കുന്നു...")
                    elif order['status'] == 'Accepted':
                        rem_time = int(order['end_time'] - time.time())
                        if rem_time > 0:
                            mins, secs = divmod(rem_time, 60)
                            st.info(f"ഓർഡർ #{order['id']} - 👨‍🍳 തയ്യാറാകുന്നു! ({mins:02d}:{secs:02d} ബാക്കി)")
                        else:
                            st.success(f"ഓർഡർ #{order['id']} - ✅ ഭക്ഷണം സർവ് ചെയ്തു!")
                if st.button("🔄 സ്റ്റാറ്റസ് റീഫ്രഷ് ചെയ്യുക"):
                    st.rerun()
            st.divider()

        for category, items in menu_data.items():
            if items:
                st.subheader(f"🍲 {category}")
                for item in items:
                    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                    with col1:
                        if item.get('image'): st.image(item['image'], width=80)
                        else: st.write("🍽️") 
                    with col2:
                        st.write(f"**{item['name']}**")
                        st.caption(f"₹{item['price']} | ⏱️ {item.get('prep_time', 300)//60} mins")
                    with col3:
                        qty = st.number_input("എണ്ണം", min_value=1, value=1, key=f"qty_{item['name']}")
                    with col4:
                        if st.button("Add", key=f"add_{item['name']}"):
                            st.session_state.cart[item['name']] = {
                                "name": item['name'], "price": item['price'], 
                                "qty": qty, "prep_time": item.get('prep_time', 300)
                            }
                            st.toast(f"{qty} {item['name']} കാർട്ടിൽ ചേർത്തു!")
                st.divider()

        if st.session_state.cart:
            st.sidebar.markdown("---")
            st.sidebar.subheader("🛒 പുതിയ ഓർഡർ (Cart)")
            total = sum(d['price'] * d['qty'] for d in st.session_state.cart.values())
            for item_name, data in st.session_state.cart.items():
                st.sidebar.write(f"- {data['qty']} x {data['name']}")
            
            # ഓർഡർ കിച്ചണിലേക്ക് വിടാനുള്ള ബട്ടൺ (ഇവിടെ പണം ചോദിക്കില്ല)
            if st.sidebar.button("👨‍🍳 Send Order to Kitchen", type="primary", use_container_width=True):
                max_time = max([i['prep_time'] for i in st.session_state.cart.values()])
                new_order = {
                    "id": int(time.time()) % 10000, 
                    "table": st.session_state.my_table,
                    "status": "Pending",
                    "items": list(st.session_state.cart.values()),
                    "suggested_time": max_time,
                    "end_time": 0,
                    "total_bill": total,
                    "payment": "Unpaid" # തുടക്കത്തിൽ പണം അടച്ചിട്ടില്ല
                }
                st.session_state.orders.append(new_order)
                st.session_state.cart = {} 
                st.success("✅ ഓർഡർ കിച്ചണിലേക്ക് അയച്ചു!")
                st.rerun()
                
        # ഭക്ഷണം കഴിച്ച് കഴിഞ്ഞതിന് ശേഷം ബില്ല് അടക്കാൻ പോകാനുള്ള ബട്ടൺ
        st.sidebar.markdown("---")
        if st.sidebar.button("💳 ബിൽ കാണുക & പണമടക്കുക (Pay Bill)", use_container_width=True):
            st.session_state.show_bill_page = True
            st.rerun()

# ==========================================
# 2. കിച്ചൺ & ക്യാഷിയർ പാനൽ
# ==========================================
elif mode == "👨‍🍳 കിച്ചൺ & ക്യാഷിയർ":
    st.title("👨‍🍳 കിച്ചൺ ലൈവ് ഡാഷ്ബോർഡ്")
    
    pending_orders = [o for o in st.session_state.orders if o['status'] == 'Pending']
    
    if not pending_orders:
        st.info("പുതിയ ഓർഡറുകൾ ഒന്നുമില്ല.")
    else:
        for order in pending_orders:
            st.error(f"🚨 ടേബിൾ {order['table']} - പുതിയ ഓർഡർ! (#{order['id']})")
            for item in order['items']:
                st.write(f"- **{item['qty']} x {item['name']}**")
                
            manual_mins = st.number_input("സമയം മാറ്റുക (മിനിറ്റിൽ):", value=order['suggested_time']//60, key=f"time_{order['id']}")
            
            if st.button("✅ Accept Order", key=f"acc_{order['id']}", type="primary"):
                order['status'] = 'Accepted'
                order['end_time'] = time.time() + manual_mins 
                st.rerun()
            st.divider()
            
    # ക്യാഷിയർക്ക് കാണാനുള്ള ബില്ലിംഗ് സ്റ്റാറ്റസ്
    st.subheader("💰 ക്യാഷ് സ്റ്റാറ്റസ് (ക്യാഷിയർക്ക് വേണ്ടി)")
    all_unpaid = [o for o in st.session_state.orders if o['payment'] != 'Unpaid']
    if all_unpaid:
        for o in all_unpaid[-5:]: # അവസാനത്തെ 5 പേയ്മെന്റുകൾ കാണിക്കുന്നു
            if "PAID" in o['payment']:
                st.success(f"ടേബിൾ {o['table']}: {o['payment']} (₹{o['total_bill']})")
            else:
                st.warning(f"ടേബിൾ {o['table']}: {o['payment']} (₹{o['total_bill']})")
    else:
        st.write("പുതിയ പേയ്മെന്റുകൾ നടന്നിട്ടില്ല.")

# ==========================================
# 3. അഡ്മിൻ പാനൽ (ADMIN PANEL)
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