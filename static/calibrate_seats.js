// static/calibrate_seats.js (reemplazado para robustez y precisión)

document.addEventListener('DOMContentLoaded', function () {
    // ===== Utilidades UI =====
    const toastElement = document.getElementById('action-toast');
    const toast = toastElement ? new bootstrap.Toast(toastElement) : null;
    function showToast(message, type = 'primary') {
        if (!toastElement || !toast) { console.log(message); return; }
        toastElement.querySelector('.toast-body').textContent = message;
        toastElement.className = `toast align-items-center text-bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.show();
    }

    // ===== Elementos =====
    const videoImg = document.getElementById('calibrateFeed');
    const canvas = document.getElementById('drawCanvas');
    const ctx = canvas.getContext('2d');
    const undoBtn = document.getElementById('undoBtn');

    // ===== Estado dibujo =====
    let drawing = false;
    let x0 = 0, y0 = 0;
    let w = 0, h = 0;

    // ===== Canvas sizing =====
    function clearPreview() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function resizeCanvas() {
        const rect = videoImg.getBoundingClientRect();
        canvas.width = Math.max(1, Math.round(rect.width));
        canvas.height = Math.max(1, Math.round(rect.height));
        drawExistingBoxes();
    }

    window.addEventListener('resize', resizeCanvas);
    videoImg.addEventListener('load', resizeCanvas);

    // ===== Dibujo con mouse/touch =====
    function getPos(evt) {
        const rect = canvas.getBoundingClientRect();
        const clientX = evt.touches ? evt.touches[0].clientX : evt.clientX;
        const clientY = evt.touches ? evt.touches[0].clientY : evt.clientY;
        return { x: clientX - rect.left, y: clientY - rect.top };
    }

    function previewRect(x, y, w, h) {
        clearPreview();
        ctx.strokeStyle = '#0dcaf0';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);
        ctx.fillStyle = 'rgba(13,202,240,0.12)';
        ctx.fillRect(x, y, w, h);
    }

    canvas.addEventListener('mousedown', (e) => {
        drawing = true;
        const p = getPos(e);
        x0 = p.x; y0 = p.y; w = 0; h = 0;
        previewRect(x0, y0, 1, 1);
    });
    canvas.addEventListener('mousemove', (e) => {
        if (!drawing) return;
        const p = getPos(e);
        w = p.x - x0; h = p.y - y0;
        previewRect(x0, y0, w, h);
    });
    canvas.addEventListener('mouseup', () => finishRect());
    canvas.addEventListener('mouseleave', () => finishRect());
    // Touch
    canvas.addEventListener('touchstart', (e) => {
        drawing = true;
        const p = getPos(e);
        x0 = p.x; y0 = p.y; w = 0; h = 0;
        previewRect(x0, y0, 1, 1);
        e.preventDefault();
    }, { passive: false });
    canvas.addEventListener('touchmove', (e) => {
        if (!drawing) return;
        const p = getPos(e);
        w = p.x - x0; h = p.y - y0;
        previewRect(x0, y0, w, h);
        e.preventDefault();
    }, { passive: false });
    canvas.addEventListener('touchend', () => finishRect());

    function finishRect() {
        if (!drawing) return;
        drawing = false;
        let fx = Math.min(x0, x0 + w);
        let fy = Math.min(y0, y0 + h);
        let fw = Math.abs(w);
        let fh = Math.abs(h);
        clearPreview();
        if (fw < 10 || fh < 10) return;
        // Guardar normalizado (preciso, independiente de resolución)
        addSeatNormalized(fx, fy, fw, fh).then(data => {
            if (data && data.success) {
                showToast(`Asiento ${data.seat_id} creado.`, 'success');
                drawExistingBoxes();
            } else {
                showToast(`Error: ${(data && data.message) || 'No se pudo crear asiento'}`, 'danger');
            }
        }).catch(err => {
            console.error(err);
            showToast('Error al crear asiento', 'danger');
        });
    }

    // ===== Normalización =====
    function toNormalizedRect(x, y, w, h) {
        const dispW = canvas.width, dispH = canvas.height;
        const natW = videoImg.naturalWidth || dispW;
        const natH = videoImg.naturalHeight || dispH;
        // Primero pasamos a coordenadas del frame natural
        const sx = natW / dispW, sy = natH / dispH;
        const fx = x * sx, fy = y * sy, fw = w * sx, fh = h * sy;
        // Luego normalizamos 0..1
        return { x: fx / natW, y: fy / natH, w: fw / natW, h: fh / natH };
    }

    function fromNormalizedRect(nr) {
        const dispW = canvas.width, dispH = canvas.height;
        const natW = videoImg.naturalWidth || dispW;
        const natH = videoImg.naturalHeight || dispH;
        const x = Math.round(nr.x * natW * (dispW / natW));
        const y = Math.round(nr.y * natH * (dispH / natH));
        const w = Math.round(nr.w * natW * (dispW / natW));
        const h = Math.round(nr.h * natH * (dispH / natH));
        return { x, y, w, h };
    }

    async function addSeatNormalized(x, y, w, h) {
        const nr = toNormalizedRect(x, y, w, h);
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
                let x, y, w, h;
                if (seat.normalized) {
                    ({ x, y, w, h } = fromNormalizedRect({ x: seat.rect[0], y: seat.rect[1], w: seat.rect[2], h: seat.rect[3] }));
                } else {
                    // Soporte legado: mapear por escala lineal de frame→display
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

    // ===== Control monitor calibración =====
    async function startCalibration() {
        try {
            const res = await fetch('/start_calibration_monitor', { method: 'POST' });
            const data = await res.json();
            if (!data.success) {
                showToast(data.message || 'No se pudo iniciar el monitor', 'danger');
                return;
            }
            // Evitar caché del mjpeg
            videoImg.src = '/video_feed/calibrate?t=' + Date.now();
            videoImg.style.display = 'block';
            videoImg.onerror = () => {
                // Retry simple si falla carga
                setTimeout(() => {
                    videoImg.src = '/video_feed/calibrate?t=' + Date.now();
                }, 1000);
            };
            showToast('Monitoreo de calibración iniciado.', 'success');
        } catch (e) {
            console.error(e);
            showToast('Error iniciando monitor de calibración', 'danger');
        }
    }

    async function stopCalibration() {
        try {
            await fetch('/stop_calibration_monitor', { method: 'POST' });
        } catch (e) {}
        videoImg.removeAttribute('src');
    }

    if (undoBtn) {
        undoBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/remove_last_seat', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('Se eliminó el último asiento.', 'warning');
                } else {
                    showToast(data.message || 'No se pudo eliminar.', 'danger');
                }
                drawExistingBoxes();
            } catch (e) {
                console.error(e);
                showToast('Error al eliminar', 'danger');
            }
        });
    }

    // ===== Init =====
    resizeCanvas();
    startCalibration();
    window.addEventListener('beforeunload', stopCalibration);
});
