import streamlit as st
import cv2
import time

from driver_monitor import DriverMonitor


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GuardianDriveAI | Safety Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "monitor" not in st.session_state:
    st.session_state.monitor = None

if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

if "latest_results" not in st.session_state:
    st.session_state.latest_results = {
        "safety_level": 1,
        "safety_message": "NOT STARTED",
        "alerts": [],
        "ear": 0.0,
        "mar": 0.0,
        "emergency": False,
    }

if "last_error" not in st.session_state:
    st.session_state.last_error = None


# --------------------------------------------------
# DASHBOARD STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1120;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #263247;
    }

    .hero {
        padding: 24px;
        border: 1px solid #263247;
        border-radius: 14px;
        background: linear-gradient(120deg, #172554, #111827);
        margin-bottom: 22px;
    }

    .hero h1 {
        color: #f8fafc;
        margin-bottom: 8px;
    }

    .hero p {
        color: #cbd5e1;
        margin-bottom: 0;
    }

    .metric-card {
        background: #111827;
        border: 1px solid #263247;
        border-radius: 12px;
        padding: 18px;
        min-height: 110px;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 14px;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 22px;
        font-weight: 650;
        margin-top: 8px;
    }

    .notice {
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #475569;
        background: #172033;
        color: #e2e8f0;
        margin-top: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def stop_monitoring():
    """Stop the camera and release monitoring resources."""

    monitor = st.session_state.monitor

    st.session_state.monitor = None
    st.session_state.monitoring = False

    if monitor is not None:
        try:
            monitor.close()
        except Exception:
            pass


def metric_card(label, value):
    """Display a dashboard metric card."""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## GuardianDriveAI")
    st.caption("Driver Safety Monitoring")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Overview", "Live Monitoring", "Safety Information"],
    )

    st.divider()

    if st.session_state.monitoring:
        st.success("Monitoring is active")
    else:
        st.caption("Monitoring is stopped")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <h1>Driver Safety Dashboard</h1>
        <p>
            Monitor driver safety signals and review alerts
            from the GuardianDriveAI detection engine.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# OVERVIEW PAGE
# --------------------------------------------------

if page == "Overview":

    st.subheader("System Overview")

    results = st.session_state.latest_results

    session_status = (
        "Running"
        if st.session_state.monitoring
        else "Not started"
    )

    camera_status = (
        "Connected"
        if st.session_state.monitoring
        else "Disconnected"
    )

    safety_status = (
        results["safety_message"]
        if st.session_state.monitoring
        else "Unavailable"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Monitoring Session", session_status)

    with c2:
        metric_card("Camera Feed", camera_status)

    with c3:
        metric_card("Safety Status", safety_status)

    st.divider()

    if st.session_state.monitoring:
        st.success("The driver monitoring session is active.")

        st.write(
            "Open **Live Monitoring** in the sidebar to view "
            "the camera feed and current detection results."
        )
    else:
        st.info(
            "Monitoring is currently stopped. Open Live Monitoring "
            "to start the camera and detection engine."
        )

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    if st.session_state.monitoring:
        st.subheader("Latest Detection Results")

        m1, m2, m3 = st.columns(3)

        with m1:
            metric_card(
                "Safety Level",
                str(results["safety_level"]),
            )

        with m2:
            metric_card("Eye Aspect Ratio", f'{results["ear"]:.3f}')

        with m3:
            metric_card(
                "Mouth Aspect Ratio",
                f'{results["mar"]:.3f}',
            )

        st.write("**Latest alerts**")

        for alert in results["alerts"]:
            if alert == "STATUS: MONITORING":
                st.success(alert)
            else:
                st.warning(alert)


# --------------------------------------------------
# LIVE MONITORING PAGE
# --------------------------------------------------

elif page == "Live Monitoring":

    st.subheader("Live Driver Monitoring")

    st.write(
        "Start the monitoring engine to activate the webcam "
        "and display actual detection results."
    )

    start_col, stop_col = st.columns(2)

    with start_col:
        start_clicked = st.button(
            "Start Monitoring",
            type="primary",
            disabled=st.session_state.monitoring,
            use_container_width=True,
        )

    with stop_col:
        stop_clicked = st.button(
            "Stop Monitoring",
            disabled=not st.session_state.monitoring,
            use_container_width=True,
        )

    if start_clicked:
        try:
            st.session_state.last_error = None
            st.session_state.monitor = DriverMonitor()
            st.session_state.monitoring = True

            st.session_state.latest_results = {
                "safety_level": 1,
                "safety_message": "NORMAL - KEEP MONITORING",
                "alerts": ["STATUS: MONITORING"],
                "ear": 0.0,
                "mar": 0.0,
                "emergency": False,
            }

            st.rerun()

        except Exception as error:
            stop_monitoring()
            st.session_state.last_error = str(error)
            st.error(f"Could not start monitoring: {error}")

    if stop_clicked:
        stop_monitoring()
        st.session_state.last_error = None
        st.rerun()

    if st.session_state.monitoring:

        st.success("Monitoring active")

        # Streamlit refreshes this section repeatedly.
        # Each refresh processes a single webcam frame.

        @st.fragment(run_every=0.1)
        def live_monitoring():

            if not st.session_state.monitoring:
                st.info("Monitoring has stopped.")
                return

            monitor = st.session_state.monitor

            if monitor is None:
                st.warning("The monitoring engine is unavailable.")
                return
            try:
                frame, results = monitor.process_frame()
                st.session_state.latest_results = results

                st.write("DEBUG: Frame received successfully")
                st.write("Frame shape:", frame.shape)

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                st.image(
                    rgb_frame,
                    caption="GuardianDriveAI Live Camera",
                    width=640,
                )

                st.subheader("Current Safety Status")

                level = results["safety_level"]

                if level == 3:
                    st.error(
                        f'LEVEL {level}: {results["safety_message"]}'
                    )
                elif level == 2:
                    st.warning(
                        f'LEVEL {level}: {results["safety_message"]}'
                    )
                else:
                    st.success(
                        f'LEVEL {level}: {results["safety_message"]}'
                    )

                c1, c2 = st.columns(2)

                with c1:
                    st.metric(
                        "Eye Aspect Ratio (EAR)",
                        f'{results["ear"]:.3f}',
                    )

                with c2:
                    st.metric(
                        "Mouth Aspect Ratio (MAR)",
                        f'{results["mar"]:.3f}',
                    )

                st.subheader("Detection Alerts")

                for alert in results["alerts"]:
                    if alert == "STATUS: MONITORING":
                        st.success(alert)
                    else:
                        st.warning(alert)

                if results["emergency"]:
                    st.error(
                        "Emergency warning: persistent eye closure detected."
                    )

        
                st.session_state.latest_results = results

                # Convert OpenCV BGR frame to RGB for Streamlit.
                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                st.image(
                    rgb_frame,
                    caption="GuardianDriveAI Live Camera",
                    use_container_width=True,
                )

                st.subheader("Current Safety Status")

                level = results["safety_level"]

                if level == 3:
                    st.error(
                        f"LEVEL {level}: "
                        f'{results["safety_message"]}'
                    )

                elif level == 2:
                    st.warning(
                        f"LEVEL {level}: "
                        f'{results["safety_message"]}'
                    )

                else:
                    st.success(
                        f"LEVEL {level}: "
                        f'{results["safety_message"]}'
                    )

                c1, c2 = st.columns(2)

                with c1:
                    st.metric(
                        "Eye Aspect Ratio (EAR)",
                        f'{results["ear"]:.3f}',
                    )

                with c2:
                    st.metric(
                        "Mouth Aspect Ratio (MAR)",
                        f'{results["mar"]:.3f}',
                    )

                st.subheader("Detection Alerts")

                for alert in results["alerts"]:
                    if alert == "STATUS: MONITORING":
                        st.success(alert)
                    else:
                        st.warning(alert)

                if results["emergency"]:
                    st.error(
                        "Emergency warning: persistent eye closure detected."
                    )

            except Exception as error:
                stop_monitoring()
                st.session_state.last_error = str(error)

                st.error(f"Monitoring stopped: {error}")
                st.rerun()

        live_monitoring()

    else:
        st.info(
            "Camera is inactive. Press Start Monitoring to begin."
        )

        if st.session_state.last_error:
            st.error(st.session_state.last_error)


# --------------------------------------------------
# SAFETY INFORMATION PAGE
# --------------------------------------------------

elif page == "Safety Information":

    st.subheader("Safety Level Guide")

    st.markdown(
        """
        - **Level 1 — Normal:** No configured warning condition detected.
        - **Level 2 — Caution:** A configured yawning, distraction,
          or hand-near-face warning has been detected.
        - **Level 3 — Critical:** A drowsiness warning has been detected.

        These levels describe the configured detection rules.
        They do not guarantee that a driver is safe.
        """
    )

    st.warning(
        "GuardianDriveAI is an assistance tool. Drivers must remain "
        "attentive and follow road safety requirements."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "GuardianDriveAI | Local prototype | "
    "OpenCV + MediaPipe + Streamlit"
)