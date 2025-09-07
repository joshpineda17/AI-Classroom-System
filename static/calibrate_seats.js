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
        // Suponemos que el tamaño del video en el backend coincide con el tamaño mostrado
        return { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) };
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
        // Enviar al backend
        fetch('/api/add_seat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(coords)
        }).then(res => res.json()).then(data => {
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
    });
    window.addEventListener('resize', () => {
        resizeCanvas();
    });

    // Iniciar calibración
    startCalibration();
    // Detener calibración al salir
    window.addEventListener('beforeunload', stopCalibration);
});