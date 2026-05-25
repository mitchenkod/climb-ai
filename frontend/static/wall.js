const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let holds = [];
let savedHolds = [];
let currentWallId = new URLSearchParams(window.location.search).get("wall_id") || "1";
let imageName = "wall.jpg";

const img = new Image();

document.getElementById("wallId").value = currentWallId;

function loadWall() {
    currentWallId = document.getElementById("wallId").value || "1";
    holds = [];
    savedHolds = [];

    fetch(`/api/walls/${currentWallId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Wall ${currentWallId} not found`);
        }
        return response.json(); 
    })
    .then(data => {
        imageName = data.image_name || "wall.jpg";
        savedHolds = data.holds || [];
        img.src = `/images/${imageName}`;
    })
    .catch(error => alert(error.message));
}

img.onload = function () {
    canvas.width = img.width;
    canvas.height = img.height;
    redraw();
};

canvas.addEventListener("click", function (event) {
    const rect = canvas.getBoundingClientRect();

    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const pixelX = (event.clientX - rect.left) * scaleX;
    const pixelY = (event.clientY - rect.top) * scaleY;
    const x = pixelX / canvas.width;
    const y = pixelY / canvas.height;

    const holdType = document.getElementById("holdType").value;

    holds.push({ x, y, x_px: pixelX, y_px: pixelY, hold_type: holdType });

    redraw();
});

function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    savedHolds.forEach(hold => drawHold(hold, "red"));
    holds.forEach(hold => drawHold(hold, "orange"));
}

function drawHold(hold, color = "red") {
    if (hold.x !== undefined && hold.y !== undefined) {
        drawPoint(hold.x, hold.y, color);
        return;
    }

    if (hold.x_px !== undefined && hold.y_px !== undefined) {
        drawPixelPoint(hold.x_px, hold.y_px, color);
    }
}

function drawPoint(x, y, color = "red") {
    drawPixelPoint(x * canvas.width, y * canvas.height, color);
}

function drawPixelPoint(x, y, color = "red") {
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
}

function drawCircle(x, y) {
    ctx.beginPath();
    ctx.arc(x * canvas.width, y * canvas.height, 12, 0, 2 * Math.PI);
    ctx.strokeStyle = "green";
    ctx.lineWidth = 3;
    ctx.stroke();
}

function saveAnnotations() {
    if (holds.length === 0) {
        alert("Nothing to save");
        return;
    }

    fetch(`/api/walls/${currentWallId}/holds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            holds: holds
        })
    })
    .then(response => response.json())
    .then(data => {
        savedHolds = data.holds || [];
        holds = [];
        redraw();
        alert("Saved!");
    });
}

function generateRoute() {
    fetch("/api/routes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            wall_id: Number(currentWallId)
        })
    })
    .then(response => response.json())
    .then(data => {
        redraw();
        data.start_holds.forEach(hold => drawCircle(hold.x, hold.y));
    });
}

loadWall();
