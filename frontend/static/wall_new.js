const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const imageInput = document.getElementById("wallImage");
const statusElement = document.getElementById("status");

let imageData = null;
let imageName = null;
let workArea = [];
const img = new Image();

imageInput.addEventListener("change", function () {
    const file = imageInput.files[0];
    if (!file) {
        return;
    }

    imageName = file.name;
    const reader = new FileReader();
    reader.onload = function () {
        imageData = reader.result;
        img.src = imageData;
    };
    reader.readAsDataURL(file);
});

img.onload = function () {
    canvas.width = img.width;
    canvas.height = img.height;
    resetWorkArea();
};

canvas.addEventListener("click", function (event) {
    if (!imageData || workArea.length >= 4) {
        return;
    }

    const point = eventPoint(event);
    workArea.push(point);
    redraw();
    statusElement.textContent = `Area corners: ${workArea.length}/4`;
});

function eventPoint(event) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (event.clientX - rect.left) * (canvas.width / rect.width),
        y: (event.clientY - rect.top) * (canvas.height / rect.height)
    };
}

function resetWorkArea() {
    workArea = [];
    redraw();
    statusElement.textContent = imageData
        ? "Area corners: 0/4"
        : "Select photo and mark 4 wall area corners clockwise from top-left.";
}

function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!imageData) {
        return;
    }

    ctx.drawImage(img, 0, 0);
    drawWorkArea();
}

function drawWorkArea() {
    if (workArea.length === 0) {
        return;
    }

    ctx.save();
    ctx.strokeStyle = "#2563eb";
    ctx.fillStyle = "rgba(37, 99, 235, 0.14)";
    ctx.lineWidth = 4;

    ctx.beginPath();
    workArea.forEach((point, index) => {
        if (index === 0) {
            ctx.moveTo(point.x, point.y);
        } else {
            ctx.lineTo(point.x, point.y);
        }
    });
    if (workArea.length === 4) {
        ctx.closePath();
        ctx.fill();
    }
    ctx.stroke();

    workArea.forEach((point, index) => {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 10, 0, Math.PI * 2);
        ctx.fillStyle = "#2563eb";
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 12px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(index + 1), point.x, point.y);
    });
    ctx.restore();
}

function createWall() {
    if (!imageData || !imageName) {
        alert("Select image first");
        return;
    }
    if (workArea.length !== 4) {
        alert("Mark 4 wall area corners");
        return;
    }

    fetch("/api/walls/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            gym_id: Number(document.getElementById("gymId").value || 1),
            image_name: imageName,
            image_data: imageData,
            width_m: Number(document.getElementById("wallWidthM").value || 1),
            height_m: Number(document.getElementById("wallHeightM").value || 1),
            angle: Number(document.getElementById("wallAngle").value || 0),
            work_area: workArea
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Create wall failed");
            });
        }
        return response.json();
    })
    .then(data => {
        window.location.href = `/static/wall/${data.wall_id}`;
    })
    .catch(error => {
        statusElement.textContent = error.message;
        alert(error.message);
    });
}
