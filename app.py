from datetime import datetime
import requests
import streamlit as st

BACKEND_URL = "https://sam-suppliers-backend-2.onrender.com"

st.set_page_config(page_title="SAM SUPPLIERS POS", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "worker_name" not in st.session_state:
    st.session_state.worker_name = ""
if "role" not in st.session_state:
    st.session_state.role = "Staff"

# --- TELEPHONE & PASSWORD LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.title("🔐 SAM SUPPLIERS - Worker Login")
    st.markdown(
        "Please enter your registered telephone number and password to access the system."
    )

    with st.form("login_form"):
        phone_input = st.text_input("Telephone Number (e.g. 0700000000)")
        password_input = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Login to POS")

        if submit_login:
            if phone_input and password_input:
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/workers/login",
                        json={"phone": phone_input, "password": password_input},
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.logged_in = True
                        st.session_state.worker_name = data["name"]
                        st.session_state.role = data["role"]
                        st.success(f"Welcome back, {data['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid telephone number or password.")
                except Exception as e:
                    st.error(f"Could not connect to server: {e}")
            else:
                st.warning("Please fill in both fields.")

    st.stop()  # Stops execution until logged in

# --- LOGGED-IN SIDEBAR & APP NAVIGATION ---
st.sidebar.title("👤 User Profile")
st.sidebar.write(f"**Name:** {st.session_state.worker_name}")
st.sidebar.write(f"**Role:** {st.session_state.role}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.worker_name = ""
    st.session_state.role = "Staff"
    st.rerun()

# Admin Worker Registration Section
if st.session_state.role == "Admin":
    with st.sidebar.expander("🛠️ Register New Worker"):
        with st.form("new_worker_form"):
            w_name = st.text_input("Worker Name")
            w_phone = st.text_input("Phone Number")
            w_pass = st.text_input("Password", type="password")
            w_role = st.selectbox("Role", ["Staff", "Admin"])
            if st.form_submit_button("Add Worker"):
                if w_name and w_phone and w_pass:
                    w_res = requests.post(
                        f"{BACKEND_URL}/workers",
                        json={
                            "name": w_name,
                            "phone": w_phone,
                            "password": w_pass,
                            "role": w_role,
                        },
                    )
                    if w_res.status_code == 200:
                        st.success("Worker registered successfully!")
                    else:
                        st.error(
                            w_res.json().get("detail", "Error adding worker")
                        )
                else:
                    st.warning("Please complete all fields.")

    with st.sidebar.expander("🛠️ Manage Workers"):
        st.subheader("Registered Workers")
        try:
            res = requests.get(f"{BACKEND_URL}/workers")
            if res.status_code == 200:
                for w in res.json():
                    st.write(f"**{w['worker_name']}** (`{w['phone']}`)")
                    reason_w = st.text_input(
                        "Reason for deletion", key=f"reason_w_{w['phone']}"
                    )
                    if st.button("Delete Worker", key=f"del_w_{w['phone']}"):
                        if not reason_w:
                            st.warning("Please provide a reason.")
                        else:
                            del_res = requests.delete(
                                f"{BACKEND_URL}/workers/{w['phone']}",
                                params={"reason": reason_w},
                            )
                            if del_res.status_code == 200:
                                st.success("Worker deleted.")
                                st.rerun()
                            else:
                                st.error("Failed to delete worker.")
        except Exception:
            st.error("Could not load workers.")

st.title("SAM SUPPLIERS")
st.markdown("Sweets • Chocolates • And More — Reliable Supply, Unbeatable Quality")

tabs = st.tabs(
    [
        "Point of Sale",
        "Business Dashboard",
        "Inventory / Products",
        "Customer Management",
        "Credit Management",
        "Deletion Audit Trail",
    ]
)

# --- TAB 1: POINT OF SALE ---
with tabs[0]:
    st.subheader("Process a Sale & Multi-Item Cart")
    try:
        prod_res = requests.get(f"{BACKEND_URL}/products")
        cust_res = requests.get(f"{BACKEND_URL}/customers")

        if prod_res.status_code == 200 and cust_res.status_code == 200:
            products = prod_res.json()
            customers = cust_res.json()

            if not products:
                st.warning("No products available. Please add products first!")
            else:
                prod_dict = {p["name"]: p for p in products}

                if "cart" not in st.session_state:
                    st.session_state.cart = []

                with st.form("add_to_cart_form"):
                    selected_prod_name = st.selectbox(
                        "Select Product", list(prod_dict.keys()), key="pos_prod"
                    )
                    selected_prod = prod_dict[selected_prod_name]

                    if selected_prod.get("is_low_stock"):
                        st.warning(
                            f"⚠️ Low Stock Warning: Only {selected_prod.get('stock_display')} remaining!"
                        )
                    else:
                        st.info(
                            f"Available Stock: {selected_prod.get('stock_display', 'N/A')}"
                        )

                    unit_type = st.selectbox("Unit Type", ["piece", "box"], key="pos_unit")
                    price_type = st.selectbox(
                        "Price Type", ["retail", "wholesale"], key="pos_price"
                    )
                    quantity = st.number_input(
                        "Quantity", min_value=1, value=1, step=1, key="pos_qty"
                    )

                    add_to_cart_btn = st.form_submit_button("Add Item to Client Order")
                    if add_to_cart_btn:
                        st.session_state.cart.append(
                            {
                                "product_id": selected_prod["id"],
                                "product_name": selected_prod["name"],
                                "unit_type": unit_type,
                                "quantity": quantity,
                                "price_type": price_type,
                            }
                        )
                        st.success(
                            f"Added {quantity} {unit_type}(s) of {selected_prod['name']} to order!"
                        )

                if st.session_state.cart:
                    st.markdown("### Current Client Order / Cart")
                    subtotal = 0.0
                    for idx, item in enumerate(st.session_state.cart):
                        p_item = prod_dict.get(item["product_name"])
                        if p_item:
                            if item["unit_type"] == "box":
                                u_price = (
                                    p_item["box_pricing"]["wholesale_price_per_box"]
                                    if item["price_type"] == "wholesale"
                                    else p_item["box_pricing"]["retail_price_per_box"]
                                )
                            else:
                                u_price = (
                                    p_item["wholesale_price_per_base"]
                                    if item["price_type"] == "wholesale"
                                    else p_item["retail_price_per_base"]
                                )
                            line_total = u_price * item["quantity"]
                            subtotal += line_total

                            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                            c1.write(
                                f"**{item['product_name']}** ({item['price_type']})"
                            )
                            c2.write(f"{item['quantity']} {item['unit_type']}(s)")
                            c3.write(f"UGX {line_total:,.0f}")
                            if c4.button("❌", key=f"remove_cart_{idx}"):
                                st.session_state.cart.pop(idx)
                                st.rerun()

                    st.markdown(f"**Cart Subtotal:** UGX {subtotal:,.0f}")

                    discount = st.number_input(
                        "Discount Amount (UGX)", min_value=0.0, value=0.0, step=500.0
                    )
                    grand_total = max(0.0, subtotal - discount)
                    st.markdown(
                        f"**Final Total after Discount:** UGX {grand_total:,.0f}"
                    )

                    payment_status = st.selectbox(
                        "Payment Method", ["Cash", "Credit", "Partial"], key="pos_pay_status"
                    )
                    if payment_status == "Cash":
                        amount_paid = float(grand_total)
                    elif payment_status == "Credit":
                        amount_paid = 0.0
                    else:
                        amount_paid = st.number_input(
                            "Amount Paid Now (UGX)",
                            min_value=0.0,
                            max_value=float(grand_total),
                            value=0.0,
                            step=500.0,
                        )

                    balance_due = grand_total - amount_paid
                    if balance_due > 0:
                        st.warning(f"Balance Left as Credit: UGX {balance_due:,.0f}")

                    delivery_option = st.selectbox(
                        "Delivery Option",
                        [
                            "Pick up",
                            "Customer delivery personnel",
                            "Own delivery",
                        ],
                        key="pos_delivery",
                    )

                    cust_dict = {c["name"]: c["id"] for c in customers}
                    cust_names = ["Walk-in Customer"] + list(cust_dict.keys())
                    selected_cust_name = st.selectbox(
                        "Customer for Order", cust_names, key="pos_cust"
                    )
                    customer_id = (
                        None
                        if selected_cust_name == "Walk-in Customer"
                        else cust_dict[selected_cust_name]
                    )

                    if st.button("Complete Checkout & Generate Receipt", type="primary"):
                        payload = {
                            "customer_id": customer_id,
                            "items": [
                                {
                                    "product_id": i["product_id"],
                                    "unit_type": i["unit_type"],
                                    "quantity": i["quantity"],
                                    "price_type": i["price_type"],
                                }
                                for i in st.session_state.cart
                            ],
                            "discount": discount,
                            "amount_paid": amount_paid,
                            "payment_status": payment_status,
                            "delivery_option": delivery_option,
                        }
                        res = requests.post(f"{BACKEND_URL}/checkout", json=payload)
                        if res.status_code == 200:
                            st.success("Sale completed successfully!")

                            receipt_text = f"""========================================
               SAM SUPPLIERS
     Sweets • Chocolates • And More
========================================
Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Cashier/Worker: {st.session_state.worker_name}
Customer: {selected_cust_name}
Delivery: {delivery_option}
----------------------------------------
"""
                            for item in st.session_state.cart:
                                receipt_text += f"- {item['product_name']} x {item['quantity']} {item['unit_type']}(s) [{item['price_type']}]\n"

                            receipt_text += f"""----------------------------------------
Subtotal: UGX {subtotal:,.0f}
Discount: UGX {discount:,.0f}
Grand Total: UGX {grand_total:,.0f}
Amount Paid: UGX {amount_paid:,.0f}
Payment Status: {payment_status}
Balance Due: UGX {balance_due:,.0f}
========================================
     Thank you for your business!
========================================
"""
                            st.download_button(
                                label="📥 Download Receipt File",
                                data=receipt_text,
                                file_name=f"Receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                mime="text/plain",
                            )
                            st.session_state.cart = []
                        else:
                            st.error(
                                res.json().get(
                                    "detail", "Error processing checkout"
                                )
                            )
                else:
                    st.info(
                        "Your cart is currently empty. Add products above to build a multi-item order."
                    )
        else:
            st.error("Cannot connect to backend or load data.")
    except Exception as e:
        st.error(f"Connection error: {e}")

# --- TAB 2: BUSINESS DASHBOARD ---
with tabs[1]:
    st.subheader("Business Dashboard & Reports")
    try:
        dash_res = requests.get(f"{BACKEND_URL}/dashboard")
        sales_res = requests.get(f"{BACKEND_URL}/sales")

        if dash_res.status_code == 200:
            data = dash_res.json()
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Sales Revenue", f"UGX {data['todays_sales']:,.0f}")
            col2.metric(
                "Total Credit Owed", f"UGX {data['credit_owed_by_customers']:,.0f}"
            )
            col3.metric("Total Expenses", f"UGX {data['total_expenses']:,.0f}")

        st.markdown("---")
        st.subheader("Sales History & Date Filters")

        if sales_res.status_code == 200:
            sales_list = sales_res.json()
            if sales_list:
                search_date = st.text_input(
                    "Filter by Date (YYYY-MM-DD or leave blank)", ""
                )
                filtered_sales = [
                    s
                    for s in sales_list
                    if not search_date or search_date in s.get("sale_date", "")
                ]

                st.write(f"Showing {len(filtered_sales)} transaction record(s):")
                for s in filtered_sales:
                    with st.container():
                        c1, c2, c3, c4, c5, c6 = st.columns(
                            [2, 2, 2, 2, 2, 1]
                        )
                        c1.write(
                            f"**{s.get('product_name')}**\n\n`{s.get('sale_date')}`"
                        )
                        c2.write(
                            f"Qty: {s.get('quantity_sold')} {s.get('unit_sold')}(s)"
                        )
                        c3.write(
                            f"Total: UGX {s.get('total_price'):,.0f}\nDisc: UGX {s.get('discount', 0):,.0f}"
                        )
                        paid = s.get("amount_paid", 0)
                        bal = (
                            s.get("total_price") - s.get("discount", 0)
                        ) - paid
                        c4.write(
                            f"Paid: UGX {paid:,.0f} ({s.get('payment_status')})\nBal: UGX {bal:,.0f}"
                        )
                        c5.write(
                            f"Cust: **{s.get('customer_name')}**\nAddr: *{s.get('customer_address')}*\nDel: {s.get('delivery_option')}"
                        )

                        if st.session_state.role == "Admin":
                            if c6.button("Delete", key=f"del_sale_{s['id']}"):
                                del_res = requests.delete(
                                    f"{BACKEND_URL}/sales/{s['id']}?role=Admin"
                                )
                                if del_res.status_code == 200:
                                    st.success("Deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete")
                        else:
                            c6.caption("🔒 Admin Only")
                        st.divider()
            else:
                st.info("No sales recorded yet.")
    except Exception as e:
        st.error(f"Could not load dashboard: {e}")

# --- TAB 3: INVENTORY / PRODUCTS ---
with tabs[2]:
    st.subheader("Inventory Management & Restocking")

    with st.expander("➕ Add New Product"):
        with st.form("add_product_form"):
            prod_name = st.text_input("Product Name")
            c1, c2 = st.columns(2)
            pieces_per_box = c1.number_input(
                "Pieces per Box", min_value=1, value=24, step=1
            )
            boxes_in_stock = c2.number_input(
                "Boxes in Stock", min_value=0, value=10, step=1
            )

            st.markdown("**Box Prices**")
            c3, c4 = st.columns(2)
            wholesale_price_per_box = c3.number_input(
                "Wholesale Price per Box", min_value=0.0, value=3600.0, step=100.0
            )
            retail_price_per_box = c4.number_input(
                "Retail Price per Box", min_value=0.0, value=4800.0, step=100.0
            )

            st.markdown("**Custom Piece Prices**")
            c5, c6 = st.columns(2)
            wholesale_price_per_base = c5.number_input(
                "Wholesale Price per Piece", min_value=0.0, value=150.0, step=10.0
            )
            retail_price_per_base = c6.number_input(
                "Retail Price per Piece", min_value=0.0, value=200.0, step=10.0
            )

            submit_prod = st.form_submit_button("Save Product")
            if submit_prod:
                if prod_name:
                    payload = {
                        "name": prod_name,
                        "base_unit_name": "piece",
                        "pieces_per_box": pieces_per_box,
                        "wholesale_price_per_box": wholesale_price_per_box,
                        "retail_price_per_box": retail_price_per_box,
                        "wholesale_price_per_base": wholesale_price_per_base,
                        "retail_price_per_base": retail_price_per_base,
                        "boxes_in_stock": boxes_in_stock,
                        "pieces_in_stock": 0,
                    }
                    res = requests.post(f"{BACKEND_URL}/products", json=payload)
                    if res.status_code == 200:
                        st.success(f"Product '{prod_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add product.")
                else:
                    st.warning("Please enter a product name.")

    st.markdown("### Existing Inventory & Restocking")
    try:
        r = requests.get(f"{BACKEND_URL}/products")
        if r.status_code == 200:
            products = r.json()
            for p in products:
                with st.container():
                    col_a, col_b = st.columns([3, 2])
                    with col_a:
                        if p.get("is_low_stock"):
                            st.markdown(
                                f"🔴 **{p['name']}** — Stock: **{p.get('stock_display')}** *(LOW STOCK)*"
                            )
                        else:
                            st.markdown(
                                f"🟢 **{p['name']}** — Stock: {p.get('stock_display')}"
                            )
                        st.text(
                            f"Box Price -> Retail: UGX {p['retail_price_per_box']:,.0f} | Wholesale: UGX {p['wholesale_price_per_box']:,.0f}"
                        )
                        st.text(
                            f"Piece Price -> Retail: UGX {p['retail_price_per_base']:,.0f} | Wholesale: UGX {p['wholesale_price_per_base']:,.0f}"
                        )

                        if st.session_state.role == "Admin":
                            reason_prod = st.text_input(
                                "Reason for deletion", key=f"reason_prod_{p['id']}"
                            )
                            if st.button("Delete Product", key=f"del_prod_{p['id']}"):
                                if not reason_prod:
                                    st.warning(
                                        "Please enter a reason for deleting this product."
                                    )
                                else:
                                    del_res = requests.delete(
                                        f"{BACKEND_URL}/products/{p['id']}",
                                        params={"reason": reason_prod},
                                    )
                                    if del_res.status_code == 200:
                                        st.success("Product deleted.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete product.")

                    with col_b:
                        with st.form(f"restock_form_{p['id']}"):
                            st.write("Quick Restock")
                            r_boxes = st.number_input(
                                "Add Boxes",
                                min_value=0,
                                value=0,
                                step=1,
                                key=f"rb_{p['id']}",
                            )
                            r_pieces = st.number_input(
                                "Add Pieces",
                                min_value=0,
                                value=0,
                                step=1,
                                key=f"rp_{p['id']}",
                            )
                            if st.form_submit_button("Update Stock"):
                                restock_payload = {
                                    "boxes_to_add": r_boxes,
                                    "pieces_to_add": r_pieces,
                                }
                                res = requests.post(
                                    f"{BACKEND_URL}/products/{p['id']}/restock",
                                    json=restock_payload,
                                )
                                if res.status_code == 200:
                                    st.success("Stock updated!")
                                    st.rerun()
                                else:
                                    st.error("Failed to restock")
                    st.divider()
    except Exception:
        st.info("Could not load product list.")

# --- TAB 4: CUSTOMER MANAGEMENT ---
with tabs[3]:
    st.subheader("Customer Management")
    with st.form("add_cust_form"):
        c_name = st.text_input("Customer Name")
        c_phone = st.text_input("Phone Number")
        c_address = st.text_input("Address / Location", value="Walk-in")
        c_opening_credit = st.number_input(
            "Pre-existing Opening Credit Owed (UGX)",
            min_value=0.0,
            value=0.0,
            step=1000.0,
        )
        sub_cust = st.form_submit_button("Save Customer")
        if sub_cust:
            if c_name:
                res = requests.post(
                    f"{BACKEND_URL}/customers",
                    json={
                        "name": c_name,
                        "phone": c_phone,
                        "address": c_address,
                        "opening_credit": c_opening_credit,
                    },
                )
                if res.status_code == 200:
                    st.success("Customer added successfully!")
                    st.rerun()
                else:
                    st.error("Error adding customer.")
            else:
                st.warning("Customer name is required.")

    st.markdown("### Registered Customers")
    try:
        custs = requests.get(f"{BACKEND_URL}/customers").json()
        for c in custs:
            st.write(
                f"- **{c['name']}** | Phone: {c.get('phone', 'N/A')} | Address: {c.get('address', 'Walk-in')} | Total Credit Owed: **UGX {c.get('total_credit_owed', 0):,.0f}**"
            )
            if st.session_state.role == "Admin":
                reason_cust = st.text_input(
                    "Reason for deletion", key=f"reason_cust_{c['id']}"
                )
                if st.button("Delete Customer", key=f"del_c_{c['id']}"):
                    if not reason_cust:
                        st.warning("Please provide a reason to delete this customer.")
                    else:
                        del_res = requests.delete(
                            f"{BACKEND_URL}/customers/{c['id']}",
                            params={"reason": reason_cust},
                        )
                        if del_res.status_code == 200:
                            st.success("Customer deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete customer.")
            st.divider()
    except Exception:
        st.info("No customers loaded.")

# --- TAB 5: CREDIT MANAGEMENT ---
with tabs[4]:
    st.subheader("Customer Credit Tracking & Clearing")
    try:
        custs = requests.get(f"{BACKEND_URL}/customers").json()
        if custs:
            cust_dict_cr = {c["name"]: c for c in custs}
            selected_cr_name = st.selectbox(
                "Select Customer to Manage Credit",
                list(cust_dict_cr.keys()),
                key="cr_cust_sel",
            )
            selected_customer = cust_dict_cr[selected_cr_name]

            st.metric(
                "Total Outstanding Credit Owed",
                f"UGX {selected_customer.get('total_credit_owed', 0):,.0f}",
            )
            st.write(
                f"**Phone:** {selected_customer.get('phone', 'N/A')} | **Address:** {selected_customer.get('address', 'Walk-in')}"
            )

            with st.form("clear_credit_form"):
                amount_cleared = st.number_input(
                    "Amount Paid / Cleared Now (UGX)",
                    min_value=0.0,
                    value=0.0,
                    step=500.0,
                )
                sub_clear = st.form_submit_button("Record Credit Payment")
                if sub_clear:
                    if amount_cleared > 0:
                        res = requests.post(
                            f"{BACKEND_URL}/customers/{selected_customer['id']}/clear-credit",
                            json={"amount_cleared": amount_cleared},
                        )
                        if res.status_code == 200:
                            st.success("Credit payment cleared successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to record payment.")
                    else:
                        st.warning("Please enter an amount greater than 0.")
        else:
            st.info("No customers found.")
    except Exception as e:
        st.error(f"Could not load credit section: {e}")

# --- TAB 6: DELETION AUDIT TRAIL ---
with tabs[5]:
    st.header("Deletion Logs & Audit Trail")
    st.write("Review all deleted items and their mandatory reasons.")
    try:
        res = requests.get(f"{BACKEND_URL}/deletion-logs")
        if res.status_code == 200:
            logs = res.json()
            if not logs:
                st.info("No deletion records found.")
            else:
                for log in logs:
                    st.markdown(
                        f"- **Type:** {log['item_type']} | **Item:** {log['item_identifier']} | **Reason:** *{log['reason']}* | <small>At: {log['deleted_at']}</small>",
                        unsafe_allow_html=True,
                    )
    except Exception:
        st.error("Could not fetch deletion logs.")
