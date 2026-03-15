// departamentos.js
// Lógica inicial para manejar eventos del formulario de departamentos

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.departamento-form form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            // Aquí irá la lógica para guardar el departamento
            alert('Departamento guardado (demo)');
        });
    }
});
