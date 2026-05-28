const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let holds = [];
let savedHolds = [];
let currentWallId = initialWallId();
let imageName = "wall.jpg";
let currentSurfaceId = null;
let currentWorkArea = [];
let draggingHoldId = null;
let selectedHoldId = null;
let selectedDraftHold = null;
let dragMoved = false;
let suppressNextClick = false;
let routeMarks = [];
let nextPositionMarks = [];
let routeRequestSeq = 0;
let routesPage = 1;
let routesPageSize = 8;
let routesTotal = 0;
let selectedRouteId = null;

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
document.getElementById("routesRefresh").addEventListener("click", function () {
    loadRoutes(routesPage);
});
document.getElementById("routesPrev").addEventListener("click", function () {
    loadRoutes(routesPage - 1);
});
document.getElementById("routesNext").addEventListener("click", function () {
    loadRoutes(routesPage + 1);
});

function setStatus(message) {
    document.getElementById("status").textContent = message;
}

function initialWallId() {
    const queryWallId = new URLSearchParams(window.location.search).get("wall_id");
    if (queryWallId) {
        return queryWallId;
    }

    const match = window.location.pathname.match(/\/static\/wall\/(\d+)$/);
    return match ? match[1] : "1";
}

function loadWall() {
    currentWallId = document.getElementById("wallId").value || "1";
    holds = [];
    savedHolds = [];
    selectedHoldId = null;
    selectedDraftHold = null;
    routeMarks = [];
    nextPositionMarks = [];
    selectedRouteId = null;
    renderRouteResult(null);

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
            currentWorkArea = parseWorkArea(surface.work_area);
            document.getElementById("wallWidthM").value = surface.width_m || surface.width || 1;
            document.getElementById("wallHeightM").value = surface.height_m || surface.height || 1;
            document.getElementById("wallAngle").value = surface.angle || 0;
        }
        img.src = `/images/${imageName}`;
        routesPage = 1;
        loadRoutes(routesPage);
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
        selectedHoldId = hasSavedId(existingHold) ? existingHold.id : null;
        selectedDraftHold = hasSavedId(existingHold) ? null : existingHold;
        redraw();
        setStatus(hasSavedId(existingHold) ? `Selected hold ${existingHold.id}` : "Selected draft hold");
        return;
    }

    const x = pixelX / canvas.width;
    const y = pixelY / canvas.height;

    const holdType = document.getElementById("holdType").value;
    const quality = Number(document.getElementById("holdQuality").value);
    const forceVectors = selectedForceVectors();

    const draftHold = {
        x,
        y,
        x_px: pixelX,
        y_px: pixelY,
        hold_type: holdType,
        quality,
        force_vectors: forceVectors
    };
    holds.push(draftHold);
    selectedHoldId = null;
    selectedDraftHold = draftHold;

    redraw();
});

canvas.addEventListener("mousedown", function (event) {
    const point = eventPoint(event);
    const hold = findHold(point.x, point.y);
    if (!hold || !hasSavedId(hold)) {
        return;
    }

    draggingHoldId = hold.id;
    selectedHoldId = hold.id;
    selectedDraftHold = null;
    dragMoved = false;
    redraw();
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

    if (hasSavedId(hold)) {
        fetch(`/api/walls/${currentWallId}/holds/${hold.id}`, { method: "DELETE" })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Delete failed");
                }
                savedHolds = savedHolds.filter(item => item.id !== hold.id);
                if (selectedHoldId === hold.id) {
                    selectedHoldId = null;
                }
                redraw();
                setStatus(`Deleted hold ${hold.id}`);
            })
            .catch(error => alert(error.message));
    } else {
        holds = holds.filter(item => item !== hold);
        if (selectedDraftHold === hold) {
            selectedDraftHold = null;
        }
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

function hasSavedId(hold) {
    return hold.id !== undefined && hold.id !== null;
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
    drawWorkArea();
    savedHolds.forEach(hold => drawHold(hold, "red"));
    holds.forEach(hold => drawHold(hold, "orange"));
    drawRoute();
    drawNextPosition();
    drawSelectedHold();
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

function parseWorkArea(rawWorkArea) {
    if (!rawWorkArea) {
        return [];
    }
    if (Array.isArray(rawWorkArea)) {
        return rawWorkArea;
    }
    try {
        return JSON.parse(rawWorkArea);
    } catch (_error) {
        return [];
    }
}

function drawWorkArea() {
    if (!currentWorkArea || currentWorkArea.length !== 4) {
        return;
    }

    ctx.save();
    ctx.beginPath();
    currentWorkArea.forEach((point, index) => {
        if (index === 0) {
            ctx.moveTo(point.x, point.y);
        } else {
            ctx.lineTo(point.x, point.y);
        }
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(37, 99, 235, 0.08)";
    ctx.strokeStyle = "rgba(37, 99, 235, 0.72)";
    ctx.lineWidth = 3;
    ctx.fill();
    ctx.stroke();
    ctx.restore();
}

function drawSelectedHold() {
    const selectedHold = savedHolds.find(hold => hold.id === selectedHoldId) || selectedDraftHold;
    const point = selectedHold ? holdPixelPoint(selectedHold) : null;
    if (!point) {
        return;
    }

    ctx.save();
    ctx.beginPath();
    ctx.arc(point.x, point.y, 14, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(37, 99, 235, 0.16)";
    ctx.fill();
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 4;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(point.x - 18, point.y);
    ctx.lineTo(point.x + 18, point.y);
    ctx.moveTo(point.x, point.y - 18);
    ctx.lineTo(point.x, point.y + 18);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
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

function drawCircle(x, y, color = "green", radius = 12, lineWidth = 3) {
    ctx.beginPath();
    ctx.arc(x * canvas.width, y * canvas.height, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
}

function drawRoute() {
    if (routeMarks.length === 0) {
        return;
    }

    const points = routeMarks
        .map(mark => ({ mark, point: holdPixelPoint(mark.hold) }))
        .filter(item => item.point);

    if (points.length === 0) {
        return;
    }

    ctx.save();
    points.forEach(item => drawRouteHoldMark(item.mark, item.point));
    ctx.restore();
}

function drawRouteHoldMark(mark, point) {
    const color = routeMarkColor(mark.role);
    ctx.beginPath();
    ctx.arc(point.x, point.y, 17, 0, 2 * Math.PI);
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(point.x, point.y, 23, 0, 2 * Math.PI);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
}

function routeMarkColor(role) {
    return isRouteEndpoint(role) ? "#facc15" : "#dc2626";
}

function isRouteEndpoint(role) {
    return role === "start" || role === "finish" || role === "top";
}

function drawNextPosition() {
    if (nextPositionMarks.length === 0) {
        return;
    }

    ctx.save();
    nextPositionMarks
        .map(hold => holdPixelPoint(hold))
        .filter(point => point)
        .forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 29, 0, 2 * Math.PI);
            ctx.strokeStyle = "#16a34a";
            ctx.lineWidth = 4;
            ctx.stroke();
        });
    ctx.restore();
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
        selectedHoldId = null;
        selectedDraftHold = null;
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
    const requestSeq = routeRequestSeq + 1;
    routeRequestSeq = requestSeq;
    routeMarks = [];
    nextPositionMarks = [];
    selectedRouteId = null;
    renderRouteResult(null);
    redraw();
    setStatus("Generating route...");

    fetch("/api/routes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            wall_id: Number(currentWallId)
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Route generation failed");
            });
        }
        return response.json();
    })
    .then(data => {
        if (requestSeq !== routeRequestSeq) {
            return;
        }
        selectedRouteId = data.route_id;
        routeMarks = routeMarksFromRoute(data);
        redraw();
        renderRouteResult(data);
        loadRoutes(1);
        if (data.difficulty_score !== null && data.difficulty_score !== undefined) {
            setStatus(`Generated route. Start difficulty: ${data.difficulty_score.toFixed(2)}`);
        } else {
            setStatus("Generated route");
        }
    })
    .catch(error => {
        if (requestSeq !== routeRequestSeq) {
            return;
        }
        redraw();
        setStatus(error.message);
        alert(error.message);
    });
}

function loadRoutes(page = 1) {
    const nextPage = Math.max(1, page);
    fetch(`/api/walls/${currentWallId}/routes?page=${nextPage}&page_size=${routesPageSize}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Routes loading failed");
            });
        }
        return response.json();
    })
    .then(data => {
        routesPage = data.page || nextPage;
        routesPageSize = data.page_size || routesPageSize;
        routesTotal = data.total || 0;
        renderRoutesList(data.routes || []);
    })
    .catch(error => setStatus(error.message));
}

function renderRoutesList(routes) {
    const list = document.getElementById("routesList");
    const pageInfo = document.getElementById("routesPageInfo");
    const prev = document.getElementById("routesPrev");
    const next = document.getElementById("routesNext");
    const totalPages = Math.max(1, Math.ceil(routesTotal / routesPageSize));

    list.innerHTML = "";
    if (routes.length === 0) {
        const empty = document.createElement("div");
        empty.className = "route-list-meta";
        empty.textContent = `No routes for wall #${currentWallId}`;
        list.appendChild(empty);
    }

    routes.forEach(route => list.appendChild(routeListItem(route)));
    pageInfo.textContent = `${routesPage} / ${totalPages}`;
    prev.disabled = routesPage <= 1;
    next.disabled = routesPage >= totalPages;
}

function routeListItem(route) {
    const item = document.createElement("div");
    item.className = "route-list-item";
    if (route.route_id === selectedRouteId) {
        item.classList.add("is-selected");
    }

    const description = document.createElement("div");
    const title = document.createElement("div");
    title.className = "route-list-title";
    title.textContent = `Route #${route.route_id}`;
    const meta = document.createElement("div");
    meta.className = "route-list-meta";
    meta.textContent = routeMeta(route);
    description.appendChild(title);
    description.appendChild(meta);

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.textContent = "Select";
    selectButton.addEventListener("click", () => selectRoute(route));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteRoute(route.route_id));

    const nextMoveButton = document.createElement("button");
    nextMoveButton.type = "button";
    nextMoveButton.textContent = "Next move";
    nextMoveButton.addEventListener("click", () => addNextMove(route));

    item.appendChild(description);
    item.appendChild(selectButton);
    item.appendChild(nextMoveButton);
    item.appendChild(deleteButton);
    return item;
}

function routeMeta(route) {
    const holds = (route.start_holds || []).map(hold => hold.id).join(", ") || "none";
    const score = route.difficulty_score !== null && route.difficulty_score !== undefined
        ? formatNumber(route.difficulty_score)
        : "-";
    return `start holds: ${holds} | score: ${score}`;
}

function routeMarksFromRoute(route) {
    if (Array.isArray(route.holds) && route.holds.length > 0) {
        return route.holds
            .filter(item => item.hold)
            .map(item => ({
                role: item.role || "intermediate",
                hold: item.hold
            }));
    }

    return (route.start_holds || []).map(hold => ({
        role: "start",
        hold
    }));
}

function selectRoute(route) {
    selectedRouteId = route.route_id;
    routeMarks = routeMarksFromRoute(route);
    nextPositionMarks = [];
    renderRouteResult(route);
    redraw();
    loadRoutes(routesPage);
    setStatus(`Selected route #${route.route_id}`);
}

function deleteRoute(routeId) {
    fetch(`/api/walls/${currentWallId}/routes/${routeId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Route deletion failed");
            });
        }
        return response.json();
    })
    .then(() => {
        if (selectedRouteId === routeId) {
            selectedRouteId = null;
            routeMarks = [];
            nextPositionMarks = [];
            renderRouteResult(null);
            redraw();
        }
        const maxPage = Math.max(1, Math.ceil((routesTotal - 1) / routesPageSize));
        loadRoutes(Math.min(routesPage, maxPage));
        setStatus(`Deleted route #${routeId}`);
    })
    .catch(error => {
        setStatus(error.message);
        alert(error.message);
    });
}

function addNextMove(route = null) {
    if (route) {
        selectedRouteId = route.route_id;
        routeMarks = routeMarksFromRoute(route);
        nextPositionMarks = [];
        renderRouteResult(route);
        redraw();
    }

    if (!selectedRouteId) {
        alert("Select a route first");
        return;
    }

    fetch(`/api/walls/${currentWallId}/routes/${selectedRouteId}/next_move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || "Next move failed");
            });
        }
        return response.json();
    })
    .then(data => {
        const route = data.route;
        selectedRouteId = route.route_id;
        routeMarks = routeMarksFromRoute(route);
        nextPositionMarks = (data.next_position && data.next_position.holds) || [];
        renderRouteResult(route);
        loadRoutes(routesPage);
        redraw();
        setStatus(`Next move: ${data.role}, position score ${formatNumber(data.next_position && data.next_position.score)}`);
    })
    .catch(error => {
        setStatus(error.message);
        alert(error.message);
    });
}

function renderRouteResult(data) {
    const result = document.getElementById("routeResult");
    const summary = document.getElementById("routeSummary");
    const breakdownBody = document.getElementById("routeBreakdown");

    if (!data) {
        result.hidden = true;
        summary.textContent = "";
        breakdownBody.innerHTML = "";
        return;
    }

    if (!data.start_position_score) {
        const startHoldIds = (data.start_holds || []).map(hold => hold.id).join(", ");
        result.hidden = false;
        summary.textContent = [
            `Route #${data.route_id}`,
            `start holds: ${startHoldIds || "none"}`,
            `score: ${formatNumber(data.difficulty_score)}`
        ].join(" | ");
        breakdownBody.innerHTML = "";
        return;
    }

    const positionScore = data.start_position_score;
    const startHoldIds = (data.start_holds || []).map(hold => hold.id).join(", ");
    result.hidden = false;
    summary.textContent = [
        `Route #${data.route_id}`,
        `start holds: ${startHoldIds || "none"}`,
        `score: ${formatNumber(positionScore.score)}`,
        `realistic: ${positionScore.is_realistic ? "yes" : "no"}`
    ].join(" | ");

    breakdownBody.innerHTML = "";
    Object.keys(positionScore.breakdown || {}).forEach(name => {
        const row = document.createElement("tr");
        row.appendChild(tableCell(name));
        row.appendChild(tableCell(formatNumber(positionScore.breakdown[name])));
        row.appendChild(tableCell(formatNumber(positionScore.weights[name])));
        row.appendChild(tableCell(formatNumber(positionScore.weighted_breakdown[name])));
        breakdownBody.appendChild(row);
    });
}

function tableCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value;
    return cell;
}

function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "-";
    }
    return Number(value).toFixed(3);
}

loadWall();
