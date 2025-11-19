// static/quick_scan.js

document.addEventListener('DOMContentLoaded', function () {

// --- Cámara del navegador ---
let mediaStream = null;
const videoEl = document.getElementById('cameraPreview');

async function startCamera() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
        videoEl.srcObject = mediaStream;
        videoEl.style.display = 'block';
    } catch (e) {
        console.error(e);
        showToast('No se pudo acceder a la cámara del navegador.', 'danger');
    }
}

function stopCamera() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }
    if (videoEl) {
        videoEl.srcObject = null;
        videoEl.style.display = 'none';
    }
}

function snapshotAsBase64() {
    if (!videoEl || !videoEl.videoWidth) return null;
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    const c = canvas.getContext('2d');
    c.drawImage(videoEl, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.9);
}

    const toastElement = document.getElementById('action-toast');
    const toast = new bootstrap.Toast(toastElement);

    function showToast(message, type = 'primary') {
        toastElement.querySelector('.toast-body').textContent = message;
        toastElement.className = `toast align-items-center text-bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.show();
    }

    const startBtn = document.getElementById('startScanBtn');
    const scanSection = document.getElementById('scanSection');
    const scanMessage = document.getElementById('scanMessage');
    const scanResult = document.getElementById('scanResult');
    const recognizedName = document.getElementById('recognizedName');
    const confirmYes = document.getElementById('confirmYes');
    const confirmNo = document.getElementById('confirmNo');
    const rescanBtn = document.getElementById('rescanBtn');
    const manualSelectContainer = document.getElementById('manualSelect');
    const manualSelect = document.getElementById('manualStudent');
    const confirmManual = document.getElementById('confirmManual');

    let recognizedStudentId = null;
    let studentsMap = {};

    // Cargar lista de estudiantes para selección manual
    async function loadStudents() {
        try {
            const res = await fetch('/api/students_list');
            const students = await res.json();
            studentsMap = {};
            manualSelect.innerHTML = '<option value="">Seleccione un estudiante</option>';
            students.forEach(s => {
                const fullName = `${s.nombre} ${s.apellido}`.trim();
                studentsMap[s.id] = fullName;
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = fullName;
                manualSelect.appendChild(opt);
            });
        } catch (error) {
            console.error('Error al cargar estudiantes:', error);
        }
    }

    // Reinicia el estado de la interfaz para un nuevo escaneo
    function resetUI() {
        recognizedStudentId = null;
        scanResult.classList.add('d-none');
        scanMessage.innerHTML = '';
        startBtn.disabled = false;
        scanSection.classList.remove('d-none');
        manualSelectContainer.classList.add('d-none');
        confirmYes.classList.add('d-none');
        confirmNo.classList.add('d-none');
        rescanBtn.classList.add('d-none');
    }

    startBtn.addEventListener('click', async function () {
        // Ocultar sección de botón y mostrar mensaje de escaneo
        startBtn.disabled = true;
        scanSection.classList.add('d-none');
        scanMessage.innerHTML = '<div class="text-info"><span class="spinner-border spinner-border-sm"></span> Escaneando... Por favor, mire a la cámara.</div>';

        try {
            const res = await fetch('/api/quick_scan', { method: 'POST' });
            const data = await res.json();
            scanMessage.innerHTML = '';
            scanResult.classList.remove('d-none');
            if (data.success) {
                recognizedStudentId = data.student_id;
                if (data.student_id) {
                    // Se reconoce a un estudiante
                    recognizedName.textContent = `${data.student_name} (${data.confidence.toFixed(1)}%)`;
                    confirmYes.classList.remove('d-none');
                    confirmNo.classList.remove('d-none');
                    manualSelectContainer.classList.add('d-none');
                    await loadStudents();
                } else {
                    // No se reconoció a nadie
                    recognizedName.textContent = 'No se reconoció a ningún rostro.';
                    confirmYes.classList.add('d-none');
                    confirmNo.classList.add('d-none');
                    // Mostrar selección manual directamente
                    await loadStudents();
                    manualSelectContainer.classList.remove('d-none');
                }
            } else {
                recognizedName.textContent = '';
                showToast(data.message || 'Error durante el escaneo.', 'danger');
                recognizedStudentId = null;
                confirmYes.classList.add('d-none');
                confirmNo.classList.add('d-none');
                manualSelectContainer.classList.add('d-none');
                rescanBtn.classList.remove('d-none');
            }
        } catch (error) {
            console.error(error);
            showToast('No se pudo completar el escaneo.', 'danger');
            resetUI();
        }
    });

    confirmYes.addEventListener('click', async function () {
        if (!recognizedStudentId) return;
        try {
            const res = await fetch('/api/confirm_attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: recognizedStudentId })
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message || 'Asistencia registrada.', 'success');
            } else {
                showToast(data.message || 'No se pudo registrar la asistencia.', 'danger');
            }
        } catch (error) {
            console.error(error);
            showToast('Error al registrar asistencia.', 'danger');
        } finally {
            resetUI();
        }
    });

    confirmNo.addEventListener('click', async function () {
        // Mostrar selección manual
        await loadStudents();
        confirmYes.classList.add('d-none');
        confirmNo.classList.add('d-none');
        manualSelectContainer.classList.remove('d-none');
    });

    confirmManual.addEventListener('click', async function () {
        const selectedId = manualSelect.value;
        if (!selectedId) {
            showToast('Seleccione un estudiante.', 'warning');
            return;
        }
        try {
            const res = await fetch('/api/confirm_attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: selectedId })
            });
            const data = await res.json();
            if (data.success) {
                const name = studentsMap[selectedId] || selectedId;
                showToast(data.message || `Asistencia registrada para ${name}.`, 'success');
            } else {
                showToast(data.message || 'No se pudo registrar la asistencia.', 'danger');
            }
        } catch (error) {
            console.error(error);
            showToast('Error al registrar asistencia.', 'danger');
        } finally {
            resetUI();
        }
    });

    rescanBtn.addEventListener('click', function () {
        resetUI();
    });

    // Inicialmente cargar lista de estudiantes
    loadStudents();
});