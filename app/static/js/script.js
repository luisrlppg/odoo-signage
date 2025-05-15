document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    initCategoryRotation();
});
// Función de partículas (mantener igual)
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        
        const size = Math.random() * 5 + 1;
        const posX = Math.random() * 100;
        const posY = Math.random() * 100;
        const delay = Math.random() * 5;
        const duration = Math.random() * 10 + 10;
        
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${posX}%`;
        particle.style.top = `${posY}%`;
        particle.style.opacity = Math.random() * 0.5 + 0.1;
        particle.style.animation = `float ${duration}s ease-in-out ${delay}s infinite`;
        
        particlesContainer.appendChild(particle);
    }
}

function initCategoryRotation() {
    const categories = ['inyeccion', 'ensamble', 'cepillo'];
    const categorySections = document.querySelectorAll('.category-section');
    const categoryDuration = 30000; // 30 segundos por categoría
    let currentCategoryIndex = 0;
    
    if (categories.length <= 1) return; // No rotar si solo hay una categoría

    function showCategory(index) {
        // Oculta todas las categorías
        categorySections.forEach(section => {
            section.classList.remove('active');
        });
        
        // Muestra la categoría actual
        document.getElementById(categories[index]).classList.add('active');
        
        // Inicia el carrusel de slides para esta categoría
        initSlideRotation(categories[index]);
        
        currentCategoryIndex = index;
    }

    function nextCategory() {
        const newIndex = (currentCategoryIndex + 1) % categories.length;
        showCategory(newIndex);
    }

    function initSlideRotation(category) {
        const slides = document.querySelectorAll(`.slide[data-category="${category}"]`);
        const slideCount = slides.length;
        let currentSlideIndex = 0;
        const slideDuration = 10000; // 10 segundos por slide
        
        if (slideCount <= 1) return; // No rotar si solo hay un slide

        function showSlide(index) {
            slides.forEach(slide => {
                slide.classList.remove('active');
                slide.style.opacity = '0';
            });
            
            slides[index].classList.add('active');
            slides[index].style.opacity = '1';
            currentSlideIndex = index;
            
            updateSlideCounter(slides[index], index);
        }

        function updateSlideCounter(slide, index) {
            const counter = slide.querySelector('.slide-counter .current');
            if (counter) {
                counter.textContent = index + 1;
            }
        }

        function nextSlide() {
            const newIndex = (currentSlideIndex + 1) % slideCount;
            showSlide(newIndex);
        }

        // Mostrar primer slide y configurar intervalo
        showSlide(0);
        const intervalId = setInterval(nextSlide, slideDuration);
        
        // Limpiar intervalo cuando cambie de categoría
        setTimeout(() => {
            clearInterval(intervalId);
        }, categoryDuration - 1000);
    }

    // Iniciar rotación de categorías
    showCategory(0);
    setInterval(nextCategory, categoryDuration);
}