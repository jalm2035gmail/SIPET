// JS migrado para pantalla de personalización
// Mostrar/ocultar panel según el estado del drawer
const personalizationPanel = document.querySelector('.personalization-panel');
const setFloatingScreen = (screen) => {
    if (personalizationPanel) {
        personalizationPanel.classList.toggle('hidden', screen !== 'personalization');
    }
};
// Ejemplo: mostrar panel al cargar
setFloatingScreen('personalization');
// Aquí puedes agregar lógica adicional para guardar colores, etc.