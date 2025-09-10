// static/calibrate_seats.js

document.addEventListener('DOMContentLoaded', function () {
    const toastElement = document.getElementById('action-toast');
    const toast = new bootstrap.Toast(toastElement);

    function showToast(message, type = 'primary') {
        toastElement.querySelector('.toast-body').textContent = message;
        toastElement.className = `toast align-items-center text-bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.show();
    }

    const videoImg = document.getElementById('calibrateFeed');
    const canvas = document.getElementById('drawCanvas');
    const ctx = canvas.getContext('2d');
    const undoBtn = document.getElementById('undoBtn');

    let drawing = false;
    let startX = 0;
    let startY = 0;

    // Ajusta el tamaño del canvas al contenedor de video
    function resizeCanvas() {
        const rect = videoImg.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
    }

    // Dibuja el rectángulo de vista previa
    function drawPreview(x0, y0, x1, y1) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 2;
        const rx = Math.min(x0, x1);
        const ry = Math.min(y0, y1);
        const rw = Math.abs(x1 - x0);
        const rh = Math.abs(y1 - y0);
        ctx.strokeRect(rx, ry, rw, rh);
    }

    // Limpia la vista previa
    function clearPreview() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // Convierte coordenadas del canvas a coordenadas relativas del video (en píxeles)
    function convertCoordsToVideo(x, y, w, h) {
    // Mapear coords del canvas (mostrado) al tamaño real del frame (naturalWidth/Height)
    const dispW = canvas.width;
    const dispH = canvas.height;
    const natW = videoImg.naturalWidth || dispW;
    const natH = videoImg.naturalHeight || dispH;
    const sx = natW / dispW;
    const sy = natH / dispH;
    return {
        x: Math.round(x * sx),
        y: Math.round(y * sy),
        w: Math.round(w * sx),
        h: Math.round(h * sy)
    };
};
    }

    // Manejo de eventos para dibujar cajas
    canvas.addEventListener('mousedown', function (e) {
        if (!videoImg.src) return;
        drawing = true;
        const rect = canvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
    });

    canvas.addEventListener('mousemove', function (e) {
        if (!drawing) return;
        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        drawPreview(startX, startY, currentX, currentY);
    });

    canvas.addEventListener('mouseup', function (e) {
        if (!drawing) return;
        drawing = false;
        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;
        const x0 = Math.min(startX, endX);
        const y0 = Math.min(startY, endY);
        const w = Math.abs(endX - startX);
        const h = Math.abs(endY - startY);
        clearPreview();
        // Evitar cajas muy pequeñas
        if (w < 10 || h < 10) return;
        const coords = convertCoordsToVideo(x0, y0, w, h);
        // Enviar al backend como NORMALIZADO para precisión
        addSeatNormalized(x0, y0, w, h).then(data => { if (data.success) { showToast(`Asiento ${data.seat_id} creado.`, 'success'); } else { showToast(`Error: ${data.message}`, 'danger'); } }).catch(err => { console.error(err); showToast('Error al crear asiento', 'danger'); });
        // fetch('/api/add_seat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(coords)
        // }).then(res => res.json()).then(data => {
            if (data.success) {
                showToast(`Asiento ${data.seat_id} creado.`, 'success');
            } else {
                showToast(`Error: ${data.message}`, 'danger');
            }
        }).catch(err => {
            console.error(err);
            showToast('Error al enviar la caja.', 'danger');
        });
    });

    // Botón para deshacer última caja
    undoBtn.addEventListener('click', function () {
        fetch('/api/remove_last_seat', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast('Última caja eliminada.', 'warning');
                } else {
                    showToast('No hay cajas para eliminar.', 'warning');
                }
            }).catch(err => {
                console.error(err);
                showToast('Error al eliminar la caja.', 'danger');
            });
    });

    // Iniciar el monitor de calibración al cargar la página
    function startCalibration() {
        fetch('/start_calibration_monitor', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    videoImg.src = '/video_feed/calibrate';
                } else {
                    showToast(data.message || 'No se pudo iniciar el monitor', 'danger');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Error iniciando la calibración.', 'danger');
            });
    }

    // Detener el monitor al salir de la página
    function stopCalibration() {
        fetch('/stop_calibration_monitor', { method: 'POST' }).catch(() => { });
    }

    // Redimensionar el canvas cuando la imagen de video cambie
    videoImg.addEventListener('load', () => {
        resizeCanvas();
        drawExistingBoxes();
    });
    window.addEventListener('resize', () => {
        resizeCanvas();
        drawExistingBoxes();
    });

    // Iniciar calibración
    startCalibration();
    // Detener calibración al salir
    window.addEventListener('beforeunload', stopCalibration);
});

// ---- Precisión: guardar coordenadas normalizadas respecto al tamaño del video ----
function toNormalizedRect(x, y, w, h) {
    const W = videoImg.naturalWidth || videoImg.width;
    const H = videoImg.naturalHeight || videoImg.height;
    return { x: x / W, y: y / H, w: w / W, h: h / H };
}
function fromNormalizedRect(nr) {
    const W = videoImg.width;
    const H = videoImg.height;
    return { x: Math.round(nr.x * W), y: Math.round(nr.y * H), w: Math.round(nr.w * W), h: Math.round(nr.h * H) };
}

async function addSeatNormalized(x, y, w, h) {
    const nr = toNormalizedRect(x,y,w,h);
    const resp = await fetch('/api/add_seat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x: nr.x, y: nr.y, w: nr.w, h: nr.h, normalized: true })
    });
    return resp.json();
}


async function drawExistingBoxes() {
    try {
        const res = await fetch('/api/seat_boxes');
        const data = await res.json();
        clearPreview();
        if (!Array.isArray(data)) return;
        for (const seat of data) {
            let x,y,w,h;
            if (seat.normalized) {
                const r = fromNormalizedRect({x: seat.rect[0], y: seat.rect[1], w: seat.rect[2], h: seat.rect[3]});
                x = r.x; y = r.y; w = r.w; h = r.h;
            } else {
                const natW = videoImg.naturalWidth || canvas.width;
                const natH = videoImg.naturalHeight || canvas.height;
                const sx = canvas.width / natW;
                const sy = canvas.height / natH;
                x = Math.round(seat.rect[0] * sx);
                y = Math.round(seat.rect[1] * sy);
                w = Math.round(seat.rect[2] * sx);
                h = Math.round(seat.rect[3] * sy);
            }
            ctx.strokeStyle = '#0dcaf0';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);
            ctx.fillStyle = 'rgba(13,202,240,0.12)';
            ctx.fillRect(x, y, w, h);
        }
    } catch (e) {
        console.error('No se pudieron dibujar cajas existentes', e);
    }
}
