console.log("🚀 Script Loaded Successfully");

/* =========================================
   SAFE GET FUNCTION
========================================= */

function safeGet(id) {

    return document.getElementById(id)?.value.trim() || "";
}

/* =========================================
   STATUS MESSAGE
========================================= */

function showStatus(message, success = true) {

    const statusDiv = document.getElementById("result");

    statusDiv.innerHTML = message;

    statusDiv.style.background = success
        ? "rgba(34,197,94,0.18)"
        : "rgba(239,68,68,0.18)";

    statusDiv.style.border = success
        ? "1px solid rgba(34,197,94,0.4)"
        : "1px solid rgba(239,68,68,0.4)";
}

/* =========================================
   DEVICE ID
========================================= */

function getDeviceId() {

    let deviceId = localStorage.getItem("device_id");

    if (!deviceId) {

        deviceId =
            "DEV-"
            + Math.random()
            .toString(36)
            .substring(2)
            + Date.now();

        localStorage.setItem(
            "device_id",
            deviceId
        );
    }

    return deviceId;
}

/* =========================================
   LOAD EMPLOYEE
========================================= */

async function loadEmployee() {

    const empId = safeGet("emp_id");

    if (!empId) {

        showStatus(
            "⚠️ Employee ID required",
            false
        );

        return;
    }

    showStatus("⏳ Loading Employee...");

    try {

        const response = await fetch(
            "/get_employee",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    emp_id: empId
                })
            }
        );

        const data = await response.json();

        if (data.success) {

            document.getElementById("name").value =
                data.name;

            document.getElementById("phone").value =
                data.phone;

            showStatus(
                `✅ Employee Loaded Successfully<br><br>
                 👤 ${data.name}<br>
                 📞 ${data.phone}`
            );

        } else {

            showStatus(
                "❌ Employee not found",
                false
            );
        }

    } catch (err) {

        console.error(err);

        showStatus(
            "❌ Server error",
            false
        );
    }
}

/* =========================================
   MARK ATTENDANCE
========================================= */

function markAttendance(action) {

    const emp_id = safeGet("emp_id");

    const otp = safeGet("otp");

    if (!emp_id) {

        showStatus(
            "⚠️ Employee ID required",
            false
        );

        return;
    }

    if (!otp) {

        showStatus(
            "⚠️ OTP required",
            false
        );

        return;
    }

    if (!navigator.geolocation) {

        showStatus(
            "❌ Geolocation not supported",
            false
        );

        return;
    }

    showStatus(
        "📍 Fetching location..."
    );

    navigator.geolocation.getCurrentPosition(

        async function (position) {

            const lat =
                position.coords.latitude;

            const lon =
                position.coords.longitude;

            const device_id =
                getDeviceId();

            try {

                showStatus(
                    "⏳ Processing Attendance..."
                );

                const response =
                    await fetch(
                        "/attendance",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                emp_id,
                                otp,
                                lat,
                                lon,
                                action,
                                device_id
                            })
                        }
                    );

                const data =
                    await response.json();

                if (data.success) {

                    showStatus(

                        `🎉 ${data.message}<br><br>

                        👤 <b>${data.name}</b><br>

                        📅 ${data.date}<br>

                        ⏰ ${data.time}<br>

                        📌 ${data.status}

                        ${data.working_hours
                            ? `<br>🕒 ${data.working_hours}`
                            : ""}`
                    );

                } else {

                    showStatus(

                        `❌ ${data.message}`,

                        false
                    );
                }

            } catch (err) {

                console.error(err);

                showStatus(
                    "❌ Server error",
                    false
                );
            }
        },

        function (error) {

            showStatus(
                "📍 Location permission required",
                false
            );
        }
    );
}