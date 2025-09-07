// static/assign_seats.js

document.addEventListener('DOMContentLoaded', function () {
    const toastElement = document.getElementById('action-toast');
    const toast = new bootstrap.Toast(toastElement);

    function showToast(message, type = 'primary') {
        toastElement.querySelector('.toast-body').textContent = message;
        toastElement.className = `toast align-items-center text-bg-${type} border-0 position-fixed top-0 end-0 m-3`;
        toast.show();
    }

    const tableBody = document.querySelector('#assignTable tbody');

    // Cargar todos los datos necesarios y construir la tabla
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

            // Construir filas de la tabla
            tableBody.innerHTML = seatBoxes.length ? seatBoxes.map(seat => {
                const sid = seat.seat_id;
                const assignedId = seatAssignments[sid] || '';
                return `
                    <tr>
                        <td>${sid}</td>
                        <td>
                            <select class="form-select seat-select" data-seat-id="${sid}">
                                <option value="">Sin asignar</option>
                                ${studentOptions}
                            </select>
                        </td>
                    </tr>
                `;
            }).join('') : '<tr><td colspan="2" class="text-center text-muted">No hay asientos definidos. Primero calibre los asientos.</td></tr>';

            // Establecer valores actuales
            document.querySelectorAll('.seat-select').forEach(sel => {
                const sid = sel.dataset.seatId;
                const assignedId = seatAssignments[sid] || '';
                sel.value = assignedId;
                sel.addEventListener('change', function () {
                    const newStudentId = this.value;
                    const seatId = this.dataset.seatId;
                    // Asignar
                    fetch('/api/assign_seat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ seat_id: seatId, student_id: newStudentId })
                    }).then(res => res.json()).then(data => {
                        if (data.success) {
                            const studentName = newStudentId ? studentMap[newStudentId] : 'Sin asignar';
                            showToast(`Asignación actualizada: ${seatId} → ${studentName}`, 'success');
                        } else {
                            showToast('No se pudo asignar el asiento.', 'danger');
                        }
                    }).catch(err => {
                        console.error(err);
                        showToast('Error al asignar asiento.', 'danger');
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