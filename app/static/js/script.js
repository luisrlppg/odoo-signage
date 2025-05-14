// Reemplaza la función initGroupView() por esta versión corregida:
function initGroupView() {
    const slideGroups = document.querySelectorAll('.slide-group');
    let currentIndex = 0;
    const intervalTime = 3000; // 15 segundos por grupo
    
    if (slideGroups.length > 1) { // Solo si hay más de un grupo
        function showNextGroup() {
            slideGroups[currentIndex].classList.remove('active');
            currentIndex = (currentIndex + 1) % slideGroups.length;
            slideGroups[currentIndex].classList.add('active');
        }
        
        // Iniciar el intervalo
        const intervalId = setInterval(showNextGroup, intervalTime);
        
        // Pausar al hacer hover (opcional)
        const container = document.querySelector('.slides-container');
        container.addEventListener('mouseenter', () => clearInterval(intervalId));
        container.addEventListener('mouseleave', () => {
            intervalId = setInterval(showNextGroup, intervalTime);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    
    // Inicializar la vista correcta según la página
    if (document.querySelector('.carousel')) {
        initCarousel();
    } else if (document.querySelector('.group-view')) {
        initGroupView();
    }
});

// Mover la lógica del carrusel a una función separada
function initCarousel() {
    const slides = document.querySelector('.slides');
    const slideItems = document.querySelectorAll('.slide');
    let currentIndex = 0;
    const intervalTime = 6000;
    
    function nextSlide() {
        slideItems[currentIndex].classList.remove('active');
        currentIndex = (currentIndex + 1) % slideItems.length;
        slideItems[currentIndex].classList.add('active');
        
        slideItems.forEach((slide, index) => {
            const offset = (index - currentIndex) * 100;
            const scale = index === currentIndex ? 1 : 0.9;
            const opacity = index === currentIndex ? 1 : 0.7;
            const zIndex = index === currentIndex ? 1 : 0;
            
            slide.style.transform = `translateX(${offset}%) scale(${scale})`;
            slide.style.opacity = opacity;
            slide.style.zIndex = zIndex;
        });
    }
    
    setInterval(nextSlide, intervalTime);
    
    // Configuración inicial
    slideItems.forEach((slide, index) => {
        const offset = (index - currentIndex) * 100;
        const scale = index === currentIndex ? 1 : 0.9;
        const opacity = index === currentIndex ? 1 : 0.7;
        const zIndex = index === currentIndex ? 1 : 0;
        
        slide.style.transform = `translateX(${offset}%) scale(${scale})`;
        slide.style.opacity = opacity;
        slide.style.zIndex = zIndex;
    });
}