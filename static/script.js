console.log("Script Loaded Successfully");

// ===============================
// SAFE GET FUNCTION
// ===============================
function safeGet(id) {
    return document.getElementById(id)?.value?.trim() || "";
}

// ===============================
// DEVICE ID
// ===============================
function getDeviceId() {

    let deviceId = localStorage.getItem("device_id");

    // FIRST TIME DEVICE CREATE
    if (!deviceId) {

        deviceId =
            'DEV-' +
            Math.random().toString(36).substring(2, 10) +
            '-' +
            Date.now();

        localStorage.setItem("device_id", deviceId);
    }

    return deviceId;
}

// ===============================
// LOAD EMPLOYEE
// ===============================
async function loadEmployee() {

    const empId = safeGet("emp_id");

    if (!empId) {
        alert("Employee ID required ❌");
        return;
    }

    try {

        const response = await fetch("/get_employee", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                emp_id: empId
            })

        });

        const data = await response.json();

        if (data.success) {

            document.getElementById("name").value = data.name || "";
            document.getElementById("phone").value = data.phone || "";

        } else {

            alert("Employee not found ❌");

            document.getElementById("name").value = "";
            document.getElementById("phone").value = "";
        }

    } catch (err) {

        console.error("LOAD EMPLOYEE ERROR:", err);

        alert("Server error ❌");
    }
}

// ===============================
// MARK ATTENDANCE
// ===============================
function markAttendance(action) {

    const emp_id = safeGet("emp_id");
    const otp = safeGet("otp");

    // VALIDATION
    if (!emp_id) {
        alert("Employee ID required ❌");
        return;
    }

    if (!otp) {
        alert("OTP required ❌");
        return;
    }

    // GEOLOCATION CHECK
    if (!navigator.geolocation) {

        alert("Geolocation not supported ❌");

        return;
    }

    // LOADING STATUS
    const statusDiv = document.getElementById("status");

    statusDiv.innerText = "Checking location...";

    navigator.geolocation.getCurrentPosition(

        async function (position) {

            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            const device_id = getDeviceId();

            try {

                const response = await fetch('/attendance', {

                    method: 'POST',

                    headers: {
                        'Content-Type': 'application/json'
                    },

                    body: JSON.stringify({
                        emp_id,
                        otp,
                        lat,
                        lon,
                        action,
                        device_id
                    })

                });

                const data = await response.json();

                // SUCCESS
                if (data.success) {

                    statusDiv.innerText =
                        `✅ ${data.name}
${data.message}
📅 ${data.date}
⏰ ${data.time}
📌 ${data.status}`;

                } else {

                    statusDiv.innerText = "";

                    alert(data.message || "Attendance failed ❌");
                }

            } catch (err) {

                console.error("ATTENDANCE ERROR:", err);

                statusDiv.innerText = "";

                alert("Server error ❌");
            }

        },

        // LOCATION ERROR
        function (error) {

            console.error("LOCATION ERROR:", error);

            statusDiv.innerText = "";

            alert("Location permission required ❌");
        },

        // LOCATION OPTIONS
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}