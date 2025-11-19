// static/assign_seats.js

document.addEventListener('DOMContentLoaded', function () {
    const toastElement = document.getElementById('action-toast');
    const toast = new bootstrap.Toast(toastElement);

    function showToast(message, type = 'primary') {
        toastElement.querySelector('.toast-body').textContent = message;
        toastElement.className = `toast align-items-center text-bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.show();
    }

    const cardsContainer = document.getElementById('assignCards');

    // Cargar todos los datos necesarios y construir las tarjetas de asientos
    async function loadAssignTable() {
        try {
            const [seatBoxesRes, assignmentsRes, studentsRes] = await Promise.all([
                fetch('/api/seat_boxes'),
                fetch('/api/seat_assignments'),
                fetch('/api/students_list')
            ]);
            const seatBoxes = await seatBoxesRes.json();
            const seatAssignments = await assignmentsRes.json();
            const students = await studentsRes.json();

            // Construir mapa de estudiantes
            const studentMap = {};
            students.forEach(s => {
                const fullName = `${s.nombre} ${s.apellido}`.trim();
                studentMap[s.id] = fullName;
            });

            // Construir opciones HTML para cada estudiante
            const studentOptions = Object.entries(studentMap).map(([id, name]) => `<option value="${id}">${name}</option>`).join('');

            // Construir tarjetas de asientos
            if (seatBoxes.length > 0) {
                cardsContainer.innerHTML = seatBoxes.map(seat => {
                    const sid = seat.seat_id;
                    return `
                      <div class="card card-custom h-100">
                        <div class="card-body">
                          <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="card-title">${sid}</span>
                            <button class="btn btn-sm btn-outline-warning rename-btn" data-seat-id="${sid}">
                              <i class="fas fa-pen"></i>
                            </button>
                          </div>
                          <div>
                            <label class="form-label">Alumno</label>
                            <select class="form-select seat-select" data-seat-id="${sid}">
                              <option value="">Sin asignar</option>
                              ${studentOptions}
                            </select>
                          </div>
                        </div>
                      </div>`;
                }).join('');
            } else {
                cardsContainer.innerHTML = `<div class="col-12"><div class="text-center text-muted">No hay asientos definidos. Primero calibre los asientos.</div></div>`;
            }
            // Establecer valores y eventos en selectores
            document.querySelectorAll('.seat-select').forEach(sel => {
                const sid = sel.dataset.seatId;
                const assignedId = seatAssignments[sid] || '';
                sel.value = assignedId;
                sel.addEventListener('change', function () {
                    const newStudentId = this.value;
                    const seatId = this.dataset.seatId;
                    fetch('/api/assign_seat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ seat_id: seatId, student_id: newStudentId })
                    }).then(res => res.json()).then(data => {
                        if (data.success) {
                            const studentName = newStudentId ? studentMap[newStudentId] : 'Sin asignar';
                            showToast(`Asignación actualizada: ${seatId} -> ${studentName}`, 'success');
                        } else {
                            showToast('No se pudo asignar el asiento.', 'danger');
                        }
                    }).catch(err => {
                        console.error(err);
                        showToast('Error al asignar asiento.', 'danger');
                    });
                });
            });
            // Establecer eventos en botones de renombrado
            document.querySelectorAll('.rename-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    const oldId = this.dataset.seatId;
                    const proposed = prompt('Nuevo identificador para el asiento:', oldId);
                    if (!proposed) return;
                    const newId = proposed.trim();
                    if (newId === oldId || newId === '') return;
                    fetch('/api/rename_seat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ old_id: oldId, new_id: newId })
                    }).then(res => res.json()).then(data => {
                        if (data.success) {
                            showToast(`Asiento renombrado: ${oldId} -> ${newId}`, 'success');
                            loadAssignTable();
                        } else {
                            showToast('No se pudo renombrar el asiento. Verifique que el nuevo nombre no exista.', 'danger');
                        }
                    }).catch(err => {
                        console.error(err);
                        showToast('Error al renombrar el asiento.', 'danger');
                    });
                });
            });

        } catch (error) {
            console.error(error);
            showToast('Error al cargar la tabla de asignaciones.', 'danger');
        }
    }

    loadAssignTable();
});