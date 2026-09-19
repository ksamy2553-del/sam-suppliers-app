import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
BACKEND_URL = "https://sam-suppliers-app-sqkruhZpqvyb9kmbolnun.streamlit.app"  # Update if your backend URL is different

st.set_page_config(page_title="Sam Suppliers POS", page_icon="🛒", layout="wide")

# --- INITIALIZE SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "worker_name" not in st.session_state:
    st.session_state["worker_name"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""

# --- SIDEBAR: AUTHENTICATION & WORKERS ---
st.sidebar.markdown("### 👤 User Profile")
if not st.session_state["logged_in"]:
    st.sidebar.info("Please log in to use the system.")
    phone = st.sidebar.text_input("Phone Number")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        try:
            res = requests.post(f"{BACKEND_URL}/workers/login", json={"phone": phone, "password": password})
            if res.status_code == 200:
                data = res.json()
                st.session_state["logged_in"] = True
                st.session_state["worker_name"] = data["name"]
                st.session_state["role"] = data["role"]
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.sidebar.error("Invalid phone or password.")
        except Exception:
            st.sidebar.error("Could not connect to backend.")
else:
    st.sidebar.markdown(f"**Name:** {st.session_state['worker_name']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["worker_name"] = ""
        st.session_state["role"] = ""
        st.rerun()

    # Admin actions in sidebar
    if st.session_state["role"] == "Admin":
        st.sidebar.markdown("---")
        with st.sidebar.expander("Register New Worker"):
            new_w_name = st.text_input("Worker Name")
            new_w_phone = st.text_input("Worker Phone")
            new_w_pass = st.text_input("Worker Password", type="password")
            new_w_role = st.selectbox("Role", ["Staff", "Admin"])
            if st.button("Create Worker"):
                payload = {"name": new_w_name, "phone": new_w_phone, "password": new_w_pass, "role": new_w_role}
                r = requests.post(f"{BACKEND_URL}/workers", json=payload)
                if r.status_code == 200:
                    st.success("Worker registered!")
                else:
                    st.error(r.json().get("detail", "Error"))

        with st.sidebar.expander("Manage Workers"):
            st.markdown("### Registered Workers")
            try:
                workers_res = requests.get(f"{BACKEND_URL}/workers")
                if workers_res.status_code == 200:
                    workers_list = workers_res.json()
                    if workers_list:
                        for w in workers_list:
                            st.markdown(f"- **{w['name']}** | {w['phone']} | *{w['role']}*")
                    else:
                        st.info("No registered workers found.")
                else:
                    st.error("Could not load workers.")
            except Exception:
                st.error("Could not load workers.")

# --- MAIN APP ROUTING ---
if not st.session_state["logged_in"]:
    st.title("SAM SUPPLIERS")
    st.subheader("Please log in via the sidebar to access the Point of Sale and management features.")
else:
    st.title("SAM SUPPLIERS")
    st.markdown("Sweets · Chocolates · And More — Reliable Supply, Unbeatable Quality")
    
    tabs = st.tabs(["Point of Sale", "Business Dashboard", "Inventory / Products", "Customer Management", "Credit Management", "Deletion Audit Trail"])
    
    # 1. POINT OF SALE TAB
    with tabs[0]:
        st.subheader("Point of Sale (POS)")
        try:
            products = requests.get(f"{BACKEND_URL}/products").json()
            customers = requests.get(f"{BACKEND_URL}/customers").json()
            
            if not products:
                st.warning("No products available in inventory.")
            else:
                prod_dict = {p["name"]: p for p in products}
                selected_prod_name = st.selectbox("Select Product", list(prod_dict.keys()))
                prod = prod_dict[selected_prod_name]
                
                st.info(f"Available Stock: {prod['stock_display']}")
                
                unit_sold = st.radio("Unit to Sell", ["Boxes", "Pieces"])
                price_type = st.radio("Price Type", ["Retail", "Wholesale"])
                
                qty = st.number_input("Quantity", min_value=1, value=1)
                
                # Price calculation
                if unit_sold == "Boxes":
                    unit_price = prod["retail_price_per_box"] if price_type == "Retail" else prod["wholesale_price_per_box"]
                else:
                    unit_price = prod["retail_price_per_base"] if price_type == "Retail" else prod["wholesale_price_per_base"]
                
                subtotal = unit_price * qty
                discount = st.number_input("Discount (UGX)", min_value=0.0, value=0.0)
                final_total = max(0.0, subtotal - discount)
                
                st.markdown(f"### Total to Pay: UGX {final_total:,.0f}")
                
                amount_paid = st.number_input("Amount Paid (UGX)", min_value=0.0, value=final_total)
                payment_status = st.selectbox("Payment Status", ["Cash", "Credit", "Partial"])
                delivery_option = st.selectbox("Delivery Option", ["Pick up", "Delivery"])
                
                cust_names = {c["name"]: c["id"] for c in customers}
                cust_names["Walk-in Customer"] = None
                selected_cust = st.selectbox("Customer", list(cust_names.keys()))
                
                if st.button("Complete Sale"):
                    sale_data = {
                        "product_id": prod["id"],
                        "unit_sold": unit_sold,
                        "quantity_sold": qty,
                        "price_type": price_type,
                        "total_price": final_total,
                        "discount": discount,
                        "amount_paid": amount_paid,
                        "payment_status": payment_status,
                        "delivery_option": delivery_option,
                        "customer_id": cust_names[selected_cust]
                    }
                    res = requests.post(f"{BACKEND_URL}/sales", json=sale_data)
                    if res.status_code == 200:
                        st.success("Sale completed successfully!")
                    else:
                        st.error("Failed to complete sale.")
        except Exception as e:
            st.error(f"Error loading POS data: {e}")

    # 2. BUSINESS DASHBOARD TAB
    with tabs[1]:
        st.subheader("Business Dashboard & Sales History")
        try:
            sales = requests.get(f"{BACKEND_URL}/sales").json()
            if sales:
                sales_df = pd.DataFrame(sales)
                st.dataframe(sales_df[["id", "sale_date", "product_name", "quantity_sold", "unit_sold", "total_price", "payment_status", "customer_name"]])
                
                st.markdown("---")
                st.subheader("Manage Sales (Admin Deletion)")
                for s in sales:
                    with st.expander(f"Sale #{s['id']} - {s.get('product_name', 'Item')} (UGX {s['total_price']:,.0f})"):
                        st.write(f"Date: {s['sale_date']} | Qty: {s['quantity_sold']} {s['unit_sold']} | Status: {s['payment_status']}")
                        
                        if st.session_state["role"] == "Admin":
                            sale_del_key = f"show_del_sale_{s['id']}"
                            if sale_del_key not in st.session_state:
                                st.session_state[sale_del_key] = False

                            if not st.session_state[sale_del_key]:
                                if st.button("Delete Sale", key=f"init_del_s_{s['id']}"):
                                    st.session_state[sale_del_key] = True
                                    st.rerun()
                            else:
                                reason_sale = st.text_input("Reason for deletion", key=f"reason_sale_{s['id']}")
                                sc1, sc2 = st.columns(2)
                                with sc1:
                                    if st.button("Confirm Deletion", key=f"conf_del_s_{s['id']}"):
                                        if not reason_sale.strip():
                                            st.warning("Please provide a reason.")
                                        else:
                                            res = requests.delete(f"{BACKEND_URL}/sales/{s['id']}", params={"reason": reason_sale})
                                            if res.status_code == 200:
                                                st.success("Sale deleted.")
                                                st.session_state[sale_del_key] = False
                                                st.rerun()
                                            else:
                                                st.error("Failed to delete sale.")
                                with sc2:
                                    if st.button("Cancel", key=f"canc_del_s_{s['id']}"):
                                        st.session_state[sale_del_key] = False
                                        st.rerun()
            else:
                st.info("No sales recorded yet.")
        except Exception:
            st.error("Could not load sales data.")

    # 3. INVENTORY / PRODUCTS TAB
    with tabs[2]:
        st.subheader("Existing Inventory & Restocking")
        
        if st.session_state["role"] == "Admin":
            with st.expander("Add New Product"):
                new_p_name = st.text_input("Product Name")
                p_pieces_box = st.number_input("Pieces per Box", min_value=1, value=48)
                w_box = st.number_input("Wholesale Price per Box", min_value=0.0, value=0.0)
                r_box = st.number_input("Retail Price per Box", min_value=0.0, value=0.0)
                w_base = st.number_input("Wholesale Price per Piece", min_value=0.0, value=0.0)
                r_base = st.number_input("Retail Price per Piece", min_value=0.0, value=0.0)
                b_stock = st.number_input("Initial Boxes in Stock", min_value=0, value=0)
                p_stock = st.number_input("Initial Pieces in Stock", min_value=0, value=0)
                
                if st.button("Save New Product"):
                    p_payload = {
                        "name": new_p_name,
                        "pieces_per_box": p_pieces_box,
                        "wholesale_price_per_box": w_box,
                        "retail_price_per_box": r_box,
                        "wholesale_price_per_base": w_base,
                        "retail_price_per_base": r_base,
                        "boxes_in_stock": b_stock,
                        "pieces_in_stock": p_stock
                    }
                    r = requests.post(f"{BACKEND_URL}/products", json=p_payload)
                    if r.status_code == 200:
                        st.success("Product added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add product.")

        try:
            products = requests.get(f"{BACKEND_URL}/products").json()
            if products:
                for p in products:
                    st.markdown(f"🟢 **{p['name']}** — Stock: {p['stock_display']}")
                    st.markdown(f"Box Price -> Retail: UGX {p['retail_price_per_box']:,.0f} | Wholesale: UGX {p['wholesale_price_per_box']:,.0f}")
                    st.markdown(f"Piece Price -> Retail: UGX {p['retail_price_per_base']:,.0f} | Wholesale: UGX {p['wholesale_price_per_base']:,.0f}")
                    
                    # Toggle-to-delete product with reason prompt
                    if st.session_state["role"] == "Admin":
                        prod_del_key = f"show_del_prod_{p['id']}"
                        if prod_del_key not in st.session_state:
                            st.session_state[prod_del_key] = False

                        if not st.session_state[prod_del_key]:
                            if st.button("Delete Product", key=f"init_del_p_{p['id']}"):
                                st.session_state[prod_del_key] = True
                                st.rerun()
                        else:
                            reason_prod = st.text_input("Reason for deletion", key=f"reason_prod_{p['id']}")
                            col_c1, col_c2 = st.columns(2)
                            with col_c1:
                                if st.button("Confirm Deletion", key=f"conf_del_p_{p['id']}"):
                                    if not reason_prod.strip():
                                        st.warning("Please provide a reason.")
                                    else:
                                        res = requests.delete(f"{BACKEND_URL}/products/{p['id']}", params={"reason": reason_prod})
                                        if res.status_code == 200:
                                            st.success("Product deleted.")
                                            st.session_state[prod_del_key] = False
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete product.")
                            with col_c2:
                                if st.button("Cancel", key=f"canc_del_p_{p['id']}"):
                                    st.session_state[prod_del_key] = False
                                    st.rerun()
                    st.markdown("---")
            else:
                st.info("No products found.")
        except Exception:
            st.error("Could not load products.")

    # 4. CUSTOMER MANAGEMENT TAB
    with tabs[3]:
        st.subheader("Customer Management")
        with st.form("add_customer_form"):
            c_name = st.text_input("Customer Name")
            c_phone = st.text_input("Phone Number")
            c_address = st.text_input("Address / Location")
            c_credit = st.number_input("Opening Credit (UGX)", min_value=0.0, value=0.0)
            submitted = st.form_submit_button("Register Customer")
            if submitted:
                if c_name.strip():
                    res = requests.post(f"{BACKEND_URL}/customers", json={"name": c_name, "phone": c_phone, "address": c_address, "opening_credit": c_credit})
                    if res.status_code == 200:
                        st.success("Customer registered successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to register customer.")
                else:
                    st.warning("Customer name is required.")

        st.markdown("---")
        st.subheader("Registered Customers")
        try:
            customers = requests.get(f"{BACKEND_URL}/customers").json()
            if customers:
                for cust in customers:
                    st.markdown(f"- **{cust['name']}** | Phone: {cust['phone']} | Address: {cust['address']} | Total Credit Owed: UGX {cust['opening_credit']:,.0f}")
                    
                    if st.session_state["role"] == "Admin":
                        del_key = f"show_del_{cust['id']}"
                        if del_key not in st.session_state:
                            st.session_state[del_key] = False

                        if not st.session_state[del_key]:
                            if st.button("Delete Customer", key=f"btn_init_{cust['id']}"):
                                st.session_state[del_key] = True
                                st.rerun()
                        else:
                            reason = st.text_input("Provide reason for deletion:", key=f"reason_{cust['id']}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Confirm Deletion", key=f"btn_conf_{cust['id']}"):
                                    if not reason.strip():
                                        st.warning("Reason is mandatory for deletion.")
                                    else:
                                        del_res = requests.delete(f"{BACKEND_URL}/customers/{cust['id']}", params={"reason": reason})
                                        if del_res.status_code == 200:
                                            st.success("Customer deleted successfully!")
                                            st.session_state[del_key] = False
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete customer.")
                            with col2:
                                if st.button("Cancel", key=f"btn_canc_{cust['id']}"):
                                    st.session_state[del_key] = False
                                    st.rerun()
                    st.markdown("---")
            else:
                st.info("No customers registered yet.")
        except Exception:
            st.info("Could not load customers.")

    # 5. CREDIT MANAGEMENT TAB
    with tabs[4]:
        st.subheader("Credit Management")
        st.info("Manage customer credits, repayments, and outstanding balances here.")

    # 6. DELETION AUDIT TRAIL TAB
    with tabs[5]:
        st.subheader("Deletion Logs & Audit Trail")
        st.markdown("Review all deleted items and their mandatory reasons.")
        try:
            logs = requests.get(f"{BACKEND_URL}/audit-logs").json()
            if logs:
                for log in logs:
                    st.markdown(f"- **Type:** {log['item_type']} | **Item:** {log['item_identifier']} | **Reason:** {log['reason']} | *Deleted at:* {log['deleted_at']}")
            else:
                st.info("No deletion logs recorded yet.")
        except Exception:
            st.info("Could not load audit logs.")
