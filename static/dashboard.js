// static/dashboard.js
document.addEventListener('DOMContentLoaded', function () {
    console.log('dashboard.js v4 loaded');
    const toastElement = document.getElementById('action-toast');
    const toast = new bootstrap.Toast(toastElement);
    const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
    const enhancedTextModal = new bootstrap.Modal(document.getElementById('enhancedTextModal'));
    const videoFeed = document.getElementById('videoFeed');
    const videoModalLabel = document.getElementById('videoModalLabel');

    function showToast(message, type = 'primary') {
        const el = toastElement;
        el.querySelector('.toast-body').textContent = message;
        el.classList.remove('text-bg-primary','text-bg-success','text-bg-danger','text-bg-warning','text-bg-info');
        el.classList.add(`text-bg-${type}`);
        bootstrap.Toast.getOrCreateInstance(el).show();
    }
    function setRecordingUI(active){
        const startBtn = document.getElementById('startRecordingBtn');
        const stopBtn  = document.getElementById('stopRecordingBtn');
        if (!startBtn || !stopBtn) return;
        startBtn.classList.toggle('hidden', !!active);
        stopBtn.classList.toggle('hidden',  !active);
    }
    const modelBtn       = document.getElementById('modelBtn');
    const modelMenu      = document.getElementById('modelMenu'); // .model-menu en HTML
    const modelBtnLabel  = document.getElementById('modelBtnLabel');
    const whisperSelect  = document.getElementById('whisperModelSelect');

    if (modelBtn && modelMenu && modelBtnLabel && whisperSelect) {
        // Toggle del menú
        modelBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            modelMenu.style.display = modelMenu.style.display === 'block' ? 'none' : 'block';
        });
        // Cerrar al hacer click fuera
        document.addEventListener('click', () => { modelMenu.style.display = 'none'; });
        // Selección de opción
        modelMenu.querySelectorAll('button[data-model]').forEach(btn => {
            btn.addEventListener('click', () => {
                const val = btn.dataset.model;
                whisperSelect.value = val;
                // Texto visible sin paréntesis
                const clean = btn.textContent.trim().split('(')[0].trim();
                modelBtnLabel.textContent = clean;
                modelMenu.style.display = 'none';
            });
        });
    }
    if (whisperSelect && modelBtnLabel) {
        const opt = whisperSelect.options[whisperSelect.selectedIndex];
        if (opt) modelBtnLabel.textContent = opt.text.split('(')[0].trim();
    }    
    function loadAttendanceSummary() {
        fetch('/api/attendance_summary_today').then(res => res.json()).then(data => {
            const tbody = document.querySelector('#attendanceSummaryTable tbody');
            tbody.innerHTML = data.length ? data.map(i => `<tr><td>${i.periodo}</td><td>${i.total}</td></tr>`).join('') : '<tr><td colspan="2" class="text-center text-muted">Sin registros.</td></tr>';
        }).catch(err => console.error("Error cargando resumen de asistencia:", err));
    }

    function loadParticipationSummary() {
        fetch('/api/participation_summary_today').then(res => res.json()).then(data => {
            const tbody = document.querySelector('#participationSummaryTable tbody');
            tbody.innerHTML = data.length ? data.map(i => `<tr><td>${i.periodo}</td><td>${i.total_participantes}</td><td>${i.total_participaciones}</td></tr>`).join('') : '<tr><td colspan="3" class="text-center text-muted">Sin registros.</td></tr>';
        }).catch(err => console.error("Error cargando resumen de participación:", err));
    }

    function loadStudentList() {
        fetch(`/api/students_list?t=${Date.now()}`, {
            headers: { 'Accept': 'application/json' },
            cache: 'no-store'
        })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(payload => {
            // Soporta: [..] o {students:[..]}
            const list =
                (Array.isArray(payload) && payload) ||
                (Array.isArray(payload.students) && payload.students) ||
                (Array.isArray(payload.data) && payload.data) ||
                (Array.isArray(payload.results) && payload.results) ||
                [];
                console.log('students_list payload keys:', Object.keys(payload || {}), 'count:', list.length);
            const tbody = document.querySelector('#studentListTable tbody');

            // Normaliza campos frecuentes
            const norm = s => {
                const id = s.id ?? s.student_id ?? s.uid ?? s._id ?? '';
                const nombre = s.nombre ?? s.first_name ?? s.name ?? s.nombres ?? '';
                const apellido = s.apellido ?? s.last_name ?? s.surname ?? s.apellidos ?? '';
                const full = (s.nombre_completo ?? `${nombre} ${apellido}`)?.trim() || (s.full_name ?? '');
                const rawDate = s.registro_fecha ?? s.fecha_registro ?? s.created_at ?? s.createdAt ?? s.registro ?? s.created ?? null;
                const dateStr = rawDate
                    ? (isNaN(Date.parse(rawDate)) ? String(rawDate) : new Date(rawDate).toLocaleString())
                    : '-';
                return { id, full, dateStr };
            };

            const rows = list.map(s => {
                const n = norm(s);
                return `
                    <tr>
                        <td>${n.id}</td>
                        <td><a href="/student/${n.id}" class="text-info text-decoration-none">${n.full}</a></td>
                        <td>${n.dateStr}</td>
                        <td><button class="btn btn-sm btn-outline-danger del-btn" data-id="${n.id}"><i class="fas fa-trash"></i></button></td>
                    </tr>`;
            });

            tbody.innerHTML = rows.length
                ? rows.join('')
                : `<tr><td colspan="4" class="text-center text-muted">
                      No hay estudiantes. <small class="d-block text-muted">payload keys: ${Object.keys(payload).join(', ') || 'array vacío'}</small>
                   </td></tr>`;
            attachStudentDeleteEvents();
        })
        .catch(err => {
            console.error("Error cargando lista de estudiantes:", err);
            const tbody = document.querySelector('#studentListTable tbody');
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Error cargando estudiantes (${err.message}).</td></tr>`;
        });
    }

    function loadTranscriptions() {
        fetch('/api/transcriptions').then(res => res.json()).then(data => {
            const tbody = document.querySelector('#transcriptionsTable tbody');
            tbody.innerHTML = data.length ? data.map(t => {
                const textLink = t.text_file_path ? `<a href="${t.text_file_path}" target="_blank" class="btn btn-sm btn-outline-warning m-1"><i class="fas fa-file-alt me-1"></i>Ver Texto</a>` : '';
                const audioLink = t.file_path ? `<a href="${t.file_path}" download class="btn btn-sm btn-outline-info m-1"><i class="fas fa-download me-1"></i>Audio</a>` : '';
                const enhanceBtn = t.enhanced_text 
                    ? `<button class="btn btn-sm btn-success m-1 view-enhanced-btn" data-text="${escape(t.enhanced_text)}"><i class="fas fa-check"></i> Ver Mejora</button>`
                    : `<button class="btn btn-sm btn-outline-primary m-1 enhance-btn" data-id="${t.id}"><i class="fas fa-magic"></i> Mejorar con IA</button>`;
                const deleteBtn = `<button class="btn btn-sm btn-outline-danger m-1 del-trans-btn" data-id="${t.id}"><i class="fas fa-trash"></i></button>`;
                return `<tr><td>${t.class_name}</td><td>${new Date(t.start_timestamp).toLocaleString()}</td><td>${Math.round(t.duration_seconds)}s</td><td class="action-buttons">${textLink}${audioLink}${enhanceBtn}${deleteBtn}</td></tr>`;
            }).join('') : '<tr><td colspan="4" class="text-center text-muted">No hay grabaciones.</td></tr>';
            attachTranscriptionEvents();
        }).catch(err => console.error("Error cargando transcripciones:", err));
    }

    function attachStudentDeleteEvents() {
        document.querySelectorAll('.del-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const studentId = this.dataset.id;
                if (confirm(`¿Eliminar al estudiante ${studentId}? Esta acción no se puede deshacer.`)) {
                    fetch(`/api/delete_student/${studentId}`, { method: 'DELETE' }).then(res => res.json()).then(data => {
                        showToast(data.message, data.success ? 'success' : 'danger');
                        if (data.success) loadStudentList();
                    });
                }
            });
        });
    }
    
    function attachTranscriptionEvents() {
        document.querySelectorAll('.del-trans-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const transcriptionId = this.dataset.id;
                if (confirm(`¿Eliminar esta transcripción y sus archivos de audio/texto?`)) {
                    fetch(`/api/delete_transcription/${transcriptionId}`, { method: 'DELETE' }).then(res => res.json()).then(data => {
                        showToast(data.message, data.success ? 'success' : 'danger');
                        if (data.success) loadTranscriptions();
                    });
                }
            });
        });
        
        document.querySelectorAll('.enhance-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const transcriptionId = this.dataset.id;
                this.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Procesando...`;
                this.disabled = true;
                const response = await fetch(`/api/enhance_transcription/${transcriptionId}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    showToast('Transcripción mejorada con éxito.', 'success');
                    loadTranscriptions();
                } else {
                    showToast(`Error: ${data.message}`, 'danger');
                    this.innerHTML = `<i class="fas fa-magic"></i> Mejorar con IA`;
                    this.disabled = false;
                }
            });
        });

        document.querySelectorAll('.view-enhanced-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const text = unescape(this.dataset.text);
                document.getElementById('enhancedTextBody').innerText = text;
                enhancedTextModal.show();
            });
        });
    }

    function updateStatusIndicators() {
        fetch('/status').then(res => res.json()).then(data => {
            const statuses = {'attendance-status': data.attendance_active, 'pose-status': data.pose_active, 'recording-status': data.recording_active};
            for (const [id, isActive] of Object.entries(statuses)) {
                const el = document.getElementById(id);
                if (!el) continue;
                const text = id === 'recording-status' ? (isActive ? 'Grabando' : 'Inactivo') : (isActive ? 'Activo' : 'Inactivo');
                el.innerHTML = `<i class="fas fa-circle me-2"></i>${text}`;
                el.className = `fs-5 fw-bold ${isActive ? 'text-success' : 'text-danger'}`;
            }
            document.getElementById('startRecordingBtn').disabled = data.recording_active;
            document.getElementById('stopRecordingBtn').disabled = !data.recording_active;
            document.getElementById('whisperModelSelect').disabled = data.recording_active;
            if (modelBtn) modelBtn.disabled = data.recording_active; // bloquear selector mientras graba
        });
    }

    async function handleMonitorAction(url, actionName, videoSrc = null, modalTitle = "Monitoreo en Vivo") {
        try {
            const response = await fetch(url, { method: 'POST' });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            showToast(data.message, data.success ? 'success' : 'warning');
            if (data.success && videoSrc) {

                videoModalLabel.textContent = modalTitle;
                videoFeed.onerror = () => showToast('No se pudo cargar el video.', 'danger');
                videoFeed.src = '';

                setTimeout(() => {
                    videoFeed.src = `${videoSrc}?t=${Date.now()}`;
                    videoModal.show();
                }, 50);
            }
        } catch (error) {
            showToast(`Error de conexión al ${actionName}.`, 'danger');
        } finally {
            updateStatusIndicators();
        }
    }

    document.getElementById('startAttendanceBtn').addEventListener('click', () => handleMonitorAction('/start_attendance_monitor', 'iniciar asistencia', '/video_feed/attendance', 'Monitoreo de Asistencia'));
    document.getElementById('stopAttendanceBtn').addEventListener('click', () => handleMonitorAction('/stop_attendance_monitor', 'detener asistencia'));
    document.getElementById('startPoseBtn').addEventListener('click', () => handleMonitorAction('/start_pose_monitor', 'iniciar pose', '/video_feed/pose', 'Monitoreo de Postura y Gestos'));
    document.getElementById('stopPoseBtn').addEventListener('click', () => handleMonitorAction('/stop_pose_monitor', 'detener pose'));
    
    document.getElementById('videoModal').addEventListener('hidden.bs.modal', event => {
        const currentSrc = videoFeed.src;
        videoFeed.src = "";
        if (currentSrc.includes('attendance')) {
            handleMonitorAction('/stop_attendance_monitor', 'detener asistencia');
        } else if (currentSrc.includes('pose')) {
            handleMonitorAction('/stop_pose_monitor', 'detener pose');
        }
    });

    document.getElementById('startRecordingBtn').addEventListener('click', async () => {
        setRecordingUI(true); // feedback inmediato
        await handleMonitorAction('/start_manual_recording', 'iniciar grabación');
    });
    document.getElementById('stopRecordingBtn').addEventListener('click', async () => {
        const btn = document.getElementById('stopRecordingBtn');
        const modelSelect = document.getElementById('whisperModelSelect');
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Transcribiendo...`;
        btn.disabled = true;
        modelSelect.disabled = true;

        const formData = new FormData();
        formData.append('model_size', modelSelect.value);
        
        try {
            const data = await fetch('/stop_manual_recording', { method: 'POST', body: formData }).then(res => res.json());
            showToast(data.message, data.success ? 'success' : 'warning');
            if (data.success) {
                loadTranscriptions();
            }
        } catch (error) {
            showToast('Error de conexión al detener la grabación.', 'danger');
        } finally {
            btn.innerHTML = `Detener y Transcribir`;
            updateStatusIndicators();
        }
    });

    function loadAllData() {
        loadAttendanceSummary();
        loadParticipationSummary();
        loadStudentList();
        loadTranscriptions();
    }
    loadAllData();
    // refresco breve tras altas recientes
    setTimeout(loadStudentList, 2000);
    setTimeout(loadStudentList, 5000);
    updateStatusIndicators();
    // sincroniza visibilidad Start/Stop según /status
    setInterval(() => {
        fetch('/status').then(r=>r.json()).then(s=>setRecordingUI(!!s.recording_active));
    }, 1000);
    
    setInterval(updateStatusIndicators, 3000);
    setInterval(() => {
        loadAttendanceSummary();
        loadParticipationSummary();
    }, 30000);
});