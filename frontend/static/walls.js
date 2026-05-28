const wallsList = document.getElementById("wallsList");
const statusElement = document.getElementById("status");

fetch("/api/walls")
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to load walls");
        }
        return response.json();
    })
    .then(walls => {
        if (walls.length === 0) {
            statusElement.textContent = "No walls yet";
            return;
        }

        wallsList.innerHTML = "";
        walls.forEach(wall => {
            const item = document.createElement("a");
            item.className = "wall-list-item";
            item.href = `/static/wall/${wall.id}`;
            item.innerHTML = `
                <img src="/images/${wall.image_name}" alt="">
                <span>Wall #${wall.id}</span>
                <small>${wall.holds_count || 0} holds</small>
            `;
            wallsList.appendChild(item);
        });
    })
    .catch(error => {
        statusElement.textContent = error.message;
    });
