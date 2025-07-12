const responseContainer = $('#response-block .block-content');

async function getLogs() {
    try {
        const response = await fetch('https://games.datsteam.dev/api/logs', {
            method: 'GET',
            headers: {
                'accept': 'application/json',
                'X-Auth-Token': getToken(),
            }
        });

        const data = await response.json();
        responseContainer.text(`Status: ${response.status}`);

        const $logsContainer = $('#logs-block .block-content');
        const messages = data.map(log => log.message).join('\n');
        $logsContainer.text(messages);

        return data;
    }
    catch (error) {
        responseContainer.text(`Failed: ${error}`);
    }
}

async function postMove(moves) {

}

async function postRegister() {
	try {
		const response = await fetch('https://games.datsteam.dev/api/register', {
			method: 'POST',
			headers: {
				'accept': 'application/json',
				'X-Auth-Token': getToken(),
			}
		});

		const data = await response.json();
		responseContainer.text(`Status: ${response.status}\n\n${JSON.stringify(data, null, 2)}`);
		return data;
	}
	catch (error) {
		responseContainer.text(`Failed: ${error}`);
	}
}



const HEX_RADIUS = 40;
const SQRT3 = Math.sqrt(3);
let scale = 1, offsetX = 0, offsetY = 0;
let selected = null;
let isDragging = false, dragStart = { x: 0, y: 0 };

const HEX_TYPES = {
    1: { color: "#FF4500", name: "Муравейник" },
    2: { color: "#F0F0F0", name: "Пустой" },
    3: { color: "#D2B48C", name: "Грязь" },
    4: { color: "#32CD32", name: "Кислота" },
    5: { color: "#A9A9A9", name: "Камень" }
};

const ANT_TYPES = {
    0: { color: "#4CAF50", name: "Рабочий" },
    1: { color: "#2196F3", name: "Солдат" },
    2: { color: "#9C27B0", name: "Разведчик" }
};

const FOOD_TYPES = {
    0: { color: "#CCC", name: "Unknown" },
    1: { color: "#EF323D", name: "Яблоко" },
    2: { color: "#8B4513", name: "Хлеб" },
    3: { color: "#FFD700", name: "Нектар" }
};

// ========= Объекты карты =========
class HexObject {
    constructor(q, r, type, centerQ, centerR) {
        this.q = q;
        this.r = r;
        this.type = type;
        const pos = this.hexToPixel(q - centerQ, r - centerR);
        this.x = pos.x;
        this.y = pos.y;
    }

    hexToPixel(q, r) {
        return {
            x: HEX_RADIUS * 3/2 * q,
            y: HEX_RADIUS * SQRT3 * (r + q / 2)
        };
    }

    containsPoint(px, py) {
        return Math.hypot(this.x - px, this.y - py) < HEX_RADIUS * 0.6;
    }
}

class HexCell extends HexObject {
    draw(ctx) {
        const fill = selected === this ? "red" : (HEX_TYPES[this.type]?.color || "#000");
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = i * Math.PI / 3;
            const x = this.x + HEX_RADIUS * Math.cos(angle);
            const y = this.y + HEX_RADIUS * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.strokeStyle = "#000";
        ctx.stroke();
    }
}

class Ant extends HexObject {
    draw(ctx) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, HEX_RADIUS * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = selected === this ? "red" : (ANT_TYPES[this.type]?.color || "#000");
        ctx.fill();
        ctx.stroke();
    }
}

class Enemy extends HexObject {
    draw(ctx) {
        const s = HEX_RADIUS * 0.6;
        ctx.fillStyle = selected === this ? "red" : "#000";
        ctx.fillRect(this.x - s/2, this.y - s/2, s, s);
        ctx.strokeStyle = "#000";
        ctx.strokeRect(this.x - s/2, this.y - s/2, s, s);
    }
}

class Food extends HexObject {
    draw(ctx) {
        const h = HEX_RADIUS * 0.4;
        ctx.beginPath();
        ctx.moveTo(this.x, this.y - h);
        ctx.lineTo(this.x + h * Math.cos(Math.PI / 6), this.y + h * Math.sin(Math.PI / 6));
        ctx.lineTo(this.x - h * Math.cos(Math.PI / 6), this.y + h * Math.sin(Math.PI / 6));
        ctx.closePath();
        ctx.fillStyle = selected === this ? "red" : (FOOD_TYPES[this.type]?.color || "#000");
        ctx.fill();
        ctx.stroke();
    }
}

// ========= Построение и рендер =========
let objects = [];

function buildMap(data) {
    objects = [];
    if (!data.map) return;

    const qs = data.map.map(c => c.q);
    const rs = data.map.map(c => c.r);
    const centerQ = (Math.min(...qs) + Math.max(...qs)) / 2;
    const centerR = (Math.min(...rs) + Math.max(...rs)) / 2;

    data.map.forEach(c => objects.push(new HexCell(c.q, c.r, c.type, centerQ, centerR)));
    data.ants.forEach(a => objects.push(new Ant(a.q, a.r, a.type, centerQ, centerR)));
    data.enemies.forEach(e => objects.push(new Enemy(e.q, e.r, e.type, centerQ, centerR)));
    data.food.forEach(f => objects.push(new Food(f.q, f.r, f.type, centerQ, centerR)));
}

function drawMap(data) {
    const $c = $("#hex-map"), canvas = $c[0];
    const ctx = canvas.getContext("2d");
    canvas.width = $c.parent().width();
    canvas.height = $c.parent().height();

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width / 2 + offsetX, canvas.height / 2 + offsetY);
    ctx.scale(scale, scale);

    buildMap(data);
    for (const obj of objects) obj.draw(ctx);

    ctx.restore();
}

// ========= Обработка событий =========
function handleClick(e) {
    const canvas = $("#hex-map")[0];
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - canvas.width / 2 - offsetX) / scale;
    const y = (e.clientY - rect.top - canvas.height / 2 - offsetY) / scale;

    selected = objects.find(o => o.containsPoint(x, y)) || null;
    drawMap(gameData);
}

// ========= Получение данных и запуск =========
let gameData = null;

async function getArena() {
    const res = await fetch("https://games.datsteam.dev/api/arena", {
        headers: { "X-Auth-Token": getToken(), "accept": "application/json" }
    });
    const data = await res.json();
    gameData = data;
    drawMap(data);
}

function getToken() {
    let token = localStorage.getItem("TOKEN");
    if (!token) {
        token = prompt("Введите TOKEN:");
        if (token) localStorage.setItem("TOKEN", token);
    }
    return token;
}

function setupCanvasEvents() {
    const $canvas = $("#hex-map");

    $canvas.on("mousedown", e => {
        if (e.button === 2) {
            isDragging = true;
            dragStart = { x: e.clientX - offsetX, y: e.clientY - offsetY };
        }
    });

    $(window).on("mousemove", e => {
        if (!isDragging) return;
        offsetX = e.clientX - dragStart.x;
        offsetY = e.clientY - dragStart.y;
        drawMap(gameData);
    }).on("mouseup", e => {
        if (e.button === 2) isDragging = false;
    });

    $canvas.on("wheel", e => {
        e.preventDefault();
        const zoom = e.originalEvent.deltaY < 0 ? 1.1 : 0.9;
        scale = Math.max(0.2, Math.min(5, scale * zoom));
        drawMap(gameData);
    });

    $canvas.on("click", handleClick);
    $canvas.on("contextmenu", e => e.preventDefault());
}

$(function () {
    setupCanvasEvents();
    getArena();
    setInterval(getArena, 2000);
    setInterval(getLogs, 3000);
});
