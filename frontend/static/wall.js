const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let holds = [];
let savedHolds = [];
let currentWallId = new URLSearchParams(window.location.search).get("wall_id") || "1";
let imageName = "wall.jpg";
let currentSurfaceId = null;
let draggingHoldId = null;
let selectedHoldId = null;
let dragMoved = false;
let suppressNextClick = false;

const img = new Image();
const forceVectorDirections = {
    down: { dx: 0, dy: -1 },
    up: { dx: 0, dy: 1 },
    left: { dx: -1, dy: 0 },
    right: { dx: 1, dy: 0 }
};

document.getElementById("wallId").value = currentWallId;
document.getElementById("holdQuality").addEventListener("input", function (event) {
    document.getElementById("holdQualityValue").textContent = event.target.value;
});

function setStatus(message) {
    document.getElementById("status").textContent = message;
}

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
        if (data.surfaces && data.surfaces.length > 0) {
            const surface = data.surfaces[0];
            currentSurfaceId = surface.id;
            document.getElementById("wallWidthM").value = surface.width_m || surface.width || 1;
            document.getElementById("wallHeightM").value = surface.height_m || surface.height || 1;
            document.getElementById("wallAngle").value = surface.angle || 0;
        }
        img.src = `/images/${imageName}`;
        setStatus(`Loaded wall ${currentWallId}`);
    })
    .catch(error => alert(error.message));
}

function updateCurrentSurfaceGeometry() {
    if (!currentSurfaceId) {
        alert("Load a wall first");
        return;
    }

    fetch(`/api/surfaces/${currentSurfaceId}/geometry`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            width_m: Number(document.getElementById("wallWidthM").value || 1),
            height_m: Number(document.getElementById("wallHeightM").value || 1),
            image_width_px: canvas.width || img.width || 1,
            image_height_px: canvas.height || img.height || 1,
            angle: Number(document.getElementById("wallAngle").value || 0)
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Update failed");
            });
        }
        return response.json();
    })
    .then(data => {
        savedHolds = data.holds || [];
        redraw();
        setStatus("Wall parameters updated");
    })
    .catch(error => alert(error.message));
}

img.onload = function () {
    canvas.width = img.width;
    canvas.height = img.height;
    redraw();
};

canvas.addEventListener("click", function (event) {
    if (suppressNextClick) {
        suppressNextClick = false;
        return;
    }

    const rect = canvas.getBoundingClientRect();

    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const pixelX = (event.clientX - rect.left) * scaleX;
    const pixelY = (event.clientY - rect.top) * scaleY;
    const existingHold = findHold(pixelX, pixelY);
    if (existingHold) {
        applyHoldToControls(existingHold);
        selectedHoldId = existingHold.id || null;
        setStatus(`Selected hold ${existingHold.id}`);
        return;
    }

    const x = pixelX / canvas.width;
    const y = pixelY / canvas.height;

    const holdType = document.getElementById("holdType").value;
    const quality = Number(document.getElementById("holdQuality").value);
    const forceVectors = selectedForceVectors();

    holds.push({
        x,
        y,
        x_px: pixelX,
        y_px: pixelY,
        hold_type: holdType,
        quality,
        force_vectors: forceVectors
    });

    redraw();
});

canvas.addEventListener("mousedown", function (event) {
    const point = eventPoint(event);
    const hold = findHold(point.x, point.y);
    if (!hold || !hold.id) {
        return;
    }

    draggingHoldId = hold.id;
    dragMoved = false;
});

canvas.addEventListener("mousemove", function (event) {
    if (!draggingHoldId) {
        return;
    }

    const point = eventPoint(event);
    const hold = savedHolds.find(item => item.id === draggingHoldId);
    if (!hold) {
        return;
    }

    hold.x_px = point.x;
    hold.y_px = point.y;
    hold.x = point.x / canvas.width;
    hold.y = point.y / canvas.height;
    dragMoved = true;
    redraw();
});

canvas.addEventListener("mouseup", function () {
    if (!draggingHoldId) {
        return;
    }

    const hold = savedHolds.find(item => item.id === draggingHoldId);
    const holdId = draggingHoldId;
    draggingHoldId = null;

    if (!hold || !dragMoved) {
        return;
    }

    suppressNextClick = true;
    updateHold(holdId, {
        x_px: hold.x_px,
        y_px: hold.y_px
    }).then(updatedHold => {
        replaceSavedHold(updatedHold);
        redraw();
        setStatus(`Moved hold ${holdId}`);
    });
});

canvas.addEventListener("contextmenu", function (event) {
    event.preventDefault();
    const point = eventPoint(event);
    const hold = findHold(point.x, point.y);
    if (!hold) {
        return;
    }

    if (hold.id) {
        fetch(`/api/walls/${currentWallId}/holds/${hold.id}`, { method: "DELETE" })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Delete failed");
                }
                savedHolds = savedHolds.filter(item => item.id !== hold.id);
                redraw();
                setStatus(`Deleted hold ${hold.id}`);
            })
            .catch(error => alert(error.message));
    } else {
        holds = holds.filter(item => item !== hold);
        redraw();
    }
});

function eventPoint(event) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
    };
}

function findHold(x, y) {
    return [...savedHolds, ...holds].find(hold => {
        const point = holdPixelPoint(hold);
        if (!point) {
            return false;
        }

        const dx = point.x - x;
        const dy = point.y - y;
        return Math.sqrt(dx * dx + dy * dy) <= 10;
    });
}

function holdPixelPoint(hold) {
    if (hold.x_px !== undefined && hold.y_px !== undefined && hold.x_px !== null && hold.y_px !== null) {
        return { x: hold.x_px, y: hold.y_px };
    }

    if (hold.x !== undefined && hold.y !== undefined) {
        return { x: hold.x * canvas.width, y: hold.y * canvas.height };
    }

    return null;
}

function applyHoldToControls(hold) {
    document.getElementById("holdType").value = hold.hold_type || "jug";
    document.getElementById("holdQuality").value = hold.quality || 5;
    document.getElementById("holdQualityValue").textContent = hold.quality || 5;

    const vectors = parseForceVectors(hold.force_vectors);
    document.querySelectorAll(".forceVector").forEach(input => {
        input.checked = vectors.some(vector => vector.name === input.value);
    });
}

function updateHold(holdId, payload) {
    return fetch(`/api/holds/${holdId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    }).then(response => {
        if (!response.ok) {
            throw new Error("Update failed");
        }
        return response.json();
    });
}

function replaceSavedHold(updatedHold) {
    savedHolds = savedHolds.map(hold => hold.id === updatedHold.id ? updatedHold : hold);
}

function saveSelectedHoldSettings() {
    const selected = savedHolds.find(hold => hold.id === selectedHoldId);
    if (!selected) {
        alert("Select a saved hold first");
        return;
    }

    updateHold(selected.id, {
        hold_type: document.getElementById("holdType").value,
        quality: Number(document.getElementById("holdQuality").value),
        force_vectors: selectedForceVectors()
    }).then(updatedHold => {
        replaceSavedHold(updatedHold);
        redraw();
        setStatus(`Updated hold ${selected.id}`);
    });
}

function selectedForceVectors() {
    return Array.from(document.querySelectorAll(".forceVector:checked"))
        .map(input => ({
            name: input.value,
            dx: forceVectorDirections[input.value].dx,
            dy: forceVectorDirections[input.value].dy
        }));
}

function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    savedHolds.forEach(hold => drawHold(hold, "red"));
    holds.forEach(hold => drawHold(hold, "orange"));
}

function drawHold(hold, color = "red") {
    const vectors = parseForceVectors(hold.force_vectors);
    const point = holdPixelPoint(hold);
    if (point) {
        drawPixelPoint(point.x, point.y, color);
        drawQualityLabel(point.x, point.y, hold.quality);
        drawForceVectors(point.x, point.y, vectors);
    }
}

function parseForceVectors(rawVectors) {
    if (!rawVectors) {
        return [];
    }

    if (Array.isArray(rawVectors)) {
        return rawVectors;
    }

    try {
        return JSON.parse(rawVectors);
    } catch (_error) {
        return [];
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

function drawForceVectors(x, y, vectors) {
    vectors.forEach(vector => {
        const length = 24;
        const endX = x + vector.dx * length;
        const endY = y - vector.dy * length;

        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(endX, endY);
        ctx.strokeStyle = "#222";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(endX, endY, 3, 0, 2 * Math.PI);
        ctx.fillStyle = "#222";
        ctx.fill();
    });
}

function drawQualityLabel(x, y, quality) {
    if (!quality) {
        return;
    }

    ctx.font = "12px Arial";
    ctx.fillStyle = "#111";
    ctx.fillText(String(quality), x + 8, y - 8);
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
        setStatus("Annotations saved");
    });
}

function uploadWall() {
    const fileInput = document.getElementById("wallImage");
    const file = fileInput.files[0];
    if (!file) {
        alert("Select an image first");
        return;
    }

    const reader = new FileReader();
    reader.onload = function () {
        fetch("/api/walls/upload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                gym_id: Number(document.getElementById("gymId").value || 1),
                image_name: file.name,
                image_data: reader.result,
                width_m: Number(document.getElementById("wallWidthM").value || 1),
                height_m: Number(document.getElementById("wallHeightM").value || 1),
                angle: Number(document.getElementById("wallAngle").value || 0)
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Upload failed");
            }
            return response.json();
        })
        .then(data => {
            currentWallId = String(data.wall_id);
            document.getElementById("wallId").value = currentWallId;
            setStatus(`Uploaded wall ${currentWallId}`);
            loadWall();
        })
        .catch(error => alert(error.message));
    };
    reader.readAsDataURL(file);
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
