import streamlit as st
import requests

import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="BrainMRI Learn", page_icon="🧠", layout="wide")

# Store login information during the session
if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

def api_request(method, endpoint, data=None):
    headers = {}

    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        response = requests.request(
            method, f"{API_URL}{endpoint}", json=data, headers=headers, timeout=30
        )

        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            st.error("Session expired. Please log in again.")
            return None

        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text

            st.error(f"API error: {detail}")
            return None

        return response.json()

    except requests.exceptions.RequestException:
        st.error(
            "Cannot connect to FastAPI. "
            "Make sure the backend is running on port 8000."
        )
        return None


# HEADER
st.title("🧠 BrainMRI Learn")
st.caption("Personalized Learning Resource Recommendation Platform")

# LOGIN AND REGISTRATION
if not st.session_state.token:

    st.subheader("Welcome!")

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
            result = api_request(
                "POST", "/login", {"email": email, "password": password}
            )

            if result:
                st.session_state.token = result["access_token"]
                st.session_state.user = api_request("GET", "/users/me")
                if st.session_state.user:
                    st.rerun()

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full name")
            new_email = st.text_input("Email address")
            new_password = st.text_input("Create password", type="password")
            register_button = st.form_submit_button("Create account")

        if register_button:
            result = api_request(
                "POST",
                "/register",
                {"name": name, "email": new_email, "password": new_password},
            )

            if result:
                st.success("Registration successful! Please log in.")

    st.stop()


# LOGGED-IN INTERFACE
user = st.session_state.user

with st.sidebar:
    st.header("My Account")

    if user:
        st.write(f"**{user['name']}**")
        st.caption(user["email"])

    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

tab1, tab2, tab3 = st.tabs(["Materials Catalog", "My Recommendations", "My History"])


# MATERIALS CATALOG
with tab1:
    st.header("Learning Materials")

    materials = api_request("GET", "/materials")

    if materials is not None:
        categories = sorted(set(m.get("category", "") for m in materials))

        selected_category = st.selectbox("Filter by category", ["All"] + categories)

        search = st.text_input("Search by material title")

        filtered = materials

        if selected_category != "All":
            filtered = [m for m in filtered if m.get("category") == selected_category]

        if search:
            filtered = [
                m for m in filtered if search.lower() in m.get("title", "").lower()
            ]

        st.write(f"Found {len(filtered)} materials")

        for material in filtered:
            material_id = material["_id"]

            with st.expander(material["title"]):
                st.write(material.get("description", ""))
                st.caption(
                    f"Category: {material.get('category', '')}"
                    f" | Difficulty: "
                    f"{material.get('difficulty', '')}"
                )

                rating = st.select_slider(
                    "Your rating",
                    options=[1, 2, 3, 4, 5],
                    value=5,
                    key=f"rating_{material_id}",
                )

                if st.button("Submit Rating", key=f"rate_{material_id}"):
                    result = api_request(
                        "POST",
                        "/interactions",
                        {
                            "material_id": material_id,
                            "type": "rating",
                            "rating": rating,
                        },
                    )
                    if result:
                        st.success("Rating saved!")

                if st.button("Mark as Viewed", key=f"view_{material_id}"):
                    result = api_request(
                        "POST",
                        "/interactions",
                        {"material_id": material_id, "type": "view", "rating": None},
                    )
                    if result:
                        st.success("View recorded!")


# PERSONALIZED RECOMMENDATIONS
with tab2:
    st.header("Recommended for You")

    st.write(
        "Recommendations are generated using " "item-based collaborative filtering."
    )

    limit = st.slider("Number of recommendations", min_value=1, max_value=10, value=5)

    if st.button("Generate Recommendations"):
        result = api_request("GET", f"/recommendations/me?limit={limit}")

        if result is not None:
            recommendations = result.get("recommendations", [])

            if not recommendations:
                st.info("No recommendations available yet.")

            for i, material in enumerate(recommendations, start=1):
                st.subheader(f"{i}. {material['title']}")

                st.write(material.get("description", ""))

                st.caption(
                    f"Category: {material.get('category', '')}"
                    f" | Difficulty: "
                    f"{material.get('difficulty', '')}"
                )

                st.write("Predicted score:", material["predicted_score"])

                st.caption(f"Method: {material['method']}")

                st.divider()

# USER HISTORY
with tab3:
    st.header("My Learning History")

    if st.button("Load History"):
        history = api_request("GET", "/users/me/history")

        if history is not None:
            if not history:
                st.info("No interactions recorded yet.")
            else:
                for interaction in history:
                    st.write(f"**{interaction['material_title']}**")
                    st.write(f"Type: {interaction['type']}")

                    if interaction.get("rating") is not None:
                        st.write(f"Rating: {interaction['rating']}/5")

                    st.caption(str(interaction["timestamp"]))
                    st.divider()
