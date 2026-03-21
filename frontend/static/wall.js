const imageName = "output_graph.jpg";
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let holds = [];

const img = new Image();
img.src = `/images/${imageName}`;

function getWall() {
    fetch("/api/walls/1", {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => {
        return response.json(); 
      })
      .then(data => {
        // 3. Получаем и используем данные
        console.log(data.holds);
        data.holds.forEach( hold => {drawPoint(hold.x, hold.y)} )
      })
}

img.onload = function () {
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    getWall();
};

canvas.addEventListener("click", function (event) {
    const rect = canvas.getBoundingClientRect();

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const holdType = document.getElementById("holdType").value;

    holds.push({ x, y, hold_type: holdType });

    drawPoint(x, y);
});

function drawPoint(x, y) {
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fillStyle = "red";
    ctx.fill();
}

function saveAnnotations() {
    fetch("/api/walls/1/holds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            holds: holds
        })
    })
    .then(response => response.json())
    .then(data => alert("Saved!"));
}